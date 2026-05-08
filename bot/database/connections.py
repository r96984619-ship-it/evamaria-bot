import logging
import time
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

# Try to import Motor (async MongoDB driver)
try:
    from motor.motor_asyncio import AsyncIOMotorClient
    MOTOR_AVAILABLE = True
except ImportError:
    MOTOR_AVAILABLE = False
    logger.warning("Motor not available, using in-memory mock database")

# ─────────────────────────────────────────────
# In-memory mock database (no MongoDB needed)
# ─────────────────────────────────────────────
class MockDB:
    def __init__(self):
        self.users: Dict[int, dict] = {}
        self.chats: Dict[int, dict] = {}
        self.media: List[dict] = []
        self.filters: Dict[str, List[dict]] = {}  # key: str(chat_id)
        self.connections: Dict[int, int] = {}  # user_id -> chat_id
        self.settings: Dict[int, dict] = {}
        self._id_counter = 0

    def _next_id(self):
        self._id_counter += 1
        return self._id_counter

_mock = MockDB()

# ─────────────────────────────────────────────
# Database interface (real or mock)
# ─────────────────────────────────────────────
_client = None
_db = None

def get_db():
    return _db

async def connect_db(uri: str, name: str):
    global _client, _db
    if not uri or not MOTOR_AVAILABLE:
        logger.info("Using in-memory mock database")
        _db = None
        return
    try:
        _client = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=5000)
        await _client.server_info()
        _db = _client[name]
        logger.info("Connected to MongoDB: %s", name)
    except Exception as e:
        logger.warning("MongoDB connection failed (%s), falling back to mock DB", e)
        _db = None


# ─── Users ────────────────────────────────────

async def add_user(user_id: int, name: str = ""):
    if _db is None:
        if user_id not in _mock.users:
            _mock.users[user_id] = {"id": user_id, "name": name, "ban": False, "join_date": time.time()}
        return
    await _db.users.update_one(
        {"id": user_id},
        {"$setOnInsert": {"id": user_id, "name": name, "ban": False, "join_date": time.time()}},
        upsert=True
    )

async def is_user_exist(user_id: int) -> bool:
    if _db is None:
        return user_id in _mock.users
    return bool(await _db.users.find_one({"id": user_id}))

async def total_users_count() -> int:
    if _db is None:
        return len(_mock.users)
    return await _db.users.count_documents({})

async def get_all_users():
    if _db is None:
        return list(_mock.users.values())
    cursor = _db.users.find({})
    return await cursor.to_list(length=None)

async def delete_user(user_id: int):
    if _db is None:
        _mock.users.pop(user_id, None)
        return
    await _db.users.delete_one({"id": user_id})

async def ban_user(user_id: int, ban: bool = True):
    if _db is None:
        if user_id in _mock.users:
            _mock.users[user_id]["ban"] = ban
        return
    await _db.users.update_one({"id": user_id}, {"$set": {"ban": ban}})

async def is_banned(user_id: int) -> bool:
    if _db is None:
        return _mock.users.get(user_id, {}).get("ban", False)
    doc = await _db.users.find_one({"id": user_id})
    return bool(doc and doc.get("ban"))


# ─── Chats ────────────────────────────────────

async def add_chat(chat_id: int, name: str = ""):
    if _db is None:
        if chat_id not in _mock.chats:
            _mock.chats[chat_id] = {"id": chat_id, "name": name, "disabled": False}
        return
    await _db.chats.update_one(
        {"id": chat_id},
        {"$setOnInsert": {"id": chat_id, "name": name, "disabled": False}},
        upsert=True
    )

async def get_chat(chat_id: int) -> Optional[dict]:
    if _db is None:
        return _mock.chats.get(chat_id)
    return await _db.chats.find_one({"id": chat_id})

async def total_chats_count() -> int:
    if _db is None:
        return len(_mock.chats)
    return await _db.chats.count_documents({})

async def get_all_chats():
    if _db is None:
        return list(_mock.chats.values())
    cursor = _db.chats.find({})
    return await cursor.to_list(length=None)

async def disable_chat(chat_id: int, disabled: bool = True):
    if _db is None:
        if chat_id in _mock.chats:
            _mock.chats[chat_id]["disabled"] = disabled
        return
    await _db.chats.update_one({"id": chat_id}, {"$set": {"disabled": disabled}})

async def is_chat_disabled(chat_id: int) -> bool:
    if _db is None:
        return _mock.chats.get(chat_id, {}).get("disabled", False)
    doc = await _db.chats.find_one({"id": chat_id})
    return bool(doc and doc.get("disabled"))


# ─── Media / Files ────────────────────────────

async def save_file(media: dict) -> tuple[bool, str]:
    """Save file metadata. Returns (new, file_id)."""
    file_id = media.get("file_id", "")
    if _db is None:
        existing = next((m for m in _mock.media if m.get("file_id") == file_id), None)
        if existing:
            return False, file_id
        media["_id"] = _mock._next_id()
        _mock.media.append(dict(media))
        return True, file_id
    existing = await _db.media.find_one({"file_id": file_id})
    if existing:
        return False, file_id
    await _db.media.insert_one(media)
    return True, file_id

