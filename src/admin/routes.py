import pathlib

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from src.admin.auth import (
    verify_admin_password,
    verify_admin_session,
    create_admin_session,
    clear_admin_session,
)
from src.config import settings
from src.secrets.manager import secret_manager

TEMPLATES_DIR = pathlib.Path(__file__).resolve().parent.parent / "templates_jinja"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

admin_router = APIRouter(prefix="/admin", tags=["admin"])


@admin_router.get("/login", response_class=HTMLResponse)
async def admin_login_page(request: Request):
    """管理者ログインフォームを表示する。"""
    if verify_admin_session(request):
        return RedirectResponse(url="/admin", status_code=303)
    return templates.TemplateResponse("admin_login.html", {"request": request, "error": None})


@admin_router.post("/login")
async def admin_login(request: Request, password: str = Form(...)):
    """パスワードを検証しセッションCookieを設定する。"""
    if await verify_admin_password(password):
        response = RedirectResponse(url="/admin", status_code=303)
        create_admin_session(response)
        return response
    return templates.TemplateResponse(
        "admin_login.html",
        {"request": request, "error": "パスワードが正しくありません"},
        status_code=401,
    )


@admin_router.get("", response_class=HTMLResponse)
@admin_router.get("/", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    """APIキー管理画面を表示する。"""
    if not verify_admin_session(request):
        return RedirectResponse(url="/admin/login", status_code=303)

    keys_status = await secret_manager.check_keys_configured()
    google_preview = await secret_manager.get_key_preview(settings.secret_id_google_key)
    openai_preview = await secret_manager.get_key_preview(settings.secret_id_openai_key)
    drive_folder = await secret_manager.get_drive_folder_id()

    return templates.TemplateResponse(
        "admin_keys.html",
        {
            "request": request,
            "google_configured": keys_status["google_api_key"],
            "openai_configured": keys_status["openai_api_key"],
            "google_preview": google_preview,
            "openai_preview": openai_preview,
            "drive_folder_id": drive_folder,
            "message": None,
        },
    )


@admin_router.post("/api/keys")
async def update_api_key(
    request: Request,
    key_type: str = Form(...),
    key_value: str = Form(...),
):
    """APIキーを更新する。"""
    if not verify_admin_session(request):
        return RedirectResponse(url="/admin/login", status_code=303)

    secret_id_map = {
        "google": settings.secret_id_google_key,
        "openai": settings.secret_id_openai_key,
    }
    secret_id = secret_id_map.get(key_type)
    if not secret_id:
        return RedirectResponse(url="/admin", status_code=303)

    success = await secret_manager.set_secret(secret_id, key_value.strip())
    message = "APIキーを更新しました" if success else "APIキーの更新に失敗しました"

    keys_status = await secret_manager.check_keys_configured()
    google_preview = await secret_manager.get_key_preview(settings.secret_id_google_key)
    openai_preview = await secret_manager.get_key_preview(settings.secret_id_openai_key)
    drive_folder = await secret_manager.get_drive_folder_id()

    return templates.TemplateResponse(
        "admin_keys.html",
        {
            "request": request,
            "google_configured": keys_status["google_api_key"],
            "openai_configured": keys_status["openai_api_key"],
            "google_preview": google_preview,
            "openai_preview": openai_preview,
            "drive_folder_id": drive_folder,
            "message": message,
        },
    )


@admin_router.post("/drive-folder")
async def update_drive_folder(
    request: Request,
    folder_id: str = Form(...),
):
    """DriveフォルダIDを更新する。"""
    if not verify_admin_session(request):
        return RedirectResponse(url="/admin/login", status_code=303)

    success = await secret_manager.set_secret(
        settings.secret_id_drive_folder, folder_id.strip()
    )
    message = "DriveフォルダIDを更新しました" if success else "更新に失敗しました"

    keys_status = await secret_manager.check_keys_configured()
    google_preview = await secret_manager.get_key_preview(settings.secret_id_google_key)
    openai_preview = await secret_manager.get_key_preview(settings.secret_id_openai_key)
    drive_folder = await secret_manager.get_drive_folder_id()

    return templates.TemplateResponse(
        "admin_keys.html",
        {
            "request": request,
            "google_configured": keys_status["google_api_key"],
            "openai_configured": keys_status["openai_api_key"],
            "google_preview": google_preview,
            "openai_preview": openai_preview,
            "drive_folder_id": drive_folder,
            "message": message,
        },
    )


@admin_router.post("/logout")
async def admin_logout():
    """管理者セッションをクリアしてログアウトする。"""
    response = RedirectResponse(url="/admin/login", status_code=303)
    clear_admin_session(response)
    return response
