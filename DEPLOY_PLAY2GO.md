# 🚀 Деплой на play2go.cloud (Ubuntu 24)

## Два способа: Docker (рекомендуется) или без Docker (systemd)

---

## ✅ СПОСОБ 1: Docker + docker-compose (рекомендуется)

### 1. Покупка и подключение к VPS

1. Купить VPS на **play2go.cloud** → выбрать **Ubuntu 24.04**
2. Получить IP-адрес, логин `root`, пароль
3. Подключиться:
```bash
ssh root@<ВАШ_IP>
```

---

### 2. Первичная настройка Ubuntu 24

```bash
# Обновить систему
apt update && apt upgrade -y

# Установить базовые утилиты
apt install -y curl wget git nano htop ufw fail2ban

# Настроить фаервол
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw --force enable

# Создать пользователя (не работать от root)
adduser botuser
usermod -aG sudo botuser
usermod -aG docker botuser 2>/dev/null || true
```

---

### 3. Установка Docker на Ubuntu 24

```bash
# Удалить старые версии если есть
apt remove -y docker docker-engine docker.io containerd runc 2>/dev/null || true

# Установить зависимости
apt install -y ca-certificates curl gnupg lsb-release

# Добавить GPG ключ Docker
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
  gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg

# Добавить репозиторий Docker
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | \
  tee /etc/apt/sources.list.d/docker.list > /dev/null

# Установить Docker
apt update
apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Запустить Docker
systemctl enable docker
systemctl start docker

# Проверить
docker --version
docker compose version
```

---

### 4. Загрузка проекта на сервер

**Вариант A — через Git (если проект на GitHub):**
```bash
cd /opt
git clone https://github.com/ВАШ_USERNAME/prompt-bot.git
cd prompt-bot
```

**Вариант B — загрузить файлы через scp с вашего компьютера:**

На **вашем компьютере** (Windows) — открыть cmd/PowerShell:
```powershell
# Загрузить весь проект на сервер
scp -r C:\Users\Print\prompt-bot root@<ВАШ_IP>:/opt/prompt-bot
```

Затем на сервере:
```bash
cd /opt/prompt-bot
```

---

### 5. Создать .env файл на сервере

```bash
cd /opt/prompt-bot
cp .env.example .env
nano .env
```

Заполнить `.env`:
```env
# ─── Обязательно ──────────────────────────────────────────────────────────────
BOT_TOKEN=7XXXXXXXXX:AAF...ваш_токен_от_BotFather...

# Ваш Telegram user_id (узнать у @userinfobot)
ADMIN_IDS=7901094710

# ─── Database ─────────────────────────────────────────────────────────────────
# SQLite (просто, без PostgreSQL):
DATABASE_URL=sqlite+aiosqlite:///./data/bot.db

# PostgreSQL (если хотите):
# DATABASE_URL=postgresql+asyncpg://botuser:botpassword@db:5432/botdb

# ─── Платежи ──────────────────────────────────────────────────────────────────
# DEMO режим (файл доставляется без реальной оплаты):
DEMO_PAYMENT=true

# Robokassa (заполнить когда подключите реальные платежи):
ROBOKASSA_MERCHANT_LOGIN=
ROBOKASSA_PASSWORD1=
ROBOKASSA_PASSWORD2=
ROBOKASSA_TEST_MODE=true

# ─── Прочее ───────────────────────────────────────────────────────────────────
DEBUG=false
LOG_LEVEL=INFO
```

Сохранить: `Ctrl+O`, Enter, `Ctrl+X`

---

### 6. Настроить docker-compose для продакшна

```bash
nano docker-compose.yml
```

Убедитесь что файл выглядит так (или обновите):
```yaml
version: "3.9"

services:
  bot:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: prompt-bot
    restart: unless-stopped
    env_file: .env
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    networks:
      - bot-network

networks:
  bot-network:
    driver: bridge
```

---

### 7. Создать папки и запустить

```bash
# Создать папки для данных
mkdir -p /opt/prompt-bot/data /opt/prompt-bot/logs

# Прав доступа
chmod 755 /opt/prompt-bot/data /opt/prompt-bot/logs

# Собрать образ
cd /opt/prompt-bot
docker compose build --no-cache

# Применить миграции БД
docker compose run --rm bot python -m alembic upgrade head

# Запустить бот
docker compose up -d

# Проверить что работает
docker compose logs -f --tail=50
```

---

### 8. Управление ботом

```bash
# Статус
docker compose ps

# Логи в реальном времени
docker compose logs -f bot

# Остановить
docker compose down

# Перезапустить
docker compose restart bot

# Обновить (после изменений кода)
docker compose down
docker compose build --no-cache
docker compose run --rm bot python -m alembic upgrade head
docker compose up -d
```

---

### 9. Автозапуск после перезагрузки сервера

Docker уже настроен на автозапуск (`restart: unless-stopped`). Проверьте:
```bash
# Docker должен запускаться автоматически
systemctl is-enabled docker
# должно вернуть: enabled
```

---

