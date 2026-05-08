import logging
from pyrogram import Client, filters
from pyrogram.types import (
    InlineQuery, InlineQueryResultCachedDocument, InlineKeyboardMarkup,
    InlineKeyboardButton, InlineQueryResultArticle, InputTextMessageContent,
)
from pyrogram.errors import QueryIdInvalid

from bot.config import Var
from bot.database import get_search_results, is_banned, add_user
from bot.utils import parse_inline_query, get_size, paginate

logger = logging.getLogger(__name__)

RESULTS_PER_PAGE = 10


@Client.on_inline_query()
async def inline_search(client: Client, query: InlineQuery):
    user = query.from_user
    await add_user(user.id, user.first_name)

    if await is_banned(user.id):
        await query.answer(
            results=[InlineQueryResultArticle(
                title="❌ You are banned",
                input_message_content=InputTextMessageContent("You are banned from using this bot."),
            )],
            cache_time=0,
        )
        return

    raw_query = query.query.strip()
    if not raw_query:
        # Show hint when query is empty
        await query.answer(
            results=[InlineQueryResultArticle(
                title="🔍 Search for files",
                description="Type a movie or file name to search",
                input_message_content=InputTextMessageContent(
                    "Use inline mode: <code>@bot query</code> or <code>@bot query|file_type</code>",
                ),
            )],
            cache_time=0,
        )
        return

    q, file_type = parse_inline_query(raw_query)
    offset = int(query.offset) if query.offset else 0

    files, total = await get_search_results(q, file_type=file_type, max_results=RESULTS_PER_PAGE, offset=offset)

    results = []
    for f in files:
        title = f.get("file_name", "Unknown")
        size = get_size(f.get("file_size", 0))
        file_type_str = f.get("file_type", "file").upper()
        desc = f"{file_type_str} • {size}"

        # Inline keyboard with "Search Again" button
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("🔁 Search Again", switch_inline_query_current_chat=q)
        ]])

        try:
            result = InlineQueryResultCachedDocument(
                title=title,
                file_id=f["file_id"],
                description=desc,
                reply_markup=kb,
            )
            results.append(result)
        except Exception as e:
            logger.warning("Skipping file %s: %s", f.get("file_id"), e)

    _, has_next, current_page, total_pages = paginate(total, offset, RESULTS_PER_PAGE)
    next_offset = str(offset + RESULTS_PER_PAGE) if has_next else ""

    switch_text = f"🔍 Results {current_page}/{total_pages} for: {q}"
    if not results:
        results = [InlineQueryResultArticle(
            title="❌ No results found",
            description=f"No files matching '{q}'",
            input_message_content=InputTextMessageContent(f"No results for: <b>{q}</b>"),
        )]

    try:
        await query.answer(
            results=results,
            next_offset=next_offset,
            cache_time=0,
            switch_pm_text=switch_text[:32],
            switch_pm_parameter="start",
        )
    except QueryIdInvalid:
        pass
    except Exception as e:
        logger.error("Inline query error: %s", e)
