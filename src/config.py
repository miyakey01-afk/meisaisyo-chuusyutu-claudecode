from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # GCP Project ID (required for Secret Manager)
    gcp_project_id: str = ""

    # Local development mode: skip Secret Manager, use env vars directly
    use_local_env: bool = False

    # API keys (used when use_local_env=True)
    google_api_key: str = ""
    openai_api_key: str = ""

    # Admin password (used when use_local_env=True or as initial fallback)
    admin_password: str = ""

    # App settings
    max_file_count: int = 10
    output_filename: str = "明細書EXCEL出力"

    # Google Drive
    drive_folder_id: str = "1BsdbbCisTpP7mxzOuDSnASxpEqGTdcEL"

    # Secret Manager secret IDs
    secret_id_google_key: str = "meisaisyo-google-api-key"
    secret_id_openai_key: str = "meisaisyo-openai-api-key"
    secret_id_admin_password: str = "meisaisyo-admin-password"
    secret_id_drive_folder: str = "meisaisyo-drive-folder-id"

    # Session
    session_secret_key: str = "change-me-in-production"
    session_max_age: int = 86400  # 24 hours

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
