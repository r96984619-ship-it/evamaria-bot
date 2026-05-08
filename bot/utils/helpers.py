import re
import math
import logging
import asyncio
from typing import List, Optional

logger = logging.getLogger(__name__)

MEDIA_TYPES = ("document", "video", "audio", "voice", "video_note", "sticker", "animation")

def get_size(size: int) -> str:
    """Convert bytes to human readable size."""
    if not size:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    idx = int(math.floor(math.log(size, 1024))) if size > 0 else 0
    p = math.pow(1024, idx)
    return f"{round(size / p, 2)} {units[idx]}"

def get_duration(seconds: int) -> str:
    """Convert seconds to HH:MM:SS."""
    if not seconds:
        return "Unknown"
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"

def extract_file_info(message) -> Optional[dict]:
    """Extract media metadata from a Pyrogram message."""
    for media_type in MEDIA_TYPES:
        media = getattr(message, media_type, None)
        if not media:
            continue
        file_name = getattr(media, "file_name", None) or f"{media_type}_{media.file_unique_id}"
        return {
            "file_id": media.file_id,
            "file_unique_id": media.file_unique_id,
            "file_name": file_name,
            "file_size": getattr(media, "file_size", 0),
            "file_type": media_type,
            "mime_type": getattr(media, "mime_type", ""),
            "duration": getattr(media, "duration", 0),
            "caption": message.caption or "",
        }
    return None

def parse_inline_query(query: str):
    """Parse 'query|file_type' syntax."""
    parts = query.strip().split("|", 1)
    q = parts[0].strip()
    ft = parts[1].strip().lower() if len(parts) > 1 else None
    return q, ft

def build_inline_result(file: dict, bot_username: str) -> dict:
    """Build an InlineQueryResultCachedDocument dict."""
    file_id = file["file_id"]
    title = file.get("file_name", "Unknown")
    size = get_size(file.get("file_size", 0))
    desc = f"{file.get('file_type', 'file').upper()} • {size}"
    return {
        "file_id": file_id,
        "title": title,
        "description": desc,
    }

def paginate(total: int, offset: int, page_size: int = 10):
    """Return (has_prev, has_next, current_page, total_pages)."""
    total_pages = math.ceil(total / page_size) if total else 1
    current_page = (offset // page_size) + 1
    has_prev = offset > 0
    has_next = offset + page_size < total
    return has_prev, has_next, current_page, total_pages

async def broadcast_messages(client, user_ids: list, message):
    """Broadcast a message to all users, tracking failures."""
    done = 0
    failed = 0
    blocked = 0
    deleted = 0
    for uid in user_ids:
        try:
            await message.copy(uid)
            done += 1
        except Exception as e:
            err = str(e).lower()
            if "blocked" in err or "user is deactivated" in err:
                blocked += 1
                from bot.database import delete_user
                await delete_user(uid)
            else:
                failed += 1
        await asyncio.sleep(0.05)
    return done, failed, blocked

def create_keyboard(buttons: list) -> list:
    """
    Create a list of InlineKeyboardButton rows from a list of dicts.
    Each dict: {text, url?, callback_data?}
    """
    from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
    rows = []
    for row in buttons:
        if isinstance(row, list):
            rows.append([_make_button(b) for b in row])
        else:
            rows.append([_make_button(row)])
    return InlineKeyboardMarkup(rows) if rows else None

def _make_button(b: dict):
    from pyrogram.types import InlineKeyboardButton
    if b.get("url"):
        return InlineKeyboardButton(b["text"], url=b["url"])
    if b.get("callback_data"):
        return InlineKeyboardButton(b["text"], callback_data=b["callback_data"])
    if b.get("switch_inline_query_current_chat") is not None:
        return InlineKeyboardButton(b["text"], switch_inline_query_current_chat=b["switch_inline_query_current_chat"])
    return InlineKeyboardButton(b["text"], callback_data="noop")

START_IMGS = []
_img_idx = 0

def next_start_img() -> Optional[str]:
    global _img_idx, START_IMGS
    if not START_IMGS:
        return None
    url = START_IMGS[_img_idx % len(START_IMGS)]
    _img_idx += 1
    return url
