#!/usr/bin/env python3
"""Entry point for EvaMariaBot."""
import asyncio
import logging
import sys
import os

logger = logging.getLogger(__name__)

REQUIRED_VARS = ["BOT_TOKEN", "API_ID", "API_HASH"]


def validate_env() -> bool:
    """Check required env vars are present and valid. Returns True if OK."""
    ok = True

    missing = [v for v in REQUIRED_VARS if not os.environ.get(v, "").strip()]
    if missing:
        print(f"[FATAL] Missing required environment variables: {', '.join(missing)}")
        print("        Set them in Railway → Variables tab and redeploy.")
        ok = False

    api_id = os.environ.get("API_ID", "")
    if api_id and not api_id.strip().lstrip("-").isdigit():
        print(f"[FATAL] API_ID must be a plain number (e.g. 12345678), got: {api_id!r}")
        ok = False

    token = os.environ.get("BOT_TOKEN", "")
    if token and (":" not in token or len(token) < 20):
        print("[FATAL] BOT_TOKEN looks invalid. Get it from @BotFather on Telegram.")
        ok = False

    if ok:
        print("[OK] Environment validated — all required variables present")
    return ok


async def main():
    if not validate_env():
        sys.exit(1)

    # Import Bot inside async context so Pyrogram's event loop setup works
    # correctly on Python 3.10+ (avoids 'no current event loop' RuntimeError)
    from bot import Bot
    bot = Bot()
    await bot.start()

    logger.info("EvaMariaBot is running. Press Ctrl+C to stop.")
    try:
        await asyncio.Event().wait()  # run forever until interrupted
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        await bot.stop()


if __name__ == "__main__":
    asyncio.run(main())
