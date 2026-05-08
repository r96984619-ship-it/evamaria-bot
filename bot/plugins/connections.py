"""Group connection management — manage a group from private chat."""
import logging
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import ChatAdminRequired, UserNotParticipant

from bot.database import set_connection, get_connection, delete_connection

logger = logging.getLogger(__name__)


@Client.on_message(filters.command("connect") & filters.group)
async def connect_group(client: Client, message: Message):
    """Connect the current group to the user's PM for remote filter management."""
    user = message.from_user
    if not user:
        return

    try:
        member = await client.get_chat_member(message.chat.id, user.id)
        if member.status not in ("administrator", "creator"):
            return await message.reply("❌ Only group admins can connect to PM.")
    except Exception:
        return await message.reply("❌ Could not verify your admin status.")

    await set_connection(user.id, message.chat.id)
    await message.reply(
        f"✅ <b>Connected!</b>\n\n"
        f"You can now manage <b>{message.chat.title}</b> from your PM.\n"
        f"Send me /filters, /filter, /del etc. in private to manage this group."
    )


@Client.on_message(filters.command("disconnect") & filters.private)
async def disconnect_group(client: Client, message: Message):
    user = message.from_user
    if not user:
        return

    conn = await get_connection(user.id)
    if not conn:
        return await message.reply("❌ No group connected.")

    await delete_connection(user.id)
    await message.reply("✅ Disconnected from group.")


@Client.on_message(filters.command("connection") & filters.private)
async def show_connection(client: Client, message: Message):
    user = message.from_user
    if not user:
        return

    conn = await get_connection(user.id)
    if not conn:
        return await message.reply("❌ No group connected. Use /connect in a group first.")

    try:
        chat = await client.get_chat(conn)
        name = chat.title
    except Exception:
        name = str(conn)

    await message.reply(
        f"🔗 <b>Connected Group:</b> {name}\n"
        f"ID: <code>{conn}</code>\n\n"
        "You can manage filters for this group from here.",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ Disconnect", callback_data="disconnect")
        ]])
    )


@Client.on_callback_query(filters.regex("^disconnect$"))
async def disconnect_cb(client, cb):
    await delete_connection(cb.from_user.id)
    await cb.message.edit("✅ Disconnected from group.")
