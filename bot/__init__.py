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

    # Only add handlers if none exist yet (main.py may have set one up already)
    if not root.handlers:
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
        logger.info("API_ID: %s | BOT_TOKEN prefix: %s", Var.API_ID, Var.BOT_TOKEN[:10] + "..." if Var.BOT_TOKEN else "MISSING")

        # Connect to database
        await connect_db(Var.DATABASE_URI, Var.DATABASE_NAME)

        # Load rotating start images
        if Var.START_IMG_URL:
            utils.START_IMGS.extend(Var.START_IMG_URL)

        try:
            await super().start()
        except AccessTokenInvalid:
            logger.critical(
                "BOT_TOKEN is invalid — Telegram rejected it.\n"
                "  → Open @BotFather on Telegram\n"
                "  → Find your bot, use /token to get the current token\n"
                "  → Copy it exactly and update BOT_TOKEN in Railway → Variables\n"
                "  → Redeploy"
            )
            raise
        except AccessTokenExpired:
            logger.critical(
                "BOT_TOKEN has been revoked by Telegram.\n"
                "  → Open @BotFather → /mybots → your bot → API Token → Revoke\n"
                "  → Copy the new token and update BOT_TOKEN in Railway → Variables\n"
                "  → Redeploy"
            )
            raise
        except ApiIdInvalid:
            logger.critical(
                "API_ID or API_HASH is wrong.\n"
                "  → Visit https://my.telegram.org/apps\n"
                "  → Copy your App api_id and api_hash\n"
                "  → Update API_ID and API_HASH in Railway → Variables\n"
                "  → Redeploy"
            )
            raise
        except AuthKeyUnregistered:
            logger.critical(
                "Auth key was invalidated by Telegram (should not happen with in_memory=True).\n"
                "  → Verify API_ID and API_HASH at https://my.telegram.org/apps\n"
                "  → Redeploy"
            )
            raise

        try:
            me = await self.get_me()
        except Exception as e:
            logger.critical("get_me() failed after successful auth — unexpected error: %s", e)
            raise

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
