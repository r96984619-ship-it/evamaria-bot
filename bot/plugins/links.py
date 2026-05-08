"""Link generation: single file and batch links."""
import base64
import json
import logging
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from bot.config import Var
from bot.database import save_file, get_file
from bot.utils import extract_file_info, get_size, get_duration

logger = logging.getLogger(__name__)


def make_file_link(file_id: str) -> str:
    bot_username = Var.BOT_USERNAME or "YourBot"
    return f"https://t.me/{bot_username}?start=file_{file_id}"


def make_batch_link(file_ids: list) -> str:
    bot_username = Var.BOT_USERNAME or "YourBot"
    payload = base64.urlsafe_b64encode(json.dumps({"ids": file_ids}).encode()).decode().rstrip("=")
    return f"https://t.me/{bot_username}?start=batch_{payload}"


@Client.on_message(filters.command("link") & filters.private)
async def get_link(client: Client, message: Message):
    """Generate a shareable link for a forwarded file."""
    if not message.reply_to_message:
        return await message.reply("Reply to a media message with /link to generate a link.")

    rm = message.reply_to_message
    info = extract_file_info(rm)
    if not info:
        return await message.reply("❌ Unsupported or no media in the replied message.")

    is_new, file_id = await save_file(info)
    link = make_file_link(file_id)
    status = "✅ New file indexed!" if is_new else "♻️ File already indexed."

    await message.reply(
        f"{status}\n\n"
        f"📄 <b>{info['file_name']}</b>\n"
        f"📁 Size: {get_size(info.get('file_size', 0))}\n\n"
        f"🔗 <b>Link:</b>\n<code>{link}</code>",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("📥 Get File", url=link)
        ]])
    )


@Client.on_message(filters.command("batch") & filters.private)
async def batch_link(client: Client, message: Message):
    """Start batch link collection. /batch to begin, then forward files, then /done."""
    user_id = message.from_user.id
    from bot import batch_sessions
    if user_id in batch_sessions:
        return await message.reply(
            "⚠️ You already have an active batch session.\n"
            "Forward files and type /done to finish, or /cancel to abort."
        )
    batch_sessions[user_id] = []
    await message.reply(
        "📦 <b>Batch Session Started!</b>\n\n"
        "Now forward the files you want to include.\n"
        "Type /done when finished or /cancel to abort."
    )


@Client.on_message(
    filters.private
    & (filters.document | filters.video | filters.audio | filters.voice | filters.animation)
)
async def collect_batch_files(client: Client, message: Message):
    """Collect files during an active batch session."""
    from bot import batch_sessions
    user_id = message.from_user.id
    if user_id not in batch_sessions:
        return  # not in batch mode

    info = extract_file_info(message)
    if not info:
        return await message.reply("❌ Unsupported media type, skipped.")

    is_new, file_id = await save_file(info)
    batch_sessions[user_id].append(file_id)
    count = len(batch_sessions[user_id])
    await message.reply(f"✅ File {count} added: <code>{info['file_name']}</code>")


@Client.on_message(filters.command("done") & filters.private)
async def done_batch(client: Client, message: Message):
    from bot import batch_sessions
    user_id = message.from_user.id
    if user_id not in batch_sessions:
        return await message.reply("No active batch session.")

    file_ids = batch_sessions.pop(user_id)
    if not file_ids:
        return await message.reply("⚠️ No files collected.")

    link = make_batch_link(file_ids)
    await message.reply(
        f"📦 <b>Batch Link Generated!</b>\n"
        f"Contains <b>{len(file_ids)}</b> file(s)\n\n"
        f"🔗 <b>Link:</b>\n<code>{link}</code>",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("📥 Get Files", url=link)
        ]])
    )


@Client.on_message(filters.command("cancel") & filters.private)
async def cancel_batch(client: Client, message: Message):
    from bot import batch_sessions
    user_id = message.from_user.id
    batch_sessions.pop(user_id, None)
    await message.reply("❌ Batch session cancelled.")
