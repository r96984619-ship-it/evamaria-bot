import logging
import logging.handlers
import os
from pyrogram import Client
from pyrogram.errors import (
    FloodWait,
    AccessTokenInvalid,
    AccessTokenExpired,
    ApiIdInvalid,
    AuthKeyUnregistered,
)
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
            # in_memory=True avoids SQLite session files on Railway's ephemeral
            # filesystem. Each restart does a fresh Telegram auth — correct for
            # containerised/serverless deployments where the disk resets.
            in_memory=True,
        )

    async def start(self):
        setup_logging()
        logger.info("Starting EvaMariaBot...")

        # Connect to database
        await connect_db(Var.DATABASE_URI, Var.DATABASE_NAME)

        # Load rotating start images
        if Var.START_IMG_URL:
            utils.START_IMGS.extend(Var.START_IMG_URL)

        try:
            await super().start()
        except AccessTokenInvalid:
            logger.critical(
                "BOT_TOKEN is invalid. Go to @BotFather on Telegram, copy the "
                "token for your bot, and update the BOT_TOKEN variable in "
                "Railway → Variables. Then redeploy."
            )
            raise
        except AccessTokenExpired:
            logger.critical(
                "BOT_TOKEN has been revoked. Open @BotFather, use /revoke on "
                "your bot to generate a new token, update BOT_TOKEN in Railway, "
                "then redeploy."
            )
            raise
        except ApiIdInvalid:
            logger.critical(
                "API_ID or API_HASH is wrong. Visit https://my.telegram.org/apps "
                "to get your correct credentials and update them in Railway → Variables."
            )
            raise
        except AuthKeyUnregistered:
            logger.critical(
                "Auth key unregistered — the session was invalidated by Telegram. "
                "This is automatically handled with in_memory=True. If this error "
                "persists, verify your API_ID / API_HASH at https://my.telegram.org/apps."
            )
            raise

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