async def get_file(file_id: str) -> Optional[dict]:
    if _db is None:
        return next((m for m in _mock.media if m.get("file_id") == file_id), None)
    return await _db.media.find_one({"file_id": file_id})

async def get_file_by_unique_id(file_unique_id: str) -> Optional[dict]:
    if _db is None:
        return next((m for m in _mock.media if m.get("file_unique_id") == file_unique_id), None)
    return await _db.media.find_one({"file_unique_id": file_unique_id})

async def get_search_results(query: str, file_type: str = None, max_results: int = 10, offset: int = 0):
    import re
    pattern = re.escape(query).replace(r"\ ", ".")
    if _db is None:
        results = []
        for m in _mock.media:
            fname = m.get("file_name", "")
            caption = m.get("caption", "")
            if re.search(pattern, fname, re.IGNORECASE) or re.search(pattern, caption, re.IGNORECASE):
                if file_type and m.get("file_type") != file_type:
                    continue
                results.append(m)
        total = len(results)
        return results[offset:offset + max_results], total

    filter_q: dict = {"$or": [
        {"file_name": {"$regex": pattern, "$options": "i"}},
        {"caption": {"$regex": pattern, "$options": "i"}}
    ]}
    if file_type:
        filter_q["file_type"] = file_type
    total = await _db.media.count_documents(filter_q)
    cursor = _db.media.find(filter_q).skip(offset).limit(max_results)
    results = await cursor.to_list(length=max_results)
    return results, total

async def total_files_count() -> int:
    if _db is None:
        return len(_mock.media)
    return await _db.media.count_documents({})

async def delete_file(file_id: str):
    if _db is None:
        _mock.media = [m for m in _mock.media if m.get("file_id") != file_id]
        return
    await _db.media.delete_one({"file_id": file_id})

async def delete_all_files():
    if _db is None:
        _mock.media.clear()
        return
    await _db.media.delete_many({})


# ─── Filters ──────────────────────────────────

async def add_filter(chat_id: int, text: str, reply_text: str, btn: list = None, file_id: str = None):
    doc = {"chat_id": chat_id, "text": text.lower(), "reply_text": reply_text, "btn": btn or [], "file_id": file_id}
    key = str(chat_id)
    if _db is None:
        if key not in _mock.filters:
            _mock.filters[key] = []
        _mock.filters[key] = [f for f in _mock.filters[key] if f["text"] != text.lower()]
        _mock.filters[key].append(doc)
        return
    await _db.filters.update_one(
        {"chat_id": chat_id, "text": text.lower()},
        {"$set": doc},
        upsert=True
    )

async def get_filters(chat_id: int) -> list:
    if _db is None:
        return _mock.filters.get(str(chat_id), [])
    cursor = _db.filters.find({"chat_id": chat_id})
    return await cursor.to_list(length=None)

async def delete_filter(chat_id: int, text: str):
    if _db is None:
        key = str(chat_id)
        _mock.filters[key] = [f for f in _mock.filters.get(key, []) if f["text"] != text.lower()]
        return
    await _db.filters.delete_one({"chat_id": chat_id, "text": text.lower()})

async def delete_all_filters(chat_id: int):
    if _db is None:
        _mock.filters.pop(str(chat_id), None)
        return
    await _db.filters.delete_many({"chat_id": chat_id})


# ─── Connections ──────────────────────────────

async def set_connection(user_id: int, chat_id: int):
    if _db is None:
        _mock.connections[user_id] = chat_id
        return
    await _db.connections.update_one(
        {"user_id": user_id},
        {"$set": {"chat_id": chat_id}},
        upsert=True
    )

async def get_connection(user_id: int) -> Optional[int]:
    if _db is None:
        return _mock.connections.get(user_id)
    doc = await _db.connections.find_one({"user_id": user_id})
    return doc["chat_id"] if doc else None

async def delete_connection(user_id: int):
    if _db is None:
        _mock.connections.pop(user_id, None)
        return
    await _db.connections.delete_one({"user_id": user_id})


# ─── Settings ─────────────────────────────────

async def get_settings(chat_id: int) -> dict:
    defaults = {
        "auto_filter": True,
        "spell_check": False,
        "pm_mode": False,
        "single_button": False,
        "protect_content": False,
        "welcome": True,
    }
    if _db is None:
        return {**defaults, **_mock.settings.get(chat_id, {})}
    doc = await _db.settings.find_one({"chat_id": chat_id})
    return {**defaults, **(doc or {})}

async def update_settings(chat_id: int, settings: dict):
    if _db is None:
        _mock.settings.setdefault(chat_id, {}).update(settings)
        return
    await _db.settings.update_one(
        {"chat_id": chat_id},
        {"$set": settings},
        upsert=True
    )
