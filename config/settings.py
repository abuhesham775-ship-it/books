"""
Settings Module - إعدادات المشروع
إدارة جميع المتغيرات البيئية والإعدادات
"""
from typing import Optional


class Settings(BaseSettings):
    """إعدادات المشروع"""

    # Telegram Configuration
    telegram_bot_token: str
    telegram_admin_id: Optional[int] = None

    # Database Configuration
    database_url: str

    # OpenRouter AI API
    openrouter_api_key: Optional[str] = None
    ai_model: str = "openai/gpt-3.5-turbo"

    # FastAPI Configuration
    fastapi_host: str = "0.0.0.0"
    fastapi_port: int = 8000
    debug: bool = False
    log_level: str = "INFO"

    # Redis Configuration (optional for FSM)
    redis_url: Optional[str] = None

    # Upload Settings
    upload_folder: str = "uploads"
    max_file_size: int = 100 * 1024 * 1024  # 100MB
    allowed_extensions: list = ["pdf", "epub", "fb2", "mobi", "txt"]

    # Points System
    points_per_referral: int = 50
    points_per_download: int = 5
    points_per_review: int = 10
    points_to_deduct: int = 10

    # AI Settings
    embedding_model: str = "text-embedding-3-small"
    max_tokens: int = 1000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    def is_owner(self, telegram_id: int) -> bool:
        """التحقق من أن المستخدم هو المالك"""
        return self.telegram_admin_id is not None and telegram_id == self.telegram_admin_id


@lru_cache()
def get_settings() -> Settings:
    """الحصول على الإعدادات المحفوظة"""
    return Settings()
