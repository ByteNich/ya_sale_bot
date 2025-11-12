"""Configuration module for Yandex Market Discount Bot."""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings."""

    # Telegram
    BOT_TOKEN: str
    ADMIN_IDS: str

    # Database
    DATABASE_URL: str

    # Parser
    CHECK_INTERVAL: int = 120  # seconds
    DISCOUNT_THRESHOLD: int = 10  # percentage
    USER_AGENT: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

    # Railway
    PORT: int = 8000

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def admin_list(self) -> List[int]:
        """Parse admin IDs from comma-separated string."""
        return [int(id.strip()) for id in self.ADMIN_IDS.split(",") if id.strip()]


settings = Settings()
