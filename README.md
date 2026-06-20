# 📚 StudyBuddyV3BOT

> A production-ready, SaaS-level AI-powered Telegram Study Assistant Bot built with Python, MongoDB, and OpenAI.

![Python](https://img.shields.io/badge/Python-3.11+-blue?style=for-the-badge&logo=python)
![Telegram](https://img.shields.io/badge/Telegram-Bot-26A5E4?style=for-the-badge&logo=telegram)
![MongoDB](https://img.shields.io/badge/MongoDB-Atlas-47A248?style=for-the-badge&logo=mongodb)
![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o--mini-412991?style=for-the-badge&logo=openai)
![Render](https://img.shields.io/badge/Deploy-Render.com-46E3B7?style=for-the-badge&logo=render)

---

## 🌟 Features

### 🤖 AI Study Assistant
- Powered by OpenAI GPT-4o-mini
- Educational focus with smart answers
- Per-user context memory (conversation history)
- Rate limiting to prevent API abuse

### 🌍 Multi-Language Support
- Auto-detects user language
- Manual language switch via inline buttons
- Supports English, Hindi, Bengali, Arabic
- Language preference saved in database

### 🧮 Inline Calculator
- Button-based calculator UI
- Safe expression evaluation
- Basic + advanced math operations

### 🌐 Translation Tool
- Translate text to any language
- Inline button interface
- Powered by deep-translator

### 📚 Study Notes
- Save personal notes
- View all saved notes
- Delete individual notes
- Max 50 notes per user

### 🎛️ Admin Panel
- Total & active user stats
- Broadcast messages with media support
- Ban / Unban users
- Maintenance mode toggle
- API usage tracking
- Full inline button UI

---

## 🏗️ Project Structure
StudyBuddyV3BOT/

├── main.py                    # Entry point

├── requirements.txt           # Dependencies

├── .env.template              # Environment template

├── .gitignore                 # Git ignore rules

├── README.md                  # This file

│

├── config/

│   ├── settings.py            # Load & validate .env

│   └── constants.py           # App-wide constants

│

├── database/

│   ├── connection.py          # MongoDB async connection

│   ├── models.py              # Data schemas

│   └── repositories/

│       ├── user_repo.py       # User CRUD

│       ├── notes_repo.py      # Notes CRUD

│       └── admin_repo.py      # Admin stats

│

├── handlers/

│   ├── start.py               # Start & menu

│   ├── ai_assistant.py        # AI chat

│   ├── calculator.py          # Calculator

│   ├── translator.py          # Translation

│   ├── notes.py               # Notes

│   ├── language.py            # Language switch

│   └── admin.py               # Admin panel

│

├── services/

│   ├── ai_service.py          # OpenAI wrapper

│   ├── translation_service.py # Translation logic

│   ├── calculator_service.py  # Safe math eval

│   ├── broadcast_service.py   # Admin broadcast

│   └── rate_limiter.py        # Rate limiting

│

├── keyboards/

│   ├── main_menu.py           # Main menu keyboard

│   ├── calculator_kb.py       # Calculator buttons

│   ├── language_kb.py         # Language selector

│   ├── notes_kb.py            # Notes buttons

│   ├── translator_kb.py       # Translator buttons

│   └── admin_kb.py            # Admin panel buttons

│

├── middlewares/

│   ├── auth_middleware.py     # Ban check + registration

│   ├── rate_limit_middleware.py # Anti-spam

│   └── maintenance_middleware.py # Maintenance gate

│

├── locales/

│   ├── translator.py          # i18n engine

│   ├── en.py                  # English strings

│   ├── hi.py                  # Hindi strings

│   ├── bn.py                  # Bengali strings

│   └── ar.py                  # Arabic strings

│

├── utils/

│   ├── logger.py              # Logging setup

│   ├── helpers.py             # Utility functions

│   └── validators.py          # Input validation

│

└── logs/                      # Auto-created at runtime

└── studybuddy.log

---

## ⚙️ Prerequisites

Before deploying, make sure you have:

- ✅ Python 3.11 or higher
- ✅ A Telegram Bot Token from [@BotFather](https://t.me/BotFather)
- ✅ A MongoDB Atlas account (free tier works)
- ✅ An OpenAI API Key from [platform.openai.com](https://platform.openai.com)
- ✅ A [Render.com](https://render.com) account (free tier works)

---

## 🚀 Quick Start — Local Development

### Step 1 — Clone the Repository

```bash
git clone https://github.com/yourusername/StudyBuddyV3BOT.git
cd StudyBuddyV3BOT
```

### Step 2 — Create Virtual Environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### Step 3 — Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4 — Configure Environment

```bash
# Copy the template
cp .env.template .env

# Open and fill in your values
nano .env        # Linux/macOS
notepad .env     # Windows
```

**Required variables to fill:**

| Variable | Where to get it |
|---|---|
| `BOT_TOKEN` | [@BotFather](https://t.me/BotFather) on Telegram |
| `MONGO_URI` | [MongoDB Atlas](https://cloud.mongodb.com) → Connect → Drivers |
| `OPENAI_API_KEY` | [OpenAI Platform](https://platform.openai.com/api-keys) |
| `ADMIN_IDS` | [@userinfobot](https://t.me/userinfobot) on Telegram |

### Step 5 — Run the Bot

```bash
python main.py
```

You should see:
✅ MongoDB connected successfully.

📡 Starting polling...

🚀 StudyBuddyV3BOT is Online!

---

## ☁️ Deploy on Render.com (Recommended)

### Step 1 — Push to GitHub

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/yourusername/StudyBuddyV3BOT.git
git push -u origin main
```

### Step 2 — Create a New Web Service on Render

1. Go to [render.com](https://render.com) and log in
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub repository
4. Fill in the settings:

| Field | Value |
|---|---|
| **Name** | `studybuddyv3bot` |
| **Region** | `Oregon (US West)` or nearest |
| **Branch** | `main` |
| **Runtime** | `Python 3` |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `python main.py` |
| **Instance Type** | `Free` (or Starter for production) |

### Step 3 — Add Environment Variables

In Render dashboard → **Environment** tab, add all variables from your `.env` file:
BOT_TOKEN          = your_bot_token

MONGO_URI          = your_mongodb_uri

OPENAI_API_KEY     = your_openai_key

ADMIN_IDS          = 123456789

DB_NAME            = studybuddy_db

OPENAI_MODEL       = gpt-4o-mini

OPENAI_MAX_TOKENS  = 1000

OPENAI_TEMPERATURE = 0.7

ENVIRONMENT        = production

LOG_LEVEL          = INFO

...

### Step 4 — Deploy

Click **"Create Web Service"** — Render will automatically:
- Install dependencies from `requirements.txt`
- Start the bot with `python main.py`
- Restart automatically on crashes

> ⚠️ **Important for Render Free Tier:**
> Free services sleep after 15 minutes of inactivity.
> Use [UptimeRobot](https://uptimerobot.com) (free) to ping your Render URL every 5 minutes to keep it alive.

---

## 🗄️ MongoDB Atlas Setup

### Step 1 — Create Free Cluster

1. Go to [cloud.mongodb.com](https://cloud.mongodb.com)
2. Create a free account
3. Click **"Build a Database"** → **M0 Free Tier**
4. Choose a cloud provider and region

### Step 2 — Create Database User

1. Go to **Database Access** → **Add New User**
2. Set username and password
3. Give **"Read and write to any database"** permission

### Step 3 — Whitelist IP Address

1. Go to **Network Access** → **Add IP Address**
2. For Render: click **"Allow Access from Anywhere"** (`0.0.0.0/0`)

### Step 4 — Get Connection String

1. Go to **Database** → **Connect** → **Drivers**
2. Copy the connection string
3. Replace `<password>` with your actual password
4. Paste into `MONGO_URI` in your `.env`

---

## 🔑 Getting API Keys

### Telegram Bot Token

Open Telegram → Search @BotFather
Send /newbot
Choose a name: StudyBuddyV3
Choose a username: StudyBuddyV3BOT
Copy the token provided


### OpenAI API Key

Go to https://platform.openai.com/api-keys
Click "Create new secret key"
Give it a name: StudyBuddyBot
Copy the key (shown only once!)
Add billing: https://platform.openai.com/account/billing


### Your Telegram Admin ID

Open Telegram → Search @userinfobot
Send /start
Copy your numeric "Id" value
Paste into ADMIN_IDS in .env


---

## 🤖 Bot Commands Reference

| Command | Description |
|---|---|
| `/start` | Launch bot & show main menu |
| `/help` | Show help information |
| `/menu` | Open main menu |
| `/cancel` | Cancel current operation |
| `/admin` | Open admin panel (admins only) |

> Most interactions use **inline buttons** — very few commands needed.

---

## 🎛️ Admin Panel Guide

Access the admin panel with `/admin` command (admin IDs only).

| Feature | Description |
|---|---|
| 👥 Total Users | See total registered users |
| 📊 Active Users | Users active in last 24h / 7d |
| 📢 Broadcast | Send message/media to all users |
| 🚫 Ban User | Ban by Telegram user ID |
| ✅ Unban User | Unban by Telegram user ID |
| 🔧 Maintenance | Toggle maintenance mode on/off |
| 📈 API Stats | View OpenAI usage statistics |
| 📋 Error Logs | View recent bot errors |

---

## 🔒 Security Features

- ✅ Admin ID-based access control
- ✅ Per-user rate limiting (anti-spam)
- ✅ Safe math expression evaluation (no `eval()`)
- ✅ Input validation on all user inputs
- ✅ Ban system stored in database
- ✅ Maintenance mode to lock all non-admin access
- ✅ Environment-based secrets (never hardcoded)
- ✅ Global error handler with admin notifications

---

## 📊 Tech Stack

| Technology | Purpose | Version |
|---|---|---|
| Python | Core language | 3.11+ |
| python-telegram-bot | Telegram API | 21.x |
| Motor | Async MongoDB driver | 3.x |
| OpenAI | AI responses | 1.x |
| deep-translator | Text translation | 1.x |
| python-dotenv | Env config | 1.x |
| aiohttp | Async HTTP | 3.x |

---

## 🐛 Troubleshooting

### Bot not responding
```bash
# Check your BOT_TOKEN is correct
# Make sure polling is running
python main.py
```

### MongoDB connection error
```bash
# Check MONGO_URI format
# Make sure IP is whitelisted in Atlas
# Verify username/password in URI
```

### OpenAI errors
```bash
# Check OPENAI_API_KEY is valid
# Make sure billing is set up at platform.openai.com
# Check rate limits on your OpenAI plan
```

### Render deployment failing
```bash
# Check Build Command: pip install -r requirements.txt
# Check Start Command: python main.py
# Check all env variables are set in Render dashboard
```

---

## 📁 Logs

Logs are stored in `logs/studybuddy.log` with automatic rotation:
- Max file size: 10MB
- Keeps last 5 backup files
- Console output + file output simultaneously

```bash
# View live logs locally
tail -f logs/studybuddy.log

# On Render: check the Logs tab in dashboard
```

---

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch: `git checkout -b feature/amazing-feature`
3. Commit your changes: `git commit -m 'Add amazing feature'`
4. Push to the branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License.

---

## 👨‍💻 Author

Built with ❤️ as a production-ready SaaS Telegram bot.

---

## ⭐ Support

If this project helped you, please give it a ⭐ on GitHub!

For issues, open a [GitHub Issue](https://github.com/yourusername/StudyBuddyV3BOT/issues).

