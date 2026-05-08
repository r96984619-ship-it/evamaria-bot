"""Manual filters per group + auto media search fallback."""
import re
import logging
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from bot.config import Var
from bot.database import (
    add_filter, get_filters, delete_filter, delete_all_filters,
    get_search_results, get_settings, add_chat, add_user,
    get_connection, is_banned,
)
from bot.utils import get_size

logger = logging.getLogger(__name__)


def _parse_buttons(text: str):
    """Parse button syntax: [Button Text : url] or [Button Text :: callback]"""
    btn_re = re.compile(r'\[(.+?)\s*:\s*(https?://\S+|[a-zA-Z0-9_]+)\]')
    buttons = []
    clean = btn_re.sub("", text).strip()
    for match in btn_re.finditer(text):
        label, value = match.group(1).strip(), match.group(2).strip()
        if value.startswith("http"):
            buttons.append({"text": label, "url": value})
        else:
            buttons.append({"text": label, "callback_data": f"alertcb#{value}"})
    return clean, buttons


def build_reply_markup(buttons: list):
    if not buttons:
        return None
    rows = []
    for b in buttons:
        if b.get("url"):
            rows.append([InlineKeyboardButton(b["text"], url=b["url"])])
        elif b.get("callback_data"):
            rows.append([InlineKeyboardButton(b["text"], callback_data=b["callback_data"])])
    return InlineKeyboardMarkup(rows) if rows else None


def is_admin_or_auth(user_id: int) -> bool:
    return user_id in Var.ADMINS or user_id in Var.AUTH_USERS


@Client.on_message(filters.command("filter") & (filters.group | filters.private))
async def add_filter_cmd(client: Client, message: Message):
    user = message.from_user
    if not user:
        return

    # Determine chat_id
    if message.chat.type in ("group", "supergroup"):
        chat_id = message.chat.id
        member = await client.get_chat_member(chat_id, user.id)
        if member.status not in ("administrator", "creator") and not is_admin_or_auth(user.id):
            return await message.reply("❌ Only group admins can add filters.")
    else:
        conn = await get_connection(user.id)
        if not conn:
            return await message.reply("❌ No group connected. Use /connect in a group first.")
        chat_id = conn

    if len(message.command) < 2:
        return await message.reply("Usage: <code>/filter keyword reply text [buttons]</code>")

    keyword = message.command[1].lower()
    reply_text = " ".join(message.command[2:]) if len(message.command) > 2 else ""

    # If replying to a message, use that as reply content
    file_id = None
    if message.reply_to_message:
        rm = message.reply_to_message
        if not reply_text:
            reply_text = rm.text or rm.caption or ""
        for attr in ("document", "video", "audio", "photo", "sticker", "animation"):
            media = getattr(rm, attr, None)
            if media:
                file_id = getattr(media, "file_id", None)
                break

    clean_text, buttons = _parse_buttons(reply_text)
    await add_filter(chat_id, keyword, clean_text, buttons, file_id)
    await message.reply(f"✅ Filter <code>{keyword}</code> saved for this chat.")


@Client.on_message(filters.command("filters") & (filters.group | filters.private))
async def list_filters(client: Client, message: Message):
    user = message.from_user
    if not user:
        return

    if message.chat.type in ("group", "supergroup"):
        chat_id = message.chat.id
    else:
        conn = await get_connection(user.id)
        if not conn:
            return await message.reply("❌ No group connected.")
        chat_id = conn

    all_filters = await get_filters(chat_id)
    if not all_filters:
        return await message.reply("No filters set for this chat.")

    text = "<b>📋 Filters in this chat:</b>\n\n"
    for f in all_filters[:Var.MAX_LIST_ELM]:
        text += f"• <code>{f['text']}</code>\n"
    await message.reply(text)


@Client.on_message(filters.command("del") & (filters.group | filters.private))
async def delete_filter_cmd(client: Client, message: Message):
    user = message.from_user
    if not user:
        return

    if message.chat.type in ("group", "supergroup"):
        chat_id = message.chat.id
        member = await client.get_chat_member(chat_id, user.id)
        if member.status not in ("administrator", "creator") and not is_admin_or_auth(user.id):
            return await message.reply("❌ Only admins can delete filters.")
    else:
        conn = await get_connection(user.id)
        if not conn:
            return await message.reply("❌ No group connected.")
        chat_id = conn

    if len(message.command) < 2:
        return await message.reply("Usage: <code>/del keyword</code>")

    keyword = message.command[1].lower()
    await delete_filter(chat_id, keyword)
    await message.reply(f"✅ Filter <code>{keyword}</code> deleted.")


