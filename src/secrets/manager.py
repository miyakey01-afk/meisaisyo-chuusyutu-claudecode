import time
from typing import Optional

from src.config import settings


class SecretManagerClient:
    """Google Cloud Secret Manager のラッパー（5分インメモリキャッシュ付き）。

    USE_LOCAL_ENV=true の場合は環境変数/.envから直接読み込む。
    """

    def __init__(self):
        self._cache: dict[str, tuple[str, float]] = {}
        self._cache_ttl = 300  # 5 minutes
        self._sm_client = None

    def _get_sm_client(self):
        if self._sm_client is None:
            from google.cloud import secretmanager
            self._sm_client = secretmanager.SecretManagerServiceClient()
        return self._sm_client

    def _get_from_cache(self, key: str) -> Optional[str]:
        if key in self._cache:
            value, ts = self._cache[key]
            if time.time() - ts < self._cache_ttl:
                return value
            del self._cache[key]
        return None

    def _set_cache(self, key: str, value: str):
        self._cache[key] = (value, time.time())

    async def get_secret(self, secret_id: str) -> Optional[str]:
        """シークレット値を取得する。キャッシュがあればキャッシュから返す。"""
        if settings.use_local_env:
            return self._get_local_env(secret_id)

        cached = self._get_from_cache(secret_id)
        if cached is not None:
            return cached

        try:
            client = self._get_sm_client()
            name = f"projects/{settings.gcp_project_id}/secrets/{secret_id}/versions/latest"
            response = client.access_secret_version(request={"name": name})
            value = response.payload.data.decode("utf-8")
            self._set_cache(secret_id, value)
            return value
        except Exception:
            return None

    async def set_secret(self, secret_id: str, value: str) -> bool:
        """シークレットに新しいバージョンを追加する。"""
        if settings.use_local_env:
            # ローカルモードでは環境変数を更新できないため、キャッシュのみ更新
            self._set_cache(secret_id, value)
            return True

        try:
            client = self._get_sm_client()
            parent = f"projects/{settings.gcp_project_id}/secrets/{secret_id}"

            # シークレットが存在しない場合は作成
            try:
                client.get_secret(request={"name": parent})
            except Exception:
                client.create_secret(
                    request={
                        "parent": f"projects/{settings.gcp_project_id}",
                        "secret_id": secret_id,
                        "secret": {"replication": {"automatic": {}}},
                    }
                )

            client.add_secret_version(
                request={
                    "parent": parent,
                    "payload": {"data": value.encode("utf-8")},
                }
            )
            self._set_cache(secret_id, value)
            return True
        except Exception:
            return False

    async def get_google_api_key(self) -> Optional[str]:
        return await self.get_secret(settings.secret_id_google_key)

    async def get_openai_api_key(self) -> Optional[str]:
        return await self.get_secret(settings.secret_id_openai_key)

    async def get_admin_password(self) -> Optional[str]:
        return await self.get_secret(settings.secret_id_admin_password)

    async def get_drive_folder_id(self) -> Optional[str]:
        value = await self.get_secret(settings.secret_id_drive_folder)
        return value or settings.drive_folder_id

    async def check_keys_configured(self) -> dict[str, bool]:
        """各APIキーの設定状態を確認する（値は返さない）。"""
        google_key = await self.get_google_api_key()
        openai_key = await self.get_openai_api_key()
        return {
            "google_api_key": bool(google_key),
            "openai_api_key": bool(openai_key),
        }

    async def get_key_preview(self, secret_id: str) -> str:
        """キーの末尾4文字をマスク表示用に取得する。"""
        value = await self.get_secret(secret_id)
        if not value:
            return ""
        if len(value) <= 4:
            return "****"
        return "..." + value[-4:]

    def _get_local_env(self, secret_id: str) -> Optional[str]:
        """ローカル開発時: secret_id から対応する環境変数値を返す。"""
        # まずキャッシュを確認（ローカルモードでの set_secret 対応）
        cached = self._get_from_cache(secret_id)
        if cached is not None:
            return cached

        mapping = {
            settings.secret_id_google_key: settings.google_api_key,
            settings.secret_id_openai_key: settings.openai_api_key,
            settings.secret_id_admin_password: settings.admin_password,
            settings.secret_id_drive_folder: settings.drive_folder_id,
        }
        value = mapping.get(secret_id)
        return value if value else None


# シングルトンインスタンス
secret_manager = SecretManagerClient()