## ✅ СПОСОБ 2: Без Docker (Python + Systemd)

### 1-3. Подключение и настройка Ubuntu 24 — те же шаги выше

### 4. Установить Python 3.11+

```bash
# Ubuntu 24 поставляется с Python 3.12, проверить:
python3 --version

# Если нужен 3.11:
apt install -y python3.11 python3.11-venv python3.11-dev

# Установить pip
apt install -y python3-pip
```

### 5. Загрузить проект

```bash
cd /opt
# Через scp (с вашего компьютера):
# scp -r C:\Users\Print\prompt-bot root@<IP>:/opt/prompt-bot

# или git clone
git clone https://github.com/ВАШЕ_РЕПО/prompt-bot.git
cd prompt-bot
```

### 6. Создать виртуальное окружение

```bash
cd /opt/prompt-bot
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 7. Создать .env

```bash
cp .env.example .env
nano .env
# Заполнить так же как в способе 1
```

### 8. Применить миграции

```bash
cd /opt/prompt-bot
source venv/bin/activate
mkdir -p data logs
python -m alembic upgrade head
```

### 9. Настроить systemd service

```bash
nano /etc/systemd/system/prompt-bot.service
```

Вставить:
```ini
[Unit]
Description=Telegram Prompt Pack Bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/prompt-bot
Environment=PATH=/opt/prompt-bot/venv/bin:/usr/local/bin:/usr/bin:/bin
EnvironmentFile=/opt/prompt-bot/.env
ExecStart=/opt/prompt-bot/venv/bin/python -m bot.main
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=prompt-bot

# Лимиты
LimitNOFILE=65536
TimeoutStartSec=30
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
```

### 10. Запустить сервис

```bash
# Перезагрузить systemd
systemctl daemon-reload

# Включить автозапуск
systemctl enable prompt-bot

# Запустить
systemctl start prompt-bot

# Проверить статус
systemctl status prompt-bot

# Смотреть логи
journalctl -u prompt-bot -f
```

---

## 🔧 Устранение проблем

### TelegramConflictError (два экземпляра бота)

```bash
# Docker:
docker compose down
sleep 5
docker compose up -d

# Systemd:
systemctl stop prompt-bot
sleep 5
systemctl start prompt-bot

# Убить все python процессы вручную:
pkill -f "python.*bot.main"
sleep 3
systemctl start prompt-bot
```

### Проверить логи

```bash
# Docker:
docker compose logs --tail=100 bot

# Systemd:
journalctl -u prompt-bot --since "1 hour ago"

# Файловые логи:
tail -f /opt/prompt-bot/logs/bot_$(date +%Y-%m-%d).log
```

### Обновить код на сервере

**Docker:**
```bash
cd /opt/prompt-bot

# Если через git:
git pull

# Если через scp (с вашего компьютера):
# scp -r C:\Users\Print\prompt-bot\bot root@<IP>:/opt/prompt-bot/

docker compose down
docker compose build --no-cache
docker compose run --rm bot python -m alembic upgrade head
docker compose up -d
```

**Systemd:**
```bash
cd /opt/prompt-bot
git pull   # или загрузить файлы через scp

systemctl stop prompt-bot
source venv/bin/activate
pip install -r requirements.txt  # если новые зависимости
python -m alembic upgrade head
systemctl start prompt-bot
```

---

## 📁 Быстрая загрузка файлов через scp

Открыть **PowerShell на вашем Windows** и выполнить:

```powershell
# Загрузить весь проект
scp -r C:\Users\Print\prompt-bot root@<ВАШ_IP>:/opt/prompt-bot

# Загрузить только код бота (обновление)
scp -r C:\Users\Print\prompt-bot\bot root@<ВАШ_IP>:/opt/prompt-bot/

# Загрузить конкретный файл
scp C:\Users\Print\prompt-bot\bot\handlers\purchase.py root@<ВАШ_IP>:/opt/prompt-bot/bot/handlers/
```

---

## 📊 Мониторинг

```bash
# Использование ресурсов
htop

# Место на диске
df -h

# Размер базы данных
ls -lh /opt/prompt-bot/data/

# Docker статистика
docker stats prompt-bot
```

---

## 🔑 Краткий чеклист деплоя

- [ ] 1. Купить VPS на play2go.cloud (Ubuntu 24.04)
- [ ] 2. Подключиться по SSH: `ssh root@<IP>`
- [ ] 3. `apt update && apt upgrade -y`
- [ ] 4. Установить Docker (команды в разделе 3)
- [ ] 5. Загрузить проект: `scp` или `git clone`
- [ ] 6. Создать `.env` с токеном бота и ADMIN_IDS
- [ ] 7. `mkdir -p data logs`
- [ ] 8. `docker compose build --no-cache`
- [ ] 9. `docker compose run --rm bot python -m alembic upgrade head`
- [ ] 10. `docker compose up -d`
- [ ] 11. `docker compose logs -f` — убедиться что бот запустился
- [ ] 12. Написать `/start` боту в Telegram ✅
