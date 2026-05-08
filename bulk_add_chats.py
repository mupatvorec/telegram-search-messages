"""
Скрипт для массового добавления чатов из файла.
Запускать один раз после первоначальной настройки.

Формат файла chats_list.txt (по одному чату на строку):
    @mychannel
    https://t.me/mychannel
    @mygroup
"""

import asyncio
import os
from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.tl.functions.channels import JoinChannelRequest

from database import Database

load_dotenv()

API_ID = int(os.getenv('API_ID'))
API_HASH = os.getenv('API_HASH')
SESSION_NAME = os.getenv('SESSION_NAME', 'monitor_session')

CHATS_FILE = 'chats_list.txt'


async def bulk_add():
    db = Database('monitor.db')
    await db.init()

    if not os.path.exists(CHATS_FILE):
        print(f"❌ Файл {CHATS_FILE} не найден!")
        print("Создайте его и добавьте по одному чату на строку:")
        print("  @mychannel")
        print("  https://t.me/mychannel")
        return

    with open(CHATS_FILE, 'r', encoding='utf-8') as f:
        lines = [l.strip() for l in f if l.strip() and not l.startswith('#')]

    if not lines:
        print("❌ Файл пустой!")
        return

    print(f"📋 Найдено {len(lines)} чатов для добавления...\n")

    async with TelegramClient(SESSION_NAME, API_ID, API_HASH) as client:
        for identifier in lines:
            try:
                entity = await client.get_entity(identifier)
                title = getattr(entity, 'title', None) or getattr(entity, 'first_name', 'Без названия')
                username = getattr(entity, 'username', None)
                chat_id = str(entity.id)

                # Вступаем в чат
                try:
                    await client(JoinChannelRequest(entity))
                    print(f"  ✅ Вступил в: {title}")
                except Exception:
                    print(f"  ℹ️  Уже состою в: {title}")

                # Добавляем в БД
                added = await db.add_chat(chat_id, title, username)
                status = "добавлен" if added else "уже есть"
                print(f"  📌 {title} — {status} (ID: {chat_id})\n")

                # Небольшая пауза чтобы не получить флуд-бан
                await asyncio.sleep(2)

            except Exception as e:
                print(f"  ❌ Ошибка для {identifier}: {e}\n")

    print("✅ Готово!")

    # Показываем итоговый список
    chats = await db.get_chats()
    print(f"\n📊 Итого чатов в мониторинге: {len(chats)}")


if __name__ == '__main__':
    asyncio.run(bulk_add())
