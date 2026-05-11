# Инструкция по подключению Robokassa

## Выбор режима работы

| Хостинг | Метод проверки оплаты | Нужен ли открытый порт? |
|---|---|---|
| **bothost.ru** | 🔄 Poll (бот сам спрашивает Robokassa) | ❌ Не нужен |
| **TimeWeb VPS** | 📡 Webhook (Robokassa сам уведомляет) | ✅ Нужен |
| **Любой VPS** | 📡 Webhook | ✅ Нужен |

> **bothost.ru** — используйте режим **poll** (описан ниже).
> Webhook там работать **не будет** — нет публичного IP.

---

## Шаг 1 — Регистрация в Robokassa

1. Перейдите на https://robokassa.com и нажмите **«Подключиться»**
2. Заполните форму регистрации (потребуется ИП или самозанятый)
3. После регистрации войдите в **Личный кабинет** → https://merchant.robokassa.ru/

---

## Шаг 2 — Создание магазина

1. В личном кабинете: **Магазины** → **Добавить магазин**
2. Заполните:
   - **Название магазина** — любое (например, "AI Prompts Bot")
   - **URL магазина** — URL вашего сайта или `https://t.me/ваш_бот`
   - **Валюта** — RUB
3. Нажмите **Сохранить**

---

## Шаг 3 — Получение credentials

В настройках магазина найдите:

| Поле в Robokassa | Переменная в .env |
|---|---|
| **Логин магазина** | `ROBOKASSA_LOGIN` |
| **Пароль #1** | `ROBOKASSA_PASSWORD1` |
| **Пароль #2** | `ROBOKASSA_PASSWORD2` |

> ⚠️ Пароль #1 используется для создания ссылок оплаты.
> Пароль #2 используется для верификации уведомлений от Robokassa.
> Это РАЗНЫЕ пароли — не перепутайте!

---

## Шаг 4 — Настройка URL уведомлений

В настройках магазина → **URL для уведомлений**:

```
ResultURL:  https://ВАШ_ДОМЕН/payment/result
SuccessURL: https://ВАШ_ДОМЕН/payment/success
FailURL:    https://ВАШ_ДОМЕН/payment/fail
```

> **Важно:** ResultURL должен быть доступен из интернета.
> На локальном компьютере не работает — нужен VPS или ngrok для тестирования.

**Метод отправки ResultURL:** выберите **POST**

---

## Шаг 5 — Узнать свою комиссию

В личном кабинете → **Тарифы** посмотрите свой процент комиссии.

Стандартные тарифы:
- **Физлица / самозанятые:** ~5-6%
- **ИП / ООО:** ~3.9%

Установите точное значение в `.env`:
```
ROBOKASSA_COMMISSION_RATE=0.05   # 5%
```

---

## Шаг 6 — Заполнить .env файл

Откройте файл `.env` и заполните:

```env
# Robokassa
ROBOKASSA_LOGIN=ваш_логин_магазина
ROBOKASSA_PASSWORD1=пароль_номер_1
ROBOKASSA_PASSWORD2=пароль_номер_2
ROBOKASSA_COMMISSION_RATE=0.05
ROBOKASSA_TEST_MODE=True         # True пока тестируете!

# Webhook (ваш VPS на TimeWeb)
WEBHOOK_HOST=https://ваш-домен.ru
WEBHOOK_PORT=8080
WEBHOOK_PATH=/payment/result
```

---

## Шаг 7 — Тестовый режим

Пока `ROBOKASSA_TEST_MODE=True` — реальные деньги **НЕ** списываются.

Тестовые данные карты для оплаты на странице Robokassa:
```
Номер карты:  4000 0000 0000 0002
Срок:         12/25
CVV:          123
```

Проверьте полный flow:
1. Нажмите "Купить" в боте
2. Перейдите по ссылке на страницу Robokassa
3. Оплатите тестовой картой
4. Убедитесь что бот прислал файл

---

## Шаг 8 — Переход в боевой режим

Когда всё проверено:
1. В `.env` измените: `ROBOKASSA_TEST_MODE=False`
2. Перезапустите бота
3. Проведите один реальный платёж для проверки

