import logging
from dataclasses import dataclass

from src.workflow.ocr import ocr_extract, OCRError
from src.workflow.router import detect_company, CompanyType
from src.workflow.analyzer import analyze_bill, AnalysisError
from src.combiner.markdown_combiner import combine_markdown_rows, EmptyResultError
from src.export.xlsx_exporter import markdown_to_xlsx
from src.drive.uploader import upload_to_drive, generate_filename, DriveUploadError

logger = logging.getLogger(__name__)

# DSL テンプレートノード 1764721294262 のエラーメッセージをそのまま使用
ERROR_MESSAGE = """\
ファイルの処理に失敗しました。

PDFや画像の容量が大きすぎる、またはページ数が多すぎる可能性があります。
お手数ですが、次のいずれかの方法をお試しください。

- ファイルを圧縮する（PDF圧縮でWeb検索しI Love PDFなどのwebサイトで圧縮）
- PDFを数ページごとに分割して、1ファイルずつアップロードする
- 画像の場合はファイルサイズを小さくしてから再アップロードする（画像圧縮でWeb検索しI Love IMGなどのwebサイトで圧縮）

※特に最近のiphoneの画像は高画質なためエラーが出る場合があります。

その他、うまく行かない場合は三宅まで連絡下さい"""

DRIVE_ERROR_MESSAGE = """\
Google Driveへのアップロードに失敗しました。\
しばらく待ってから再度お試しください。\
それでも解決しない場合は三宅まで連絡下さい。"""


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
        logger.info("Step 1: OCR開始 (ファイル数=%d)", len(files))
        ocr_text = await ocr_extract(files, google_api_key)
        logger.info("Step 1: OCR完了 (テキスト長=%d)", len(ocr_text))

        # Step 2: 会社判定
        company = detect_company(ocr_text)
        logger.info("Step 2: 会社判定完了 → %s", company)

        # Step 3: 明細分析
        logger.info("Step 3: 明細分析開始")
        analysis_result = await analyze_bill(ocr_text, company, openai_api_key)
        logger.info("Step 3: 明細分析完了")

        # Step 4: Markdown結合
        results = {company: analysis_result}
        markdown = combine_markdown_rows(results)
        logger.info("Step 4: Markdown結合完了")

        # Step 5: XLSX変換
        xlsx_bytes = markdown_to_xlsx(markdown)
        logger.info("Step 5: XLSX変換完了 (サイズ=%d bytes)", len(xlsx_bytes))

        # Step 6: Google Driveアップロード
        filename = generate_filename()
        drive_url = upload_to_drive(xlsx_bytes, drive_folder_id, filename)
        logger.info("Step 6: Driveアップロード完了 → %s", drive_url)

        return PipelineResult(
            success=True,
            drive_url=drive_url,
            filename=filename,
        )

    except DriveUploadError as e:
        logger.error("Google Driveアップロード失敗: %s", e, exc_info=True)
        return PipelineResult(success=False, error_message=DRIVE_ERROR_MESSAGE)
    except (OCRError, AnalysisError, EmptyResultError, ValueError) as e:
        logger.error("パイプライン処理エラー: %s", e, exc_info=True)
        return PipelineResult(success=False, error_message=ERROR_MESSAGE)
    except Exception as e:
        logger.error("パイプライン予期せぬエラー: %s", e, exc_info=True)
        return PipelineResult(success=False, error_message=ERROR_MESSAGE)
