"""Admin commands: stats, users, chats, ban, broadcast, logs, delete files."""
import os
import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from bot.config import Var
from bot.database import (
    total_users_count, total_chats_count, total_files_count,
    get_all_users, get_all_chats,
    ban_user, is_banned, add_user,
    disable_chat, is_chat_disabled,
    delete_all_files,
)
from bot.utils import broadcast_messages

logger = logging.getLogger(__name__)

CONFIRM_DELETE_STATE = set()


def admin_filter(_, __, message: Message):
    user = message.from_user
    if not user:
        return False
    return user.id in Var.ADMINS or user.id in Var.AUTH_USERS


admins_only = filters.create(admin_filter)


@Client.on_message(filters.command("stats") & admins_only)
async def stats_cmd(client: Client, message: Message):
    users = await total_users_count()
    chats = await total_chats_count()
    files = await total_files_count()
    await message.reply(
        f"📊 <b>Bot Statistics</b>\n\n"
        f"👤 Users: <b>{users}</b>\n"
        f"💬 Chats: <b>{chats}</b>\n"
        f"📁 Indexed Files: <b>{files}</b>"
    )


@Client.on_message(filters.command("users") & admins_only)
async def list_users(client: Client, message: Message):
    all_users = await get_all_users()
    if not all_users:
        return await message.reply("No users found.")
    lines = [f"• {u.get('name', 'Unknown')} (<code>{u['id']}</code>)" for u in all_users[:50]]
    await message.reply(
        f"<b>👤 Users ({len(all_users)} total):</b>\n\n" + "\n".join(lines)
    )


@Client.on_message(filters.command("chats") & admins_only)
async def list_chats(client: Client, message: Message):
    all_chats = await get_all_chats()
    if not all_chats:
        return await message.reply("No chats found.")
    lines = [f"• {c.get('name', 'Unknown')} (<code>{c['id']}</code>)" for c in all_chats[:50]]
    await message.reply(
        f"<b>💬 Chats ({len(all_chats)} total):</b>\n\n" + "\n".join(lines)
    )


@Client.on_message(filters.command("ban") & admins_only)
async def ban_cmd(client: Client, message: Message):
    if len(message.command) < 2:
        return await message.reply("Usage: <code>/ban user_id</code>")
    try:
        uid = int(message.command[1])
    except ValueError:
        return await message.reply("❌ Invalid user ID.")

    await add_user(uid)
    await ban_user(uid, True)
    await message.reply(f"🚫 User <code>{uid}</code> has been banned.")


@Client.on_message(filters.command("unban") & admins_only)
async def unban_cmd(client: Client, message: Message):
    if len(message.command) < 2:
        return await message.reply("Usage: <code>/unban user_id</code>")
    try:
        uid = int(message.command[1])
    except ValueError:
        return await message.reply("❌ Invalid user ID.")

    await ban_user(uid, False)
    await message.reply(f"✅ User <code>{uid}</code> has been unbanned.")


@Client.on_message(filters.command("disable") & admins_only)
async def disable_cmd(client: Client, message: Message):
    if len(message.command) < 2:
        chat_id = message.chat.id
    else:
        try:
            chat_id = int(message.command[1])
        except ValueError:
            return await message.reply("❌ Invalid chat ID.")

    await disable_chat(chat_id, True)
    await message.reply(f"🔕 Chat <code>{chat_id}</code> has been disabled.")


@Client.on_message(filters.command("enable") & admins_only)
async def enable_cmd(client: Client, message: Message):
    if len(message.command) < 2:
        chat_id = message.chat.id
    else:
        try:
            chat_id = int(message.command[1])
        except ValueError:
            return await message.reply("❌ Invalid chat ID.")

    await disable_chat(chat_id, False)
    await message.reply(f"🔔 Chat <code>{chat_id}</code> has been enabled.")


@Client.on_message(filters.command("leave") & admins_only)
async def leave_cmd(client: Client, message: Message):
    if len(message.command) < 2:
        return await message.reply("Usage: <code>/leave chat_id</code>")
    try:
        chat_id = int(message.command[1])
    except ValueError:
        return await message.reply("❌ Invalid chat ID.")
    try:
        await client.leave_chat(chat_id)
        await message.reply(f"✅ Left chat <code>{chat_id}</code>.")
    except Exception as e:
        await message.reply(f"❌ Failed to leave: {e}")


@Client.on_message(filters.command("logs") & admins_only)
async def logs_cmd(client: Client, message: Message):
    log_file = "bot.log"
    if os.path.exists(log_file):
        await client.send_document(message.chat.id, log_file, caption="📋 Bot logs")
    else:
        await message.reply("❌ No log file found.")


@Client.on_message(filters.command("broadcast") & admins_only)
async def broadcast_cmd(client: Client, message: Message):
    if not message.reply_to_message:
        return await message.reply("❌ Reply to a message to broadcast it to all users.")

    all_users = await get_all_users()
    if not all_users:
        return await message.reply("No users to broadcast to.")

    status = await message.reply(f"📣 Broadcasting to {len(all_users)} users...")
    user_ids = [u["id"] for u in all_users]
    done, failed, blocked = await broadcast_messages(client, user_ids, message.reply_to_message)
    await status.edit(
        f"📣 <b>Broadcast Complete!</b>\n\n"
        f"✅ Sent: <b>{done}</b>\n"
        f"❌ Failed: <b>{failed}</b>\n"
        f"🚫 Blocked/Deleted: <b>{blocked}</b>"
    )


@Client.on_message(filters.command("deletefiles") & admins_only)
async def delete_files_cmd(client: Client, message: Message):
    uid = message.from_user.id
    if uid in CONFIRM_DELETE_STATE:
        CONFIRM_DELETE_STATE.discard(uid)
        count = await total_files_count()
        await delete_all_files()
        await message.reply(f"🗑 Deleted all <b>{count}</b> indexed files.")
    else:
        CONFIRM_DELETE_STATE.add(uid)
        await message.reply(
            "⚠️ <b>WARNING!</b>\n\n"
            "This will delete ALL indexed media files from the database.\n"
            "Type /deletefiles again to confirm.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ Confirm Delete", callback_data="confirm_deletefiles"),
                InlineKeyboardButton("❌ Cancel", callback_data="cancel_deletefiles"),
            ]])
        )


@Client.on_callback_query(filters.regex("^confirm_deletefiles$"))
async def confirm_delete_files(client, cb):
    if cb.from_user.id not in Var.ADMINS and cb.from_user.id not in Var.AUTH_USERS:
        return await cb.answer("❌ Unauthorized", show_alert=True)
    count = await total_files_count()
    await delete_all_files()
    CONFIRM_DELETE_STATE.discard(cb.from_user.id)
    await cb.message.edit(f"🗑 Deleted all <b>{count}</b> indexed files.")


@Client.on_callback_query(filters.regex("^cancel_deletefiles$"))
async def cancel_delete_files(client, cb):
    CONFIRM_DELETE_STATE.discard(cb.from_user.id)
    await cb.message.edit("❌ Deletion cancelled.")
