#!/usr/bin/env python3
"""Entry point for EvaMariaBot."""
import asyncio
import logging
import sys
import os

# Disable stdout buffering immediately so all output appears in Railway logs
# in the correct order alongside Pyrogram's logging output.
# You can also achieve this by setting PYTHONUNBUFFERED=1 in Railway Variables.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)

# Bootstrap logging before anything else so even early failures are visible.
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

REQUIRED_VARS = ["BOT_TOKEN", "API_ID", "API_HASH"]


def validate_env() -> bool:
    """Check required env vars are present and valid. Returns True if OK."""
    ok = True

    missing = [v for v in REQUIRED_VARS if not os.environ.get(v, "").strip()]
    if missing:
        logger.critical("Missing required environment variables: %s", ", ".join(missing))
        logger.critical("Go to Railway → your service → Variables and add them, then redeploy.")
        ok = False

    api_id = os.environ.get("API_ID", "")
    if api_id and not api_id.strip().lstrip("-").isdigit():
        logger.critical("API_ID must be a plain integer (e.g. 12345678), got: %r", api_id)
        ok = False

    token = os.environ.get("BOT_TOKEN", "")
    if token and (":" not in token or len(token) < 20):
        logger.critical(
            "BOT_TOKEN looks invalid (got %r). Get the correct token from @BotFather.", token[:10] + "..."
        )
        ok = False

    if ok:
        logger.info("Environment validated — all required variables present.")
    return ok


async def main():
    if not validate_env():
        sys.exit(1)

    # Import Bot inside async context so Pyrogram's event loop setup works
    # correctly on Python 3.10+ (avoids 'no current event loop' RuntimeError).
    from bot import Bot
    bot = Bot()

    try:
        await bot.start()
    except Exception as e:
        # bot/__init__.py already logs a descriptive CRITICAL message for known
        # Pyrogram auth errors. This catches anything else.
        logger.critical(
            "Bot failed to start: [%s] %s",
            type(e).__name__, e,
            exc_info=True,
        )
        logger.critical(
            "--------------------------------------------------------------------------\n"
            "COMMON FIXES:\n"
            "  BOT_TOKEN invalid/revoked → regenerate via @BotFather and update Railway\n"
            "  API_ID / API_HASH wrong   → check https://my.telegram.org/apps\n"
            "  MongoDB URI wrong         → check DATABASE_URI in Railway Variables\n"
            "--------------------------------------------------------------------------"
        )
        sys.exit(1)

    logger.info("EvaMariaBot is running. Press Ctrl+C to stop.")
    try:
        await asyncio.Event().wait()  # run forever until interrupted
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        await bot.stop()


if __name__ == "__main__":
    asyncio.run(main())
