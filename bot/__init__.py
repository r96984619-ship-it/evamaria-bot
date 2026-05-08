import logging
import logging.handlers
import os
from pyrogram import Client
from pyrogram.errors import FloodWait
import asyncio

from bot.config import Var
from bot.database import connect_db
from bot import utils

logger = logging.getLogger(__name__)

# Global batch session store: {user_id: [file_ids]}
batch_sessions: dict = {}


def setup_logging():
    fmt = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    root.addHandler(sh)

    fh = logging.handlers.RotatingFileHandler("bot.log", maxBytes=5 * 1024 * 1024, backupCount=2)
    fh.setFormatter(fmt)
    root.addHandler(fh)


class Bot(Client):
    def __init__(self):
        super().__init__(
            "EvaMaria",
            api_id=Var.API_ID,
            api_hash=Var.API_HASH,
            bot_token=Var.BOT_TOKEN,
            plugins=dict(root="bot/plugins"),
            sleep_threshold=60,
        )

    async def start(self):
        setup_logging()
        logger.info("Starting EvaMariaBot...")

        # Connect to database
        await connect_db(Var.DATABASE_URI, Var.DATABASE_NAME)

        # Load rotating start images
        if Var.START_IMG_URL:
            utils.START_IMGS.extend(Var.START_IMG_URL)

        await super().start()

        me = await self.get_me()
        # Patch BOT_USERNAME at runtime
        Var.BOT_USERNAME = me.username or Var.BOT_USERNAME
        logger.info("Bot started as @%s (ID: %s)", me.username, me.id)

        if Var.LOG_CHANNEL:
            try:
                await self.send_message(Var.LOG_CHANNEL, f"✅ **{Var.BOT_NAME}** started successfully!")
            except Exception as e:
                logger.warning("Could not send startup message to log channel: %s", e)

    async def stop(self, *args):
        logger.info("Bot stopping...")
        await super().stop()
        logger.info("Bot stopped.")
