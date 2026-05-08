#!/usr/bin/env python3
"""Entry point for EvaMariaBot."""
import asyncio
import logging

from bot import Bot

logger = logging.getLogger(__name__)


async def main():
    bot = Bot()
    await bot.start()
    logger.info("Bot is running. Press Ctrl+C to stop.")
    try:
        await asyncio.Event().wait()  # run forever
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        await bot.stop()


if __name__ == "__main__":
    asyncio.run(main())