---

## Настройка VPS (TimeWeb) для webhook

Робокасса стучится на ваш сервер — порт 8080 должен быть открыт.

### Через Nginx (рекомендуется):

```nginx
location /payment/ {
    proxy_pass http://127.0.0.1:8080;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

### Открыть порт в firewall TimeWeb:

В панели TimeWeb → **Серверы** → ваш сервер → **Файрвол** → добавить правило:
- Порт: `8080`
- Протокол: `TCP`
- Источник: `0.0.0.0/0`

### Или напрямую без Nginx:

В `.env` установите порт как часть `WEBHOOK_HOST` и откройте его напрямую:
```
WEBHOOK_HOST=https://ваш-ip:8080
WEBHOOK_PORT=8080
```

В Robokassa укажите: `ResultURL: http://ВАШ_IP:8080/payment/result`

---

## Проверка работы webhook

После запуска бота выполните тест:

```bash
curl -X POST http://localhost:8080/payment/result \
  -d "OutSum=315.00&InvId=1&SignatureValue=TEST"
```

Должен вернуть: `BAD_SIGNATURE` (это нормально — значит сервер работает)

---

## 🤖 Настройка для bothost.ru (без webhook)

На bothost.ru нет открытых портов, поэтому используется **режим Poll** — бот сам проверяет оплату через Robokassa API каждые 30 секунд.

### .env для bothost.ru:

```env
BOT_TOKEN=ваш_токен
ADMIN_IDS=ваш_id

# Robokassa
ROBOKASSA_LOGIN=ваш_логин
ROBOKASSA_PASSWORD1=пароль_1
ROBOKASSA_PASSWORD2=пароль_2
ROBOKASSA_COMMISSION_RATE=0.05
ROBOKASSA_TEST_MODE=True

# Для bothost.ru — НЕ указывайте WEBHOOK_HOST, укажите poll
PAYMENT_CHECK_MODE=poll
PAYMENT_POLL_INTERVAL=30
PAYMENT_EXPIRE_MINUTES=60

# WEBHOOK_HOST — оставьте пустым или не указывайте вообще

DATABASE_URL=sqlite+aiosqlite:///./data/bot.db
```

### Настройки в Robokassa для poll режима:

В Robokassa личном кабинете → настройки магазина:
- **ResultURL** — можно оставить пустым или указать любой URL (он не используется в poll режиме)
- **SuccessURL** — URL куда перенаправится пользователь после оплаты в браузере (необязательно)
- **FailURL** — URL куда перенаправится пользователь при ошибке (необязательно)

> В poll режиме бот сам проверяет статус оплаты через API — ResultURL **не нужен**.

### Как загрузить на bothost.ru:

1. Зарегистрируйтесь на https://bothost.ru
2. Создайте новый бот-проект
3. Загрузите все файлы проекта
4. В настройках проекта укажите переменные окружения из вашего `.env`
5. Укажите команду запуска: `python -m bot.main`
6. Запустите бота

### Как проверить что poll работает:

Запустите бота и смотрите логи — должны появиться строки:
```
Payment mode: POLL (interval=30s, expire=60m)
Payment poller started | interval=30s expire=60m
```

После тестовой оплаты через 30 секунд должно появиться:
```
Robokassa poll: payment confirmed | inv_id=1 state=100
Poller: purchase completed | inv_id=1 user_id=...
Poller: file delivered | user_id=...
```

---

## Диагностика

Ключевые строки в логах:

**Poll режим (bothost.ru):**
- `Payment mode: POLL` — поллер запущен
- `Poller: checking N pending purchase(s)` — проверка идёт
- `Robokassa poll: payment confirmed` — оплата подтверждена
- `Poller: purchase completed` — покупка засчитана
- `Poller: file delivered` — файл отправлен

**Webhook режим (VPS):**
- `Robokassa webhook server started` — webhook сервер запущен
- `Robokassa ResultURL received` — пришло уведомление
- `Robokassa signature verified OK` — подпись верна
- `Purchase completed via Robokassa` — покупка засчитана
- `File delivered after Robokassa payment` — файл отправлен
