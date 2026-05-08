import os
from os import environ

class Var:
    # Bot credentials
    BOT_TOKEN = environ.get("BOT_TOKEN", "")
    API_ID = int(environ.get("API_ID", 0))
    API_HASH = environ.get("API_HASH", "")

    # Database
    DATABASE_URI = environ.get("DATABASE_URI", "")  # if empty, uses in-memory mock
    DATABASE_NAME = environ.get("DATABASE_NAME", "EvaMaria")

    # Channels / auth
    AUTH_CHANNEL = int(environ.get("AUTH_CHANNEL", 0))  # 0 = no subscription check
    AUTH_USERS = list(map(int, environ.get("AUTH_USERS", "").split() if environ.get("AUTH_USERS") else []))
    ADMINS = list(map(int, environ.get("ADMINS", "").split() if environ.get("ADMINS") else []))
    CHANNELS = list(map(int, environ.get("CHANNELS", "0").split()))

    # Bot identity
    BOT_NAME = environ.get("BOT_NAME", "EvaMariaBot")
    BOT_USERNAME = environ.get("BOT_USERNAME", "")

    # Start images (rotating)
    START_IMG_URL = environ.get("START_IMG_URL", "").split()

    # Caption templates
    FILE_CAPTION = environ.get("FILE_CAPTION", "{file_name}\n\n📁 Size: {file_size}\n🕒 Duration: {duration}")
    BATCH_FILE_CAPTION = environ.get("BATCH_FILE_CAPTION", "{file_name}")

    # Feature flags
    PROTECT_CONTENT = environ.get("PROTECT_CONTENT", "false").lower() == "true"
    SPELL_CHECK_REPLY = environ.get("SPELL_CHECK_REPLY", "false").lower() == "true"
    MAX_LIST_ELM = int(environ.get("MAX_LIST_ELM", 50))
    PM_MODE = environ.get("PM_MODE", "false").lower() == "true"
    SINGLE_BUTTON = environ.get("SINGLE_BUTTON", "false").lower() == "true"
    IMDB_TEMPLATE = environ.get(
        "IMDB_TEMPLATE",
        "🎬 <b>{title}</b> ({year})\n⭐ Rating: {rating}\n🎭 Genre: {genres}\n🎥 Director: {director}\n👥 Cast: {cast}"
    )

    # Logging
    LOG_CHANNEL = int(environ.get("LOG_CHANNEL", 0))
    PORT = int(environ.get("PORT", 8080))
