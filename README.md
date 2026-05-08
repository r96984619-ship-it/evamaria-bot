# EvaMariaBot 🤖

A full-featured Telegram media catalog bot — turns groups and channels into a searchable file library.

## Features

- **📁 Media Indexing** — Auto-indexes documents, video, audio from configured channels
- **🔍 Inline Search** — Search files via `@bot query` or `@bot query|file_type` syntax
- **🎯 Manual Filters** — Per-group keyword filters with URL/alert buttons and file attachments
- **📥 File Delivery** — Deep-link PM delivery for single files and batch bundles
- **🎬 IMDb Lookup** — `/imdb` and `/search` with poster, cast, rating
- **🔗 Group Connection** — Manage groups remotely from PM
- **⚙️ Settings** — Per-group toggles: auto-filter, PM mode, protect-content, etc.
- **👮 Admin Tools** — Stats, ban/unban, broadcast, disable chats, logs, delete indexed files
- **🗄️ Mock DB** — Runs without MongoDB (in-memory) for quick testing

## Quick Start

### 1. Clone and configure

```bash
cp .env.example .env
# Fill in BOT_TOKEN, API_ID, API_HASH, ADMINS
```

### 2. Run locally (no MongoDB needed)

```bash
pip install -r requirements.txt
python main.py
```

### 3. Run mock end-to-end tests

```bash
python mock_test.py
```

## Deploy to Railway

1. Create a new project on [Railway](https://railway.app)
2. Connect this repo (or push to GitHub first)
3. Add environment variables from `.env.example`
4. (Optional) Add a MongoDB plugin from the Railway dashboard
5. Deploy — Railway auto-detects the `Dockerfile`

### Required Environment Variables

| Variable | Description |
|---|---|
| `BOT_TOKEN` | From @BotFather |
| `API_ID` | From my.telegram.org |
| `API_HASH` | From my.telegram.org |
| `ADMINS` | Space-separated admin user IDs |

### Optional but Recommended

| Variable | Description |
|---|---|
| `DATABASE_URI` | MongoDB connection string (empty = in-memory mock) |
| `CHANNELS` | Space-separated channel IDs to auto-index |
| `LOG_CHANNEL` | Channel ID for bot startup/error logs |
| `AUTH_CHANNEL` | Channel users must join to use the bot |

## Bot Commands

### User Commands
- `/start` — Welcome message (photo card in PM, text in group)
- `/help` — Full command reference
- `/about` — Bot info
- `/imdb <movie>` — IMDb lookup with poster
- `/search <movie>` — Search IMDb results

### Group Admin Commands
- `/filter keyword reply [buttons]` — Add a manual filter
- `/filters` — List all filters
- `/del keyword` — Remove a filter
- `/delall` — Delete all filters
- `/connect` — Connect group to your PM
- `/settings` — Toggle group settings

### Bot Admin Commands
- `/stats` — User/chat/file counts
- `/users` — List users
- `/chats` — List chats
- `/ban <id>` — Ban user
- `/unban <id>` — Unban user
- `/disable [chat_id]` — Disable bot in chat
- `/enable [chat_id]` — Re-enable bot in chat
- `/broadcast` — Broadcast (reply to message)
- `/logs` — Get log file
- `/deletefiles` — Delete all indexed media (with confirmation)
- `/index <link> [end_id]` — Index messages from a channel
- `/link` — Generate shareable file link (reply to media)
- `/batch` — Start batch link session
- `/done` — Finish batch session

## File Search

### Inline mode
```
@YourBot avengers
@YourBot spider man|video
@YourBot soundtrack|audio
```

### Group auto-search
Just type the file name in a connected group — the bot auto-searches and shows clickable results.

## Architecture

```
evamaria-bot/
├── main.py                  # Entry point
├── bot/
│   ├── __init__.py          # Bot class (Pyrogram Client)
│   ├── config.py            # All settings from env vars
│   ├── database/
│   │   ├── __init__.py
│   │   └── connections.py   # MongoDB + in-memory mock DB
│   ├── plugins/
│   │   ├── start.py         # /start, /help, /about + deep-link delivery
│   │   ├── inline.py        # Inline query search
│   │   ├── channel.py       # Channel indexing (/index, forwarded media)
│   │   ├── filters.py       # Manual filters + auto media search fallback
│   │   ├── links.py         # /link and /batch link generation
│   │   ├── connections.py   # /connect group ↔ PM
│   │   ├── settings.py      # /settings with inline toggles
│   │   ├── admin.py         # Admin tools
│   │   └── imdb_plugin.py   # /imdb and /search
│   └── utils/
│       ├── helpers.py       # Size/duration formatting, search utils
│       └── imdb.py          # IMDb lookup (stub if unavailable)
├── mock_test.py             # End-to-end tests (no Telegram needed)
├── requirements.txt
├── Dockerfile
├── railway.toml
└── .env.example
```
