import logging
import pathlib
from typing import List

from fastapi import FastAPI, File, UploadFile, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.admin.routes import admin_router
from src.config import settings
from src.secrets.manager import secret_manager
from src.workflow.pipeline import process_bill

logger = logging.getLogger(__name__)

BASE_DIR = pathlib.Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates_jinja"
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(title="明細抽出くん Ver2")

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

app.include_router(admin_router)


@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/extract")
async def extract_bill(files: List[UploadFile] = File(...)):
    """ファイルを受け取り、明細抽出パイプラインを実行する。"""
    # バリデーション: ファイル数
    if len(files) > settings.max_file_count:
        return JSONResponse(
            content={
                "success": False,
                "error_message": f"ファイルは同時に{settings.max_file_count}枚までです。",
            }
        )

    # バリデーション: ファイル形式
    allowed_ext = {".pdf", ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"}
    for f in files:
        ext = "." + f.filename.rsplit(".", 1)[-1].lower() if "." in f.filename else ""
        if ext not in allowed_ext:
            return JSONResponse(
                content={
                    "success": False,
                    "error_message": f"サポートされていないファイル形式です: {f.filename}",
                }
            )

    # APIキー取得
    google_key = await secret_manager.get_google_api_key()
    openai_key = await secret_manager.get_openai_api_key()
    if not google_key or not openai_key:
        return JSONResponse(
            content={
                "success": False,
                "error_message": "APIキーが設定されていません。管理者に連絡してください。",
            }
        )

    # DriveフォルダID取得
    drive_folder_id = await secret_manager.get_drive_folder_id()

    # ファイル読み込み
    file_data: list[tuple[str, bytes]] = []
    for f in files:
        content = await f.read()
        file_data.append((f.filename, content))

    # パイプライン実行
    filenames = [f.filename for f in files]
    logger.info("パイプライン開始: files=%s, drive_folder_id=%s", filenames, drive_folder_id)
    result = await process_bill(file_data, google_key, openai_key, drive_folder_id)

    if result.success:
        logger.info("パイプライン成功: filename=%s", result.filename)
    else:
        logger.warning("パイプライン失敗: error_message=%s", result.error_message)

    return JSONResponse(
        content={
            "success": result.success,
            "drive_url": result.drive_url,
            "filename": result.filename,
            "error_message": result.error_message,
        }
    )


@app.get("/health")
async def health():
    return {"status": "ok"}
