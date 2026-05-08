import asyncio
import logging
import random
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated

from bot.config import Var
from bot.database import (
    add_user, add_chat, is_user_exist,
    get_file, is_banned, get_connection,
)
from bot.utils import next_start_img, get_size, get_duration

logger = logging.getLogger(__name__)

PRIVATE_START_TEXT = (
    "👋 <b>Hello {name}!</b>\n\n"
    "I am <b>{bot_name}</b> — a powerful media search bot.\n\n"
    "🔍 Search for movies, series, and files in inline mode.\n"
    "📥 Receive files directly in PM.\n\n"
    "➕ <b>Add me to your group</b> to enable auto media search!"
)

GROUP_START_TEXT = (
    "👋 <b>Hey {name}!</b>\n\n"
    "Use me in <b>inline mode</b> to search files:\n"
    "<code>@{bot_username} movie name</code>\n\n"
    "Or just type a movie/file name here for auto-search!"
)

HELP_TEXT = (
    "<b>📚 Help Menu</b>\n\n"
    "<b>User Commands:</b>\n"
    "• /start — Welcome message\n"
    "• /help — This menu\n"
    "• /about — About the bot\n"
    "• /search &lt;query&gt; — Search for movies (IMDb)\n"
    "• /imdb &lt;query&gt; — Quick IMDb lookup\n\n"
    "<b>Group Commands:</b>\n"
    "• /filter &lt;keyword&gt; &lt;reply&gt; — Add a manual filter\n"
    "• /filters — List all filters\n"
    "• /del &lt;keyword&gt; — Remove a filter\n"
    "• /delall — Remove all filters (admin)\n"
    "• /connect — Connect group to PM\n"
    "• /disconnect — Disconnect group from PM\n"
    "• /settings — Group settings\n\n"
    "<b>Admin Commands:</b>\n"
    "• /stats — Bot statistics\n"
    "• /users — All users\n"
    "• /chats — All chats\n"
    "• /ban &lt;user_id&gt; — Ban user\n"
    "• /unban &lt;user_id&gt; — Unban user\n"
    "• /broadcast — Broadcast message\n"
    "• /logs — Get log file\n"
    "• /deletefiles — Delete all indexed files\n"
)

ABOUT_TEXT = (
    "<b>🤖 About {bot_name}</b>\n\n"
    "Version: <code>2.0</code>\n"
    "Framework: Pyrogram\n"
    "Database: MongoDB (Motor)\n"
    "Developer: EvaMaria Team\n\n"
    "A feature-rich Telegram media catalog bot for searching, "
    "indexing, and delivering files from channels and groups."
)


def start_keyboard(is_group: bool = False):
    if is_group:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🔍 Search Files", switch_inline_query_current_chat="")]
        ])

    buttons = []

    # Row 1: "Add to Group" only if BOT_USERNAME is known (avoids ButtonUrlInvalid)
    row1 = []
    if Var.BOT_USERNAME:
        row1.append(
            InlineKeyboardButton("➕ Add to Group", url=f"https://t.me/{Var.BOT_USERNAME}?startgroup=start")
        )
    row1.append(InlineKeyboardButton("📣 Updates", url="https://t.me/EvaMaria"))
    buttons.append(row1)

    # Row 2
    buttons.append([
        InlineKeyboardButton("🔍 Inline Search", switch_inline_query_current_chat=""),
        InlineKeyboardButton("❓ Help", callback_data="help"),
    ])

    return InlineKeyboardMarkup(buttons)


