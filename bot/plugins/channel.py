"""Channel/group indexing from forwarded messages or Telegram links."""
import re
import logging
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait, ChatAdminRequired, ChannelPrivate

from bot.config import Var
from bot.database import save_file
from bot.utils import extract_file_info, MEDIA_TYPES

logger = logging.getLogger(__name__)

LINK_RE = re.compile(r"https?://t\.me/(?:c/)?([^/]+)/(\d+)")


def is_admin(user_id: int) -> bool:
    return user_id in Var.ADMINS or user_id in Var.AUTH_USERS


@Client.on_message(filters.command("index") & filters.private)
async def index_command(client: Client, message: Message):
    """Index media from a channel link or a range of messages."""
    if not message.from_user or not is_admin(message.from_user.id):
        return await message.reply("❌ Only admins can index channels.")

    if len(message.command) < 2:
        return await message.reply(
            "Usage:\n"
            "• <code>/index https://t.me/channel/123</code> — index single message\n"
            "• <code>/index https://t.me/channel/1 100</code> — index range 1-100"
        )

    args = message.command[1:]
    link = args[0]
    match = LINK_RE.match(link)
    if not match:
        return await message.reply("❌ Invalid Telegram link.")

    chat_ref = match.group(1)
    start_id = int(match.group(2))
    end_id = int(args[1]) if len(args) > 1 else start_id

    if start_id > end_id:
        start_id, end_id = end_id, start_id

    count = end_id - start_id + 1
    if count > 500:
        return await message.reply("❌ Max 500 messages per index request.")

    status_msg = await message.reply(f"⏳ Indexing {count} message(s)...")
    indexed = 0
    duplicates = 0
    skipped = 0

    for msg_id in range(start_id, end_id + 1):
        try:
            msg = await client.get_messages(chat_ref, msg_id)
        except FloodWait as fw:
            await asyncio.sleep(fw.value)
            try:
                msg = await client.get_messages(chat_ref, msg_id)
            except Exception:
                skipped += 1
                continue
        except (ChatAdminRequired, ChannelPrivate):
            await status_msg.edit("❌ Bot lacks access to this channel. Make sure it's added as admin.")
            return
        except Exception as e:
            logger.warning("Failed to fetch message %s/%s: %s", chat_ref, msg_id, e)
            skipped += 1
            continue

        if not msg or msg.empty:
            skipped += 1
            continue

        info = extract_file_info(msg)
        if not info:
            skipped += 1
            continue

        is_new, _ = await save_file(info)
        if is_new:
            indexed += 1
        else:
            duplicates += 1

        if (indexed + duplicates + skipped) % 20 == 0:
            try:
                await status_msg.edit(
                    f"⏳ Progress: {indexed + duplicates + skipped}/{count}\n"
                    f"✅ Indexed: {indexed} | ♻️ Duplicates: {duplicates} | ⏭ Skipped: {skipped}"
                )
            except Exception:
                pass

        await asyncio.sleep(0.1)

    await status_msg.edit(
        f"✅ <b>Indexing Complete!</b>\n\n"
        f"📥 New files: <b>{indexed}</b>\n"
        f"♻️ Duplicates: <b>{duplicates}</b>\n"
        f"⏭ Skipped: <b>{skipped}</b>"
    )


@Client.on_message(
    filters.forwarded
    & (filters.document | filters.video | filters.audio | filters.voice | filters.animation)
    & filters.private
)
async def index_forwarded(client: Client, message: Message):
    """Index a single forwarded media message."""
    if not message.from_user or not is_admin(message.from_user.id):
        return

    info = extract_file_info(message)
    if not info:
        return await message.reply("❌ Unsupported media type.")

    is_new, file_id = await save_file(info)
    if is_new:
        await message.reply(
            f"✅ File indexed!\n"
            f"📄 Name: <code>{info['file_name']}</code>\n"
            f"🆔 File ID: <code>{file_id}</code>"
        )
    else:
        await message.reply("♻️ This file is already in the database (duplicate).")


@Client.on_message(
    (filters.document | filters.video | filters.audio | filters.voice | filters.animation)
    & filters.channel
)
async def auto_index_channel(client: Client, message: Message):
    """Automatically index media posted in configured channels."""
    if message.chat and message.chat.id in Var.CHANNELS:
        info = extract_file_info(message)
        if info:
            await save_file(info)
            logger.debug("Auto-indexed: %s from channel %s", info.get("file_name"), message.chat.id)
