import logging
from dataclasses import dataclass

from openai import AuthenticationError as OpenAIAuthError
from openai import APIConnectionError as OpenAIConnectionError
from openai import APITimeoutError as OpenAITimeoutError
from openai import RateLimitError as OpenAIRateLimitError
from google.genai.errors import ClientError as GenaiClientError
from google.genai.errors import ServerError as GenaiServerError
from googleapiclient.errors import HttpError as DriveHttpError
from google.auth.exceptions import GoogleAuthError

from src.workflow.ocr import ocr_extract, OCRError
from src.workflow.router import detect_company, CompanyType
from src.workflow.analyzer import analyze_bill, AnalysisError
from src.combiner.markdown_combiner import combine_markdown_rows, EmptyResultError
from src.export.xlsx_exporter import markdown_to_xlsx
from src.drive.uploader import upload_to_drive, generate_filename

logger = logging.getLogger(__name__)

ERROR_MESSAGE_FILE_TOO_LARGE = """\
ファイルの処理に失敗しました。

PDFや画像の容量が大きすぎる、またはページ数が多すぎる可能性があります。
お手数ですが、次のいずれかの方法をお試しください。

- ファイルを圧縮する（PDF圧縮でWeb検索しI Love PDFなどのwebサイトで圧縮）
- PDFを数ページごとに分割して、1ファイルずつアップロードする
- 画像の場合はファイルサイズを小さくしてから再アップロードする（画像圧縮でWeb検索しI Love IMGなどのwebサイトで圧縮）

※特に最近のiphoneの画像は高画質なためエラーが出る場合があります。

その他、うまく行かない場合は三宅まで連絡下さい"""

ERROR_MESSAGE_API_KEY = """\
APIキーが無効または期限切れです。
管理者に連絡してAPIキーを確認してください。"""

ERROR_MESSAGE_NETWORK = """\
外部サービスへの通信に失敗しました。
しばらく待ってから再度お試しください。"""

ERROR_MESSAGE_EMPTY_RESULT = """\
データが抽出できませんでした。
ファイルの内容を確認し、明細書が含まれているか確認してください。"""

ERROR_MESSAGE_DRIVE_UPLOAD = """\
Google Driveへのアップロードに失敗しました。
しばらく待ってから再度お試しください。それでも解決しない場合は三宅まで連絡下さい。"""

ERROR_MESSAGE_UNKNOWN = """\
予期しないエラーが発生しました。
三宅まで連絡下さい。"""


def _classify_cause(cause: BaseException | None) -> str:
    """ラップされた例外の __cause__ を検査してエラー種別を返す。"""
    if cause is None:
        return "unknown"

    # OpenAI errors (AnalysisError の中)
    if isinstance(cause, OpenAIAuthError):
        return "api_key"
    if isinstance(cause, (OpenAIConnectionError, OpenAITimeoutError, OpenAIRateLimitError)):
        return "network"

    # Google Gemini errors (OCRError の中)
    if isinstance(cause, GenaiClientError):
        code = getattr(cause, "code", 0)
        status = str(getattr(cause, "status", ""))
        message = str(getattr(cause, "message", ""))
        if code in (401, 403) or "API_KEY_INVALID" in status or "API_KEY_INVALID" in message:
            return "api_key"
        if code == 429:
            return "network"
        return "file_too_large"
    if isinstance(cause, GenaiServerError):
        return "network"

    # Python built-in の接続エラー
    if isinstance(cause, (ConnectionError, TimeoutError, OSError)):
        return "network"

    return "unknown"


@dataclass
class PipelineResult:
    success: bool
    drive_url: str | None = None
    filename: str | None = None
    error_message: str | None = None


async def process_bill(
    files: list[tuple[str, bytes]],
    google_api_key: str,
    openai_api_key: str,
    drive_folder_id: str,
) -> PipelineResult:
    """明細抽出パイプライン全体を実行する。

    1. OCR (Gemini 2.5 Flash)
    2. 会社判定 (IF/ELSE)
    3. 明細分析 (GPT-4.1)
    4. Markdown結合
    5. XLSX変換
    6. Google Driveアップロード

    Args:
        files: (filename, content_bytes) のリスト
        google_api_key: Google API Key (Gemini用)
        openai_api_key: OpenAI API Key (GPT-4.1用)
        drive_folder_id: Google DriveフォルダID

    Returns:
        PipelineResult with drive_url on success, error_message on failure
    """
    try:
        # Step 1: OCR
        ocr_text = await ocr_extract(files, google_api_key)

        # Step 2: 会社判定
        company = detect_company(ocr_text)

        # Step 3: 明細分析
        analysis_result = await analyze_bill(ocr_text, company, openai_api_key)

        # Step 4: Markdown結合
        results = {company: analysis_result}
        markdown = combine_markdown_rows(results)

        # Step 5: XLSX変換
        xlsx_bytes = markdown_to_xlsx(markdown)

        # Step 6: Google Driveアップロード
        filename = generate_filename()
        drive_url = upload_to_drive(xlsx_bytes, drive_folder_id, filename)

        return PipelineResult(
            success=True,
            drive_url=drive_url,
            filename=filename,
        )

    except EmptyResultError as e:
        logger.warning("Pipeline failed: empty result. %s", e)
        return PipelineResult(success=False, error_message=ERROR_MESSAGE_EMPTY_RESULT)

    except (OCRError, AnalysisError) as e:
        category = _classify_cause(e.__cause__)
        logger.error(
            "Pipeline failed at %s: %s (cause: %s, category: %s)",
            type(e).__name__, e, e.__cause__, category,
        )
        message = {
            "api_key": ERROR_MESSAGE_API_KEY,
            "network": ERROR_MESSAGE_NETWORK,
            "file_too_large": ERROR_MESSAGE_FILE_TOO_LARGE,
        }.get(category, ERROR_MESSAGE_FILE_TOO_LARGE)
        return PipelineResult(success=False, error_message=message)

    except ValueError as e:
        logger.warning("Pipeline failed: xlsx conversion error. %s", e)
        return PipelineResult(success=False, error_message=ERROR_MESSAGE_EMPTY_RESULT)

    except (DriveHttpError, GoogleAuthError) as e:
        logger.error("Pipeline failed: Drive error. %s", e)
        return PipelineResult(success=False, error_message=ERROR_MESSAGE_DRIVE_UPLOAD)

    except Exception as e:
        logger.exception("Pipeline failed: unexpected error.")
        return PipelineResult(success=False, error_message=ERROR_MESSAGE_UNKNOWN)
