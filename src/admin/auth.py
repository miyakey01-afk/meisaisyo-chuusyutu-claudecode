import time
from typing import Optional

from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from fastapi import Request, Response

from src.config import settings
from src.secrets.manager import secret_manager

ADMIN_COOKIE_NAME = "meisaisyo_admin_session"

_serializer: Optional[URLSafeTimedSerializer] = None


def _get_serializer() -> URLSafeTimedSerializer:
    global _serializer
    if _serializer is None:
        _serializer = URLSafeTimedSerializer(settings.session_secret_key)
    return _serializer


async def verify_admin_password(password: str) -> bool:
    """入力されたパスワードを保存済みパスワードと照合する。"""
    stored = await secret_manager.get_admin_password()
    if not stored:
        return False
    return password == stored


def create_admin_session(response: Response) -> None:
    """管理者セッションCookieを設定する。"""
    serializer = _get_serializer()
    token = serializer.dumps({"admin": True})
    response.set_cookie(
        key=ADMIN_COOKIE_NAME,
        value=token,
        max_age=settings.session_max_age,
        httponly=True,
        samesite="lax",
    )


def verify_admin_session(request: Request) -> bool:
    """リクエストの管理者セッションCookieを検証する。"""
    token = request.cookies.get(ADMIN_COOKIE_NAME)
    if not token:
        return False
    try:
        serializer = _get_serializer()
        data = serializer.loads(token, max_age=settings.session_max_age)
        return data.get("admin") is True
    except (BadSignature, SignatureExpired):
        return False


def clear_admin_session(response: Response) -> None:
    """管理者セッションCookieを削除する。"""
    response.delete_cookie(key=ADMIN_COOKIE_NAME)
