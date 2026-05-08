import os
from os import environ


def _parse_ints(env_key: str, default: str = "") -> list:
    """Parse space-separated integers, silently skipping invalid values."""
    raw = environ.get(env_key, default).strip()
    if not raw:
        return []
    result = []
    for val in raw.split():
        try:
            result.append(int(val))
        except ValueError:
            pass  # skip placeholders like -100xxxxxxxxxx
    return result


def _parse_int(env_key: str, default: int = 0) -> int:
    """Parse a single integer, returning default on failure."""
    try:
        return int(environ.get(env_key, str(default)))
    except ValueError:
        return default


class Var:
    # Bot credentials
    BOT_TOKEN = environ.get("BOT_TOKEN", "")
    API_ID = _parse_int("API_ID", 0)
    API_HASH = environ.get("API_HASH", "")

    # Database
    DATABASE_URI = environ.get("DATABASE_URI", "")  # empty = in-memory mock
    DATABASE_NAME = environ.get("DATABASE_NAME", "EvaMaria")

    # Channels / auth
    AUTH_CHANNEL = _parse_int("AUTH_CHANNEL", 0)   # 0 = no subscription check
    AUTH_USERS = _parse_ints("AUTH_USERS")
    ADMINS = _parse_ints("ADMINS")
    CHANNELS = _parse_ints("CHANNELS")              # channels to auto-index

    # Bot identity
    BOT_NAME = environ.get("BOT_NAME", "EvaMariaBot")
    BOT_USERNAME = environ.get("BOT_USERNAME", "")

    # Start images (rotating)
    START_IMG_URL = environ.get("START_IMG_URL", "").split()

    # Caption templates
    FILE_CAPTION = environ.get(
        "FILE_CAPTION",
        "{file_name}\n\n📁 Size: {file_size}\n🕒 Duration: {duration}"
    )
    BATCH_FILE_CAPTION = environ.get("BATCH_FILE_CAPTION", "{file_name}")

    # Feature flags
    PROTECT_CONTENT = environ.get("PROTECT_CONTENT", "false").lower() == "true"
    SPELL_CHECK_REPLY = environ.get("SPELL_CHECK_REPLY", "false").lower() == "true"
    MAX_LIST_ELM = _parse_int("MAX_LIST_ELM", 50)
    PM_MODE = environ.get("PM_MODE", "false").lower() == "true"
    SINGLE_BUTTON = environ.get("SINGLE_BUTTON", "false").lower() == "true"
    IMDB_TEMPLATE = environ.get(
        "IMDB_TEMPLATE",
        "🎬 <b>{title}</b> ({year})\n⭐ Rating: {rating}\n🎭 Genre: {genres}\n🎥 Director: {director}\n👥 Cast: {cast}"
    )

    # Logging
    LOG_CHANNEL = _parse_int("LOG_CHANNEL", 0)
    PORT = _parse_int("PORT", 8080)
