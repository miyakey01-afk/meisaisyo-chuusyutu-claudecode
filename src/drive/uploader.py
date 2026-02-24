import io
import logging
from datetime import datetime, timezone, timedelta

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseUpload
import google.auth

logger = logging.getLogger(__name__)

JST = timezone(timedelta(hours=9))


class DriveUploadError(Exception):
    """Google Drive アップロード固有のエラー"""
    pass


def _get_drive_service():
    """Application Default Credentials で Drive API サービスを取得する。"""
    try:
        credentials, project = google.auth.default(
            scopes=["https://www.googleapis.com/auth/drive.file"]
        )
        logger.info("Drive API 認証成功 (project=%s)", project)
        return build("drive", "v3", credentials=credentials, cache_discovery=False)
    except Exception as e:
        logger.error("Drive API 認証失敗: %s", e)
        raise DriveUploadError(f"Drive API 認証に失敗しました: {e}") from e


def generate_filename(base_name: str = "明細書EXCEL出力") -> str:
    """日時付きのファイル名を生成する。"""
    now = datetime.now(JST)
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    return f"{base_name}_{timestamp}.xlsx"


def upload_to_drive(
    xlsx_bytes: bytes,
    folder_id: str,
    filename: str | None = None,
) -> str:
    """XLSXファイルをGoogle Driveにアップロードし、webViewLinkを返す。

    Args:
        xlsx_bytes: XLSXファイルのバイト列
        folder_id: アップロード先のGoogle DriveフォルダID
        filename: ファイル名（省略時は自動生成）

    Returns:
        Google DriveのwebViewLink (閲覧/ダウンロード用URL)
    """
    if filename is None:
        filename = generate_filename()

    logger.info("Drive アップロード開始: folder_id=%s, filename=%s", folder_id, filename)

    service = _get_drive_service()

    file_metadata = {
        "name": filename,
        "parents": [folder_id],
    }
    media = MediaIoBaseUpload(
        io.BytesIO(xlsx_bytes),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        resumable=False,
    )
    try:
        file = (
            service.files()
            .create(
                body=file_metadata,
                media_body=media,
                fields="id,webViewLink",
            )
            .execute()
        )
        link = file.get("webViewLink", "")
        logger.info("Drive アップロード成功: file_id=%s, link=%s", file.get("id"), link)
        return link
    except HttpError as e:
        logger.error(
            "Drive API HTTPエラー: status=%s, reason=%s, details=%s",
            e.status_code, e.reason, e.error_details,
        )
        raise DriveUploadError(
            f"Drive API エラー (HTTP {e.status_code}): {e.reason}"
        ) from e
    except Exception as e:
        logger.error("Drive アップロード予期せぬエラー: %s", e, exc_info=True)
        raise DriveUploadError(f"Drive アップロードに失敗しました: {e}") from e
