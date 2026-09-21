import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


BYBIT_DEMO_API_KEY = os.getenv("BYBIT_DEMO_API_KEY")
BYBIT_DEMO_API_SECRET = os.getenv("BYBIT_DEMO_API_SECRET")

SYMBOL = os.getenv("SYMBOL", "BTCUSDT")
CATEGORY = os.getenv("CATEGORY", "linear")


def validate_settings():
    if not BYBIT_DEMO_API_KEY:
        raise RuntimeError("BYBIT_DEMO_API_KEY is missing.")

    if not BYBIT_DEMO_API_SECRET:
        raise RuntimeError("BYBIT_DEMO_API_SECRET is missing.")