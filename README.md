# 🤖 AI Prompts Pack Bot

Production-ready Telegram bot for selling a digital product (PDF) — built with **aiogram 3.x**, **SQLAlchemy 2.0**, **Alembic**, **Loguru**, and deployable on **TimeWeb VPS**.

---

## 📁 Project Structure

```
prompt-bot/
├── bot/
│   ├── __init__.py
│   ├── main.py              # Entry point, dispatcher setup
│   ├── config.py            # pydantic-settings configuration
│   ├── logger.py            # Loguru setup + stdlib intercept
│   ├── database.py          # Async SQLAlchemy engine & session
│   ├── models/
│   │   ├── base.py          # DeclarativeBase with timestamps
│   │   ├── user.py          # User model
│   │   ├── product.py       # Product model (single row)
│   │   └── purchase.py      # Purchase model
│   ├── states/
│   │   └── admin_states.py  # FSM states for admin panel
│   ├── keyboards/
│   │   ├── main_kb.py       # User-facing inline keyboards
│   │   └── admin_kb.py      # Admin panel keyboards
│   ├── handlers/
│   │   ├── start.py         # /start, main menu
│   │   ├── catalog.py       # Product view, purchases list
│   │   ├── purchase.py      # Buy flow, payment, PDF delivery
│   │   └── admin.py         # /admin panel with FSM editing
│   ├── services/
│   │   ├── cache.py         # TTL in-memory cache (cachetools)
│   │   ├── product_service.py
│   │   ├── user_service.py
│   │   └── purchase_service.py
│   └── utils/
│       └── text.py          # MarkdownV2 helpers & message templates
├── alembic/
│   ├── env.py               # Async Alembic environment
│   ├── script.py.mako
│   └── versions/
│       └── 20240101_0000_0001_initial_schema.py
├── deploy/
│   ├── prompt-bot.service   # Systemd unit file
│   └── nginx.conf           # Nginx config (for webhook mode)
├── logs/                    # Auto-created, daily rotation
├── data/                    # SQLite DB (dev) or persistent volume
├── Dockerfile               # Multi-stage slim image
├── docker-compose.yml       # Bot + PostgreSQL + migrations
├── requirements.txt
├── alembic.ini
├── .env.example
└── README.md
```

---

## ⚙️ Features

| Feature | Details |
|---|---|
| **Tech stack** | Python 3.11, aiogram 3.x, SQLAlchemy 2.0, Alembic, asyncpg/aiosqlite |
| **Logging** | Loguru — colorful console + daily rotating files (7-day retention) |
| **Caching** | cachetools TTLCache (60s) for product data |
| **UX** | 100% inline keyboards, edit_message (no chat clutter), MarkdownV2 |
| **Payment** | Demo mode (instant delivery) or real Telegram Payments |
| **Admin panel** | /admin — edit name, price, description, buttons, upload PDF |
| **Database** | SQLite (dev) / PostgreSQL (prod) via DATABASE_URL |
| **Deployment** | Docker + docker-compose OR systemd on TimeWeb VPS |

---

## 🚀 Quick Start (Local Development)

### 1. Clone and set up environment

```bash
git clone https://github.com/yourname/prompt-bot.git
cd prompt-bot

python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env — set BOT_TOKEN and ADMIN_IDS at minimum
```

### 3. Run migrations (optional for SQLite — tables auto-created)

```bash
alembic upgrade head
```

### 4. Start the bot

```bash
python -m bot.main
```

---

## 🐳 Docker (Local with PostgreSQL)

```bash
# Copy and configure .env
cp .env.example .env
# Set DATABASE_URL=postgresql+asyncpg://botuser:changeme@postgres:5432/botdb
# Set POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB in .env

# Build and start
docker-compose up -d --build

# View logs
docker-compose logs -f bot

# Run migrations manually if needed
docker-compose run --rm migrate
```

---

## ☁️ Deployment Guide — TimeWeb VPS

