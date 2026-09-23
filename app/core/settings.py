import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]

load_dotenv(BASE_DIR / ".env", override=False)
ENV = os.getenv("ENV", "dev")
load_dotenv(BASE_DIR / f".env.{ENV}", override=False)


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is not configured")
    return value


def _positive_int(name: str, default: int) -> int:
    raw_value = os.getenv(name, str(default)).strip()
    try:
        value = int(raw_value)
    except ValueError as exception:
        raise RuntimeError(f"{name} must be an integer") from exception
    if value <= 0:
        raise RuntimeError(f"{name} must be positive")
    return value


DATABASE_URL = _required("DATABASE_URL")
SECRET_KEY = _required("SECRET_KEY")
SQL_ECHO = os.getenv("SQL_ECHO", "false").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}

ACCESS_TOKEN_EXPIRY_MINUTES = _positive_int("ACCESS_TOKEN_EXPIRY_MINUTES", 15)
REFRESH_TOKEN_INACTIVITY_DAYS = _positive_int("REFRESH_TOKEN_INACTIVITY_DAYS", 30)
TIDE_DEFAULT_DATA_LIMIT = _positive_int("TIDE_DEFAULT_DATA_LIMIT", 100)
TIDE_MAX_DATA_LIMIT = _positive_int("TIDE_MAX_DATA_LIMIT", 500)
TIDE_MAX_MUTATIONS_PER_REQUEST = _positive_int(
    "TIDE_MAX_MUTATIONS_PER_REQUEST",
    100,
)
TIDE_MAX_REQUEST_BYTES = _positive_int("TIDE_MAX_REQUEST_BYTES", 2 * 1024 * 1024)

if TIDE_DEFAULT_DATA_LIMIT > TIDE_MAX_DATA_LIMIT:
    raise RuntimeError("TIDE_DEFAULT_DATA_LIMIT cannot exceed TIDE_MAX_DATA_LIMIT")

if "CHANGE_ME" in DATABASE_URL:
    raise RuntimeError("DATABASE_URL still contains a CHANGE_ME placeholder")
if SECRET_KEY.startswith("CHANGE_ME"):
    raise RuntimeError("SECRET_KEY still contains a CHANGE_ME placeholder")
if len(SECRET_KEY) < 64:
    raise RuntimeError("SECRET_KEY must contain at least 64 characters")
