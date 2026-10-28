import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")


@dataclass(frozen=True)
class Settings:
    openai_key: str = os.getenv("OPENAI_API_KEY", "")
    menu_model: str = os.getenv("OPENAI_MENU_MODEL", "gpt-6-luna")
    image_model: str = os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-2.5-flare")
    data_dir: Path = Path(os.getenv("DATA_DIR", str(Path(__file__).parent / "data")))
    secure_cookies: bool = os.getenv("SECURE_COOKIES", "false").lower() == "true"
    daily_scan_limit: int = int(os.getenv("DAILY_SCAN_LIMIT", "100"))
    daily_image_limit: int = int(os.getenv("DAILY_IMAGE_LIMIT", "100"))


settings = Settings()
