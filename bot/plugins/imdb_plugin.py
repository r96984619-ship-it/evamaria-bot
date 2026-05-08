"""IMDb lookup commands: /imdb and /search"""
import logging
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from bot.config import Var
from bot.utils.imdb import search_imdb

logger = logging.getLogger(__name__)


def format_imdb(movie: dict, template: str = None) -> str:
    tmpl = template or Var.IMDB_TEMPLATE
    try:
        return tmpl.format(**movie)
    except Exception:
        return (
            f"🎬 <b>{movie.get('title', 'Unknown')}</b> ({movie.get('year', '?')})\n"
            f"⭐ Rating: {movie.get('rating', 'N/A')}\n"
            f"🎭 Genre: {movie.get('genres', 'N/A')}\n"
            f"🎥 Director: {movie.get('director', 'N/A')}\n"
            f"👥 Cast: {movie.get('cast', 'N/A')}\n"
            f"📝 {movie.get('plot', '')}"
        )


@Client.on_message(filters.command(["imdb", "search"]))
async def imdb_command(client: Client, message: Message):
    if len(message.command) < 2:
        return await message.reply("Usage: <code>/imdb Movie Name</code>")

    query = " ".join(message.command[1:])
    status = await message.reply(f"🔍 Searching IMDb for: <b>{query}</b>...")

    results = await search_imdb(query, results=5)
    if not results:
        return await status.edit("❌ No results found on IMDb.")

    movie = results[0]
    text = format_imdb(movie)
    poster = movie.get("poster")
    url = movie.get("url", "https://imdb.com")

    kb_rows = []
    if len(results) > 1:
        row = []
        for i, m in enumerate(results[1:4], 2):
            row.append(InlineKeyboardButton(
                f"{i}. {m.get('title', '?')[:20]}",
                callback_data=f"imdb_sel#{i-1}#{query}"
            ))
        kb_rows.append(row)
    kb_rows.append([InlineKeyboardButton("🌐 View on IMDb", url=url)])
    kb = InlineKeyboardMarkup(kb_rows) if kb_rows else None

    try:
        if poster:
            await status.delete()
            await message.reply_photo(poster, caption=text, reply_markup=kb)
        else:
            await status.edit(text, reply_markup=kb, disable_web_page_preview=True)
    except Exception as e:
        logger.error("IMDb reply error: %s", e)
        await status.edit(text, disable_web_page_preview=True)

    # Store results for callback selection
    # Simple approach: we re-search in callback
