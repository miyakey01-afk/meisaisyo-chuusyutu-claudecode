import io
from datetime import datetime, timezone, timedelta

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import google.auth

JST = timezone(timedelta(hours=9))


def _get_drive_service():
    """Application Default Credentials で Drive API サービスを取得する。"""
    credentials, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/drive.file"]
    )
    return build("drive", "v3", credentials=credentials, cache_discovery=False)


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
    file = (
        service.files()
        .create(
            body=file_metadata,
            media_body=media,
            fields="id,webViewLink",
        )
        .execute()
    )
    return file.get("webViewLink", "")
