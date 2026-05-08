#!/usr/bin/env python3
"""
Mock end-to-end test — exercises all major flows without a real Telegram connection.
Run with: python mock_test.py
"""
import asyncio
import sys
import os

# Patch env so config loads without errors
os.environ.setdefault("BOT_TOKEN", "mock:token")
os.environ.setdefault("API_ID", "12345678")
os.environ.setdefault("API_HASH", "mock_hash")
os.environ.setdefault("ADMINS", "100")

from bot.database.connections import (
    connect_db,
    add_user, is_user_exist, total_users_count,
    ban_user, is_banned,
    add_chat, total_chats_count,
    save_file, get_file, get_search_results, total_files_count, delete_all_files,
    add_filter, get_filters, delete_filter,
    set_connection, get_connection, delete_connection,
    get_settings, update_settings,
)
from bot.utils.helpers import (
    get_size, get_duration, extract_file_info, parse_inline_query,
    paginate,
)
from bot.utils.imdb import search_imdb

PASS = "✅"
FAIL = "❌"
results = []


def check(name: str, condition: bool):
    icon = PASS if condition else FAIL
    print(f"  {icon} {name}")
    results.append(condition)


async def run_tests():
    print("\n══════════════════════════════════════")
    print("   EvaMariaBot Mock End-to-End Tests   ")
    print("══════════════════════════════════════\n")

    # Initialize in-memory DB (no URI → mock)
    await connect_db("", "EvaMaria")

    # ── Users ──────────────────────────────────────────────────────────────────
    print("👤 User Management")
    await add_user(100, "Alice")
    await add_user(200, "Bob")
    check("add_user / is_user_exist", await is_user_exist(100))
    check("total_users_count == 2", await total_users_count() == 2)
    await ban_user(200, True)
    check("ban_user / is_banned", await is_banned(200))
    await ban_user(200, False)
    check("unban_user", not await is_banned(200))

    # ── Chats ──────────────────────────────────────────────────────────────────
    print("\n💬 Chat Management")
    await add_chat(-1001, "Test Group")
    check("add_chat / total_chats_count", await total_chats_count() == 1)

    # ── Media / Files ──────────────────────────────────────────────────────────
    print("\n📁 Media Indexing")
    f1 = {"file_id": "fid_001", "file_unique_id": "uniq_001", "file_name": "Avengers.Endgame.2019.mkv",
          "file_size": 2_500_000_000, "file_type": "video", "mime_type": "video/x-matroska",
          "duration": 10800, "caption": ""}
    f2 = {"file_id": "fid_002", "file_unique_id": "uniq_002", "file_name": "Spider-Man.No.Way.Home.mkv",
          "file_size": 1_800_000_000, "file_type": "video", "mime_type": "video/x-matroska",
          "duration": 8640, "caption": "Spider-Man returns"}
    f3 = {"file_id": "fid_003", "file_unique_id": "uniq_003", "file_name": "soundtrack.mp3",
          "file_size": 5_000_000, "file_type": "audio", "mime_type": "audio/mpeg",
          "duration": 240, "caption": ""}

    is_new, _ = await save_file(f1)
    check("save new file (Avengers)", is_new)
    is_dup, _ = await save_file(f1)
    check("detect duplicate file", not is_dup)
    await save_file(f2)
    await save_file(f3)
    check("total_files_count == 3", await total_files_count() == 3)
    check("get_file by id", (await get_file("fid_001")) is not None)

    # ── Search ─────────────────────────────────────────────────────────────────
    print("\n🔍 Search")
    results_q, total = await get_search_results("avengers")
    check("search 'avengers' finds 1 result", total == 1 and len(results_q) == 1)
    results_q2, total2 = await get_search_results("spider")
    check("search 'spider' finds 1 result", total2 == 1)
    results_q3, total3 = await get_search_results("man")
    check("search 'man' finds results (partial match)", total3 >= 1)
    results_q4, total4 = await get_search_results("spider", file_type="video")
    check("file_type filter works", total4 == 1)
    results_q5, total5 = await get_search_results("spider", file_type="audio")
    check("file_type filter excludes non-matching", total5 == 0)
    results_q6, _ = await get_search_results("spider", max_results=1, offset=0)
    check("pagination offset works", len(results_q6) <= 1)

    # ── Inline query parsing ───────────────────────────────────────────────────
    print("\n📡 Inline Query Parsing")
    q, ft = parse_inline_query("avengers|video")
    check("parse 'avengers|video' → query='avengers'", q == "avengers")
    check("parse 'avengers|video' → file_type='video'", ft == "video")
    q2, ft2 = parse_inline_query("spider man")
    check("parse no pipe → file_type=None", ft2 is None)

    # ── Filters ────────────────────────────────────────────────────────────────
    print("\n🎯 Manual Filters")
    await add_filter(-1001, "hello", "Hi there!", [{"text": "Wave", "url": "https://t.me"}], None)
    await add_filter(-1001, "bye", "Goodbye!", [], None)
    all_filters = await get_filters(-1001)
    check("add_filter + get_filters returns 2", len(all_filters) == 2)
    await delete_filter(-1001, "bye")
    all_filters2 = await get_filters(-1001)
    check("delete_filter reduces to 1", len(all_filters2) == 1)

    # ── Connections ────────────────────────────────────────────────────────────
    print("\n🔗 Group Connections")
    await set_connection(100, -1001)
    check("set_connection / get_connection", await get_connection(100) == -1001)
    await delete_connection(100)
    check("delete_connection", await get_connection(100) is None)

    # ── Settings ───────────────────────────────────────────────────────────────
    print("\n⚙️  Settings")
    settings = await get_settings(-1001)
    check("get_settings returns defaults", isinstance(settings, dict) and "auto_filter" in settings)
    await update_settings(-1001, {"auto_filter": False, "pm_mode": True})
    settings2 = await get_settings(-1001)
    check("update_settings persists changes", settings2["auto_filter"] is False and settings2["pm_mode"] is True)

    # ── Utility helpers ────────────────────────────────────────────────────────
    print("\n🛠  Utility Helpers")
    check("get_size(0)", get_size(0) == "0 B")
    check("get_size(1536)", get_size(1536) == "1.5 KB")
    check("get_size(2.5GB)", "GB" in get_size(2_500_000_000))
    check("get_duration(0)", get_duration(0) == "Unknown")
    check("get_duration(3661)", get_duration(3661) == "01:01:01")
    check("paginate total=25 offset=0", paginate(25, 0, 10) == (False, True, 1, 3))
    check("paginate total=25 offset=20", paginate(25, 20, 10) == (True, False, 3, 3))

    # ── IMDb stub ──────────────────────────────────────────────────────────────
    print("\n🎬 IMDb Stub (no API key required)")
    imdb_results = await search_imdb("The Dark Knight")
    check("IMDb search returns at least 1 result", len(imdb_results) >= 1)
    check("IMDb result has 'title' key", "title" in imdb_results[0])
    check("IMDb result has 'rating' key", "rating" in imdb_results[0])

    # ── Delete all files (with confirmation flow) ──────────────────────────────
    print("\n🗑  Cleanup")
    await delete_all_files()
    check("delete_all_files → total == 0", await total_files_count() == 0)

    # ── Summary ────────────────────────────────────────────────────────────────
    passed = sum(results)
    total_tests = len(results)
    failed = total_tests - passed
    print(f"\n══════════════════════════════════════")
    print(f"Results: {passed}/{total_tests} passed", "🎉" if failed == 0 else "⚠️")
    if failed:
        print(f"  {failed} test(s) failed — review output above")
    print("══════════════════════════════════════\n")
    return failed == 0


if __name__ == "__main__":
    ok = asyncio.run(run_tests())
    sys.exit(0 if ok else 1)
