"""Configuration loading from environment variables."""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


def _get_required(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise ValueError(f"Required environment variable '{key}' is not set.")
    return value


def _get_admin_ids() -> list[int]:
    raw = os.getenv("ADMIN_IDS", "")
    if not raw.strip():
        return []
    return [int(x.strip()) for x in raw.split(",") if x.strip().isdigit()]


MAIN_BOT_TOKEN: str = _get_required("MAIN_BOT_TOKEN")
ADMIN_BOT_TOKEN: str = _get_required("ADMIN_BOT_TOKEN")
ADMIN_IDS: list[int] = _get_admin_ids()
BOT_USERNAME: str = os.getenv("BOT_USERNAME", "")
DATA_DIR: Path = Path(os.getenv("DATA_DIR", "./data"))
