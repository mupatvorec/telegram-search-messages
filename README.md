# 📖 Инструкция по установке и запуску на Beget VPS

## Что делает бот
- Мониторит Telegram-чаты и каналы от имени вашего аккаунта (userbot)
- При нахождении ключевого слова присылает уведомление в Telegram-бот
- Уведомление содержит: текст сообщения, ссылку, имя и контакт автора

---

## Шаг 1 — Получить данные для API

### 1.1 API ID и API Hash
1. Зайдите на https://my.telegram.org
2. Войдите под своим номером телефона
3. Перейдите в **API Development Tools**
4. Создайте новое приложение (название любое)
5. Скопируйте `api_id` и `api_hash`

### 1.2 Создать бота
1. Напишите @BotFather в Telegram
2. Отправьте `/newbot`
3. Придумайте имя и username для бота
4. Скопируйте токен (вида `1234567890:AABB...`)

### 1.3 Узнать свой Telegram ID
1. Напишите @userinfobot в Telegram
2. Он покажет ваш `Id` — скопируйте его

---

## Шаг 2 — Подключиться к серверу Beget

Beget даёт SSH-доступ. Подключитесь через терминал:
```bash
ssh username@your-server-ip
```
Или через встроенный SSH-терминал в панели Beget.

---

## Шаг 3 — Загрузить файлы на сервер

Загрузите папку `tg_monitor_bot` на сервер через:
- **FTP-клиент** (FileZilla, Cyberduck)
- Или команду `scp`:
```bash
scp -r tg_monitor_bot/ username@your-server-ip:/home/username/
```

---

## Шаг 4 — Установка на сервере

Подключитесь по SSH и выполните:

```bash
# Перейдите в папку с ботом
cd ~/tg_monitor_bot

# Создайте виртуальное окружение Python
python3 -m venv venv

# Активируйте его
source venv/bin/activate

# Установите зависимости
pip install -r requirements.txt
```

---

## Шаг 5 — Настройка конфигурации

```bash
# Скопируйте пример конфига
cp .env.example .env

# Откройте для редактирования
nano .env
```

Заполните файл `.env`:
```
API_ID=ваш_api_id
API_HASH=ваш_api_hash
BOT_TOKEN=токен_от_botfather
OWNER_ID=ваш_telegram_id
SESSION_NAME=monitor_session
```

Сохранить: `Ctrl+O`, выйти: `Ctrl+X`

---

## Шаг 6 — Первый запуск (создание сессии)

При первом запуске Telethon попросит авторизацию:

```bash
source venv/bin/activate
python main.py
```

Вам придёт код в Telegram — введите его в терминале.
После авторизации бот запустится. Проверьте что всё работает (напишите `/start` боту).

Остановите бот: `Ctrl+C`

---

## Шаг 7 — Массовое добавление чатов (опционально)

Отредактируйте `chats_list.txt` — добавьте чаты по одному на строку:
```
@mychannel
https://t.me/mygroup
```

Запустите скрипт:
```bash
python bulk_add_chats.py
```

---

## Шаг 8 — Автозапуск через systemd (работает даже после перезагрузки)

### 8.1 Настройте service-файл

```bash
nano tg-monitor.service
```

Замените `YOUR_USERNAME` на ваш логин на сервере (команда `whoami`).

### 8.2 Установите службу

```bash
# Скопируйте service-файл
sudo cp tg-monitor.service /etc/systemd/system/

# Перезагрузите systemd
sudo systemctl daemon-reload

# Включите автозапуск
sudo systemctl enable tg-monitor

# Запустите бота
sudo systemctl start tg-monitor
```

### 8.3 Проверьте статус

```bash
sudo systemctl status tg-monitor
```

Должно показать `Active: active (running)`

---

## Полезные команды для управления

```bash
# Посмотреть статус
sudo systemctl status tg-monitor

# Остановить бота
sudo systemctl stop tg-monitor

# Перезапустить бота
sudo systemctl restart tg-monitor

# Посмотреть логи (последние 50 строк)
sudo journalctl -u tg-monitor -n 50

# Следить за логами в реальном времени
sudo journalctl -u tg-monitor -f
```

---

## Команды в боте

| Команда | Описание |
|---------|----------|
| `/start` | Главное меню |
| `/words` | Показать все ключевые слова |
| `/addword слово` | Добавить ключевое слово/фразу |
| `/delword слово` | Удалить ключевое слово |
| `/chats` | Список чатов для мониторинга |
| `/addchat @username` | Добавить чат |
| `/delchat @username` | Удалить чат |
| `/status` | Статистика и статус |
| `/help` | Справка |

---

## Что придёт в уведомлении

```
🔔 Найдено совпадение!
━━━━━━━━━━━━━━━━━━━━
🔑 Ключевые слова: `ищу подрядчика`
💬 Чат: Название чата
👤 Автор: @username
━━━━━━━━━━━━━━━━━━━━
📝 Сообщение:
Текст сообщения целиком...
━━━━━━━━━━━━━━━━━━━━
🔗 Перейти к сообщению
```

---

## Возможные проблемы

**Ошибка при добавлении чата:**
- Чат должен быть публичным
- Или userbot уже должен быть в нём

**Бот не реагирует на команды:**
- Убедитесь что `OWNER_ID` в `.env` — это именно ваш ID

**Сессия истекла:**
- Удалите файл `monitor_session.session` и запустите `python main.py` вручную
