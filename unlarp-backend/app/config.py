"""App settings, read from environment variables (see .env.example)."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings:
    def __init__(self) -> None:
        self.secret_key: str = os.getenv("UNLARP_SECRET_KEY", "dev-only-change-me")
        self.database_url: str = os.getenv(
            "UNLARP_DATABASE_URL", f"sqlite:///{BASE_DIR / 'unlarp.db'}"
        )
        self.media_dir: Path = Path(os.getenv("UNLARP_MEDIA_DIR", BASE_DIR / "media"))
        # Each generated image costs money, so free users get a daily cap.
        self.daily_generation_limit: int = int(
            os.getenv("UNLARP_DAILY_GENERATION_LIMIT", "5")
        )
        self.token_expire_minutes: int = int(
            os.getenv("UNLARP_TOKEN_EXPIRE_MINUTES", str(60 * 24 * 7))
        )
        self.max_selfie_bytes: int = 10 * 1024 * 1024
        self.max_selfies_per_user: int = 10


settings = Settings()
