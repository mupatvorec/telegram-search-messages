"""
Telegram Monitor Bot
Мониторинг публичных каналов и чатов по ключевым словам
"""

import asyncio
import logging
import os
from dotenv import load_dotenv

from telethon import TelegramClient, events
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message

from database import Database
from handlers import register_handlers
from monitor import Monitor

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Конфиг из .env
API_ID = int(os.getenv('API_ID'))
API_HASH = os.getenv('API_HASH')
BOT_TOKEN = os.getenv('BOT_TOKEN')
OWNER_ID = int(os.getenv('OWNER_ID'))
SESSION_NAME = os.getenv('SESSION_NAME', 'monitor_session')


async def main():
    # База данных
    db = Database('monitor.db')
    await db.init()

    # Userbot (читает сообщения из чатов)
    userbot = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    await userbot.start()
    logger.info("✅ Userbot запущен")

    # Notification Bot (отправляет уведомления)
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    # Монитор
    monitor = Monitor(userbot, bot, db, OWNER_ID)

    # Регистрируем хендлеры команд
    register_handlers(dp, db, monitor, OWNER_ID)

    # Запускаем мониторинг
    await monitor.start()

    logger.info("✅ Бот запущен и готов к работе")

    # Запускаем оба в параллели
    await asyncio.gather(
        dp.start_polling(bot, allowed_updates=["message"]),
        userbot.run_until_disconnected()
    )


if __name__ == '__main__':
    asyncio.run(main())