### Prerequisites
- TimeWeb VPS with Ubuntu 22.04 (minimum 1 CPU, 1 GB RAM)
- SSH access to the server
- Your bot token from [@BotFather](https://t.me/BotFather)

---

### Method 1: Docker (Recommended)

#### Step 1 — Connect to your VPS

```bash
ssh root@YOUR_SERVER_IP
```

#### Step 2 — Install Docker and Docker Compose

```bash
# Update system
apt update && apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com | sh

# Install Docker Compose plugin
apt install -y docker-compose-plugin

# Verify
docker --version
docker compose version
```

#### Step 3 — Create a deploy user (security best practice)

```bash
useradd -m -s /bin/bash deploy
usermod -aG docker deploy
su - deploy
```

#### Step 4 — Upload the project

**Option A — via Git:**
```bash
git clone https://github.com/yourname/prompt-bot.git /home/deploy/prompt-bot
cd /home/deploy/prompt-bot
```

**Option B — via SCP from your local machine:**
```bash
# Run this on your LOCAL machine:
scp -r ./prompt-bot deploy@YOUR_SERVER_IP:/home/deploy/
```

#### Step 5 — Configure environment

```bash
cd /home/deploy/prompt-bot
cp .env.example .env
nano .env
```

Fill in the following values:
```env
BOT_TOKEN=your_real_bot_token_here
ADMIN_IDS=your_telegram_user_id

# PostgreSQL (Docker internal hostname = "postgres")
DATABASE_URL=postgresql+asyncpg://botuser:StrongPass123@postgres:5432/botdb
POSTGRES_USER=botuser
POSTGRES_PASSWORD=StrongPass123
POSTGRES_DB=botdb

LOG_LEVEL=INFO
DEBUG=false
```

#### Step 6 — Run migrations and start the bot

```bash
# Build images
docker compose build

# Run migrations first
docker compose run --rm migrate

# Start bot and database in background
docker compose up -d bot postgres

# Check status
docker compose ps

# View live logs
docker compose logs -f bot
```

#### Step 7 — Verify the bot is running

```bash
# Check container health
docker compose ps

# Check logs for startup message
docker compose logs bot | grep "Bot started"

# Test: send /start to your bot in Telegram
```

#### Step 8 — Auto-restart on server reboot

Docker's `restart: unless-stopped` policy handles this automatically.
To verify:
```bash
# Simulate reboot
sudo reboot

# After reconnecting:
docker compose -f /home/deploy/prompt-bot/docker-compose.yml ps
```

---

### Method 2: Without Docker (systemd + venv)

#### Step 1 — Install system dependencies

```bash
apt update && apt upgrade -y
apt install -y python3.11 python3.11-venv python3-pip postgresql postgresql-contrib git
```

#### Step 2 — Set up PostgreSQL

```bash
sudo -u postgres psql

-- Inside psql:
CREATE USER botuser WITH PASSWORD 'StrongPass123';
CREATE DATABASE botdb OWNER botuser;
GRANT ALL PRIVILEGES ON DATABASE botdb TO botuser;
\q
```

#### Step 3 — Create app user and directory

```bash
useradd -r -s /bin/false botuser
mkdir -p /opt/prompt-bot
chown botuser:botuser /opt/prompt-bot
```

#### Step 4 — Upload and install

```bash
# Upload project files to /opt/prompt-bot/
# (use git clone or scp)

cd /opt/prompt-bot

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

#### Step 5 — Configure environment

```bash
cp .env.example .env
nano .env
# Set BOT_TOKEN, ADMIN_IDS, DATABASE_URL (postgresql+asyncpg://...)
```

#### Step 6 — Run Alembic migrations

```bash
source /opt/prompt-bot/venv/bin/activate
cd /opt/prompt-bot
alembic upgrade head
```

#### Step 7 — Install systemd service

```bash
cp deploy/prompt-bot.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable prompt-bot
systemctl start prompt-bot

# Check status
systemctl status prompt-bot

# View logs
journalctl -u prompt-bot -f
```

#### Step 8 — Verify

```bash
systemctl status prompt-bot
# Should show: Active: active (running)
```

---

### Updating the Bot

#### Docker update:
```bash
cd /home/deploy/prompt-bot
git pull

# Rebuild and restart
docker compose down
docker compose build
docker compose run --rm migrate   # if there are new migrations
docker compose up -d
```

#### Systemd update:
```bash
cd /opt/prompt-bot
git pull

source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head

systemctl restart prompt-bot
```

---

### Viewing Logs

#### Docker:
```bash
# Live logs
docker compose logs -f bot

# Last 100 lines
docker compose logs --tail=100 bot

# Log files (inside volume)
ls -la /home/deploy/prompt-bot/logs/
cat /home/deploy/prompt-bot/logs/bot_2024-01-15.log
```

#### Systemd:
```bash
# Live journal logs
journalctl -u prompt-bot -f

# Log files
ls /opt/prompt-bot/logs/
tail -f /opt/prompt-bot/logs/bot_$(date +%Y-%m-%d).log
```

---

### Backup

```bash
# Backup PostgreSQL database
docker compose exec postgres pg_dump -U botuser botdb > backup_$(date +%Y%m%d).sql

# Backup SQLite (if using SQLite)
cp data/bot.db backup_bot_$(date +%Y%m%d).db

# Backup logs
tar -czf logs_backup_$(date +%Y%m%d).tar.gz logs/
```

---

## 🔑 Admin Panel

1. Add your Telegram user ID to `ADMIN_IDS` in `.env`
2. Send `/admin` to the bot
3. Available actions:
   - ✏️ Edit product name
   - 💰 Change price
   - 📝 Edit description
   - 🔘 Change buy button text (use `{price}` placeholder)
   - ✅ Change confirm button text
   - 📄 Upload new PDF file
   - 👁 Preview product as users see it
   - 📊 View statistics (users, purchases, revenue)

---

## 💳 Payment Modes

### Demo Mode (default)
Leave `PAYMENT_PROVIDER_TOKEN` empty. When user clicks "Confirm", the purchase is recorded and PDF is delivered immediately — no real payment.

### Real Payments
1. In [@BotFather](https://t.me/BotFather): go to your bot → Payments → connect a provider (Sberbank, YooKassa, etc.)
2. Copy the provider token
3. Set `PAYMENT_PROVIDER_TOKEN=your_token` in `.env`
4. Restart the bot

---

## 📋 Environment Variables Reference

| Variable | Required | Default | Description |
|---|---|---|---|
| `BOT_TOKEN` | ✅ | — | Telegram bot token from @BotFather |
| `ADMIN_IDS` | ✅ | — | Comma-separated admin user IDs |
| `DATABASE_URL` | — | SQLite | Database connection URL |
| `PAYMENT_PROVIDER_TOKEN` | — | empty | Payment provider token (empty = demo) |
| `DEBUG` | — | false | Enable SQLAlchemy query logging |
| `LOG_LEVEL` | — | INFO | Logging level (DEBUG/INFO/WARNING/ERROR) |
| `DEFAULT_PRODUCT_NAME` | — | preset | Product name for first run |
| `DEFAULT_PRODUCT_PRICE` | — | 299 | Product price (RUB) for first run |

---

## 🛠️ Development Commands

```bash
# Run bot
python -m bot.main

# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Show migration history
alembic history

# Check current revision
alembic current
```

---

## 📝 License

MIT License — free to use and modify.
