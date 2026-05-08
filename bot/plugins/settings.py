"""Group settings management via inline keyboard toggles."""
import logging
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from bot.config import Var
from bot.database import get_settings, update_settings, get_connection

logger = logging.getLogger(__name__)

SETTINGS_KEYS = {
    "auto_filter": "🔍 Auto Filter",
    "spell_check": "📝 Spell Check",
    "pm_mode": "📩 PM Mode",
    "single_button": "🔘 Single Button",
    "protect_content": "🔒 Protect Content",
    "welcome": "👋 Welcome Msg",
}


def settings_keyboard(settings: dict, chat_id: int):
    rows = []
    for key, label in SETTINGS_KEYS.items():
        val = settings.get(key, False)
        icon = "✅" if val else "❌"
        rows.append([InlineKeyboardButton(
            f"{icon} {label}",
            callback_data=f"toggle#{chat_id}#{key}"
        )])
    rows.append([InlineKeyboardButton("🔙 Close", callback_data="close_settings")])
    return InlineKeyboardMarkup(rows)


@Client.on_message(filters.command("settings") & (filters.group | filters.private))
async def settings_cmd(client: Client, message: Message):
    user = message.from_user
    if not user:
        return

    if message.chat.type in ("group", "supergroup"):
        try:
            member = await client.get_chat_member(message.chat.id, user.id)
            if member.status not in ("administrator", "creator") and user.id not in Var.ADMINS:
                return await message.reply("❌ Only group admins can manage settings.")
        except Exception:
            return
        chat_id = message.chat.id
        chat_name = message.chat.title
    else:
        conn = await get_connection(user.id)
        if not conn:
            return await message.reply("❌ No group connected. Use /connect in a group first.")
        chat_id = conn
        try:
            chat = await client.get_chat(chat_id)
            chat_name = chat.title
        except Exception:
            chat_name = str(chat_id)

    settings = await get_settings(chat_id)
    kb = settings_keyboard(settings, chat_id)
    await message.reply(
        f"⚙️ <b>Settings for {chat_name}</b>\n\nToggle options below:",
        reply_markup=kb
    )


@Client.on_callback_query(filters.regex(r"^toggle#(-?\d+)#(\w+)$"))
async def toggle_setting(client: Client, cb: CallbackQuery):
    _, chat_id_str, key = cb.data.split("#")
    chat_id = int(chat_id_str)

    # Verify admin
    user = cb.from_user
    if user.id not in Var.ADMINS and user.id not in Var.AUTH_USERS:
        try:
            member = await client.get_chat_member(chat_id, user.id)
            if member.status not in ("administrator", "creator"):
                return await cb.answer("❌ Unauthorized", show_alert=True)
        except Exception:
            return await cb.answer("❌ Unauthorized", show_alert=True)

    settings = await get_settings(chat_id)
    current = settings.get(key, False)
    settings[key] = not current
    await update_settings(chat_id, {key: not current})

    label = SETTINGS_KEYS.get(key, key)
    new_val = "ON" if not current else "OFF"
    await cb.answer(f"{label} turned {new_val}")

    kb = settings_keyboard(settings, chat_id)
    try:
        await cb.message.edit_reply_markup(reply_markup=kb)
    except Exception:
        pass


@Client.on_callback_query(filters.regex("^close_settings$"))
async def close_settings(client, cb):
    try:
        await cb.message.delete()
    except Exception:
        await cb.answer("Closed")