@Client.on_message(filters.command("start") & filters.private)
async def start_pm(client: Client, message: Message):
    user = message.from_user
    try:
        await add_user(user.id, user.first_name)
    except Exception as e:
        logger.warning("add_user failed for %s: %s", user.id, e)

    try:
        if await is_banned(user.id):
            return await message.reply("🚫 You are banned from using this bot.")
    except Exception as e:
        logger.warning("is_banned check failed for %s: %s", user.id, e)

    # Handle deep-link payload
    if len(message.command) > 1:
        payload = message.command[1]

        # Single file delivery: file_<id>
        if payload.startswith("file_"):
            file_id = payload[5:]
            try:
                file_doc = await get_file(file_id)
            except Exception as e:
                logger.error("get_file failed: %s", e)
                return await message.reply("❌ Could not retrieve file.")
            if file_doc:
                try:
                    caption = Var.FILE_CAPTION.format(
                        file_name=file_doc.get("file_name", "File"),
                        file_size=get_size(file_doc.get("file_size", 0)),
                        duration=get_duration(file_doc.get("duration", 0)),
                    )
                    await client.send_cached_media(
                        user.id,
                        file_doc["file_id"],
                        caption=caption,
                        protect_content=Var.PROTECT_CONTENT,
                    )
                except FloodWait as fw:
                    await asyncio.sleep(fw.value)
                    await client.send_cached_media(user.id, file_doc["file_id"])
                except Exception as e:
                    logger.error("send_cached_media failed: %s", e)
                    await message.reply("❌ Could not send the file.")
            else:
                await message.reply("❌ File not found or has been deleted.")
            return

        # Batch delivery: batch_<encoded>
        if payload.startswith("batch_"):
            import json, base64
            try:
                data = json.loads(base64.urlsafe_b64decode(payload[6:] + "=="))
                file_ids = data.get("ids", [])
                sent = 0
                for fid in file_ids[:50]:
                    fdoc = await get_file(fid)
                    if fdoc:
                        try:
                            await client.send_cached_media(
                                user.id, fdoc["file_id"],
                                caption=fdoc.get("file_name", ""),
                                protect_content=Var.PROTECT_CONTENT,
                            )
                            sent += 1
                            await asyncio.sleep(0.3)
                        except Exception:
                            pass
                await message.reply(f"✅ Sent {sent}/{len(file_ids)} files.")
            except Exception as e:
                logger.error("Batch delivery error: %s", e)
                await message.reply("❌ Invalid batch link.")
            return

    img_url = next_start_img()
    text = PRIVATE_START_TEXT.format(name=user.mention, bot_name=Var.BOT_NAME)
    kb = start_keyboard()

    # Try with photo first, then plain text with keyboard, then plain text only.
    # Each fallback drops one more thing that could cause a Telegram rejection.
    if img_url:
        try:
            return await message.reply_photo(img_url, caption=text, reply_markup=kb)
        except Exception as e:
            logger.warning("reply_photo failed (%s), falling back to text", e)

    try:
        return await message.reply(text, reply_markup=kb, disable_web_page_preview=True)
    except Exception as e:
        logger.warning("reply with keyboard failed (%s), sending plain text", e)

    # Last resort: no keyboard, no photo — guaranteed to work
    await message.reply(text, disable_web_page_preview=True)


@Client.on_message(filters.command("start") & filters.group)
async def start_group(client: Client, message: Message):
    chat = message.chat
    user = message.from_user
    try:
        await add_chat(chat.id, chat.title)
        if user:
            await add_user(user.id, user.first_name)
    except Exception as e:
        logger.warning("DB error in start_group: %s", e)

    text = GROUP_START_TEXT.format(
        name=user.mention if user else "there",
        bot_username=Var.BOT_USERNAME or "the bot",
    )
    try:
        await message.reply(text, reply_markup=start_keyboard(is_group=True), disable_web_page_preview=True)
    except Exception as e:
        logger.warning("start_group reply failed (%s), sending plain text", e)
        await message.reply(text, disable_web_page_preview=True)


@Client.on_message(filters.command("help"))
async def help_cmd(client: Client, message: Message):
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="start")]])
    await message.reply(HELP_TEXT, reply_markup=kb, disable_web_page_preview=True)


@Client.on_message(filters.command("about"))
async def about_cmd(client: Client, message: Message):
    text = ABOUT_TEXT.format(bot_name=Var.BOT_NAME)
    await message.reply(text, disable_web_page_preview=True)


@Client.on_callback_query(filters.regex("^help$"))
async def help_cb(client, cb):
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="start")]])
    await cb.message.edit(HELP_TEXT, reply_markup=kb, disable_web_page_preview=True)


@Client.on_callback_query(filters.regex("^start$"))
async def start_cb(client, cb):
    user = cb.from_user
    img_url = next_start_img()
    text = PRIVATE_START_TEXT.format(name=user.mention, bot_name=Var.BOT_NAME)
    kb = start_keyboard()
    try:
        await cb.message.edit(text, reply_markup=kb, disable_web_page_preview=True)
    except Exception as e:
        logger.warning("start_cb edit failed: %s", e)
    await cb.answer()
