import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


BYBIT_DEMO_API_KEY = os.getenv("BYBIT_DEMO_API_KEY")
BYBIT_DEMO_API_SECRET = os.getenv("BYBIT_DEMO_API_SECRET")

SYMBOL = os.getenv("SYMBOL", "BTCUSDT")
CATEGORY = os.getenv("CATEGORY", "linear")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

OPENAI_MODEL = os.getenv(
    "OPENAI_MODEL",
    "gpt-5.6-luna",
)

LLM_PROVIDER = os.getenv(
    "LLM_PROVIDER",
    "lmstudio",
)

LM_STUDIO_BASE_URL = os.getenv(
    "LM_STUDIO_BASE_URL",
    "http://localhost:1234/v1",
)

LM_STUDIO_MODEL = os.getenv(
    "LM_STUDIO_MODEL",
)

GROQ_API_KEY = os.getenv(
    "GROQ_API_KEY",
)

GROQ_MODEL = os.getenv(
    "GROQ_MODEL",
    "openai/gpt-oss-20b",
)

GROQ_BASE_URL = os.getenv(
    "GROQ_BASE_URL",
    "https://api.groq.com/openai/v1",
)

def validate_settings():
    if not BYBIT_DEMO_API_KEY:
        raise RuntimeError("BYBIT_DEMO_API_KEY is missing.")

    if not BYBIT_DEMO_API_SECRET:
        raise RuntimeError("BYBIT_DEMO_API_SECRET is missing.")
    
def validate_openai_settings():
    if not OPENAI_API_KEY:
        raise RuntimeError(
            "OPENAI_API_KEY is missing."
        )

    if not OPENAI_MODEL:
        raise RuntimeError(
            "OPENAI_MODEL is missing."
        )
    
def validate_lmstudio_settings():
    if not LM_STUDIO_BASE_URL:
        raise RuntimeError(
            "LM_STUDIO_BASE_URL is missing."
        )

    if not LM_STUDIO_MODEL:
        raise RuntimeError(
            "LM_STUDIO_MODEL is missing."
        )

def validate_groq_settings():
    if not GROQ_API_KEY:
        raise RuntimeError(
            "GROQ_API_KEY is missing."
        )

    if not GROQ_MODEL:
        raise RuntimeError(
            "GROQ_MODEL is missing."
        )

    if not GROQ_BASE_URL:
        raise RuntimeError(
            "GROQ_BASE_URL is missing."
        )
    
def validate_bybit_demo_settings():
    if not BYBIT_DEMO_API_KEY:
        raise RuntimeError(
            "BYBIT_DEMO_API_KEY is missing."
        )

    if not BYBIT_DEMO_API_SECRET:
        raise RuntimeError(
            "BYBIT_DEMO_API_SECRET is missing."
        )