@Client.on_message(filters.command("delall") & (filters.group | filters.private))
async def delete_all_filters_cmd(client: Client, message: Message):
    user = message.from_user
    if not user or not is_admin_or_auth(user.id):
        return await message.reply("❌ Only bot admins can delete all filters.")

    if message.chat.type in ("group", "supergroup"):
        chat_id = message.chat.id
    else:
        conn = await get_connection(user.id)
        if not conn:
            return await message.reply("❌ No group connected.")
        chat_id = conn

    await delete_all_filters(chat_id)
    await message.reply("✅ All filters deleted.")


@Client.on_message(filters.text & (filters.group | filters.private) & ~filters.command(""))
async def text_handler(client: Client, message: Message):
    """Check manual filters first, then fall back to auto media search."""
    user = message.from_user
    if not user:
        return

    await add_user(user.id, user.first_name)

    if await is_banned(user.id):
        return

    chat = message.chat
    if chat.type in ("group", "supergroup"):
        await add_chat(chat.id, chat.title)
        chat_id = chat.id
    else:
        return  # PM text handled by other handlers

    settings = await get_settings(chat_id)
    if not settings.get("auto_filter", True):
        return

    text_lower = message.text.lower().strip()

    # 1. Check manual filters
    all_filters = await get_filters(chat_id)
    for f in all_filters:
        if f["text"] in text_lower or re.search(rf'\b{re.escape(f["text"])}\b', text_lower, re.IGNORECASE):
            reply_text = f.get("reply_text", "")
            buttons = f.get("btn", [])
            file_id = f.get("file_id")
            kb = build_reply_markup(buttons)

            if file_id:
                try:
                    await client.send_cached_media(chat_id, file_id, caption=reply_text, reply_markup=kb)
                    return
                except Exception:
                    pass
            if reply_text:
                await message.reply(reply_text, reply_markup=kb, disable_web_page_preview=True)
                return

    # 2. Auto media search fallback
    if len(text_lower) < 3:
        return

    files, total = await get_search_results(text_lower, max_results=5)
    if not files:
        return

    btns = []
    for f in files:
        name = f.get("file_name", "Unknown")[:50]
        size = get_size(f.get("file_size", 0))
        btns.append([InlineKeyboardButton(
            f"📄 {name} [{size}]",
            callback_data=f"file#{f['file_id']}"
        )])

    btns.append([InlineKeyboardButton("🔁 Search Again", switch_inline_query_current_chat=text_lower)])

    await message.reply(
        f"🔍 Found <b>{total}</b> result(s) for: <b>{text_lower}</b>",
        reply_markup=InlineKeyboardMarkup(btns),
        disable_web_page_preview=True,
    )


@Client.on_callback_query(filters.regex(r"^file#(.+)$"))
async def file_callback(client, cb):
    """Send a file to the user when they click a result button."""
    file_id = cb.data.split("#", 1)[1]
    from bot.database import get_file
    from bot.config import Var
    from bot.utils import get_size, get_duration

    fdoc = await get_file(file_id)
    if not fdoc:
        return await cb.answer("❌ File not found.", show_alert=True)

    try:
        caption = Var.FILE_CAPTION.format(
            file_name=fdoc.get("file_name", "File"),
            file_size=get_size(fdoc.get("file_size", 0)),
            duration=get_duration(fdoc.get("duration", 0)),
        )
        await client.send_cached_media(
            cb.from_user.id,
            fdoc["file_id"],
            caption=caption,
            protect_content=Var.PROTECT_CONTENT,
        )
        await cb.answer("✅ File sent to your PM!")
    except Exception as e:
        if "PEER_ID_INVALID" in str(e) or "user" in str(e).lower():
            bot_username = Var.BOT_USERNAME
            await cb.answer(
                f"Start the bot first: t.me/{bot_username}",
                show_alert=True,
            )
        else:
            await cb.answer(f"❌ Error: {e}", show_alert=True)


@Client.on_callback_query(filters.regex(r"^alertcb#(.+)$"))
async def alert_callback(client, cb):
    data = cb.data.split("#", 1)[1]
    await cb.answer(data, show_alert=True)
