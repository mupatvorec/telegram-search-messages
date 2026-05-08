"""
База данных SQLite для хранения ключевых слов и чатов
"""

import aiosqlite
import logging

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path

    async def init(self):
        """Создание таблиц при первом запуске"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS keywords (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    word TEXT UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS chats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id TEXT UNIQUE NOT NULL,
                    chat_title TEXT,
                    chat_username TEXT,
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS matches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id TEXT,
                    chat_title TEXT,
                    message_id INTEGER,
                    sender_name TEXT,
                    sender_username TEXT,
                    keyword TEXT,
                    message_text TEXT,
                    message_link TEXT,
                    found_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.commit()
        logger.info("✅ База данных инициализирована")

    # ─── KEYWORDS ──────────────────────────────────────────────────────────────

    async def add_keyword(self, word: str) -> bool:
        """Добавить ключевое слово. Возвращает True если добавлено, False если уже есть"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "INSERT INTO keywords (word) VALUES (?)",
                    (word.lower().strip(),)
                )
                await db.commit()
            return True
        except aiosqlite.IntegrityError:
            return False

    async def delete_keyword(self, word: str) -> bool:
        """Удалить ключевое слово. Возвращает True если удалено"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "DELETE FROM keywords WHERE word = ?",
                (word.lower().strip(),)
            )
            await db.commit()
            return cursor.rowcount > 0

    async def get_keywords(self) -> list[str]:
        """Получить все ключевые слова"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT word FROM keywords ORDER BY word")
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

    # ─── CHATS ─────────────────────────────────────────────────────────────────

    async def add_chat(self, chat_id: str, title: str = None, username: str = None) -> bool:
        """Добавить чат для мониторинга"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "INSERT INTO chats (chat_id, chat_title, chat_username) VALUES (?, ?, ?)",
                    (str(chat_id), title, username)
                )
                await db.commit()
            return True
        except aiosqlite.IntegrityError:
            return False

    async def delete_chat(self, chat_id: str) -> bool:
        """Удалить чат из мониторинга"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "DELETE FROM chats WHERE chat_id = ?",
                (str(chat_id),)
            )
            await db.commit()
            return cursor.rowcount > 0

    async def get_chats(self) -> list[dict]:
        """Получить все активные чаты"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM chats WHERE is_active = 1 ORDER BY chat_title"
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_chat_ids(self) -> list[str]:
        """Получить список ID активных чатов"""
        chats = await self.get_chats()
        return [c['chat_id'] for c in chats]

    async def update_chat_title(self, chat_id: str, title: str):
        """Обновить название чата"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE chats SET chat_title = ? WHERE chat_id = ?",
                (title, str(chat_id))
            )
            await db.commit()

    # ─── MATCHES ───────────────────────────────────────────────────────────────

    async def save_match(self, data: dict):
        """Сохранить найденное совпадение"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO matches 
                (chat_id, chat_title, message_id, sender_name, sender_username, keyword, message_text, message_link)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data.get('chat_id'),
                data.get('chat_title'),
                data.get('message_id'),
                data.get('sender_name'),
                data.get('sender_username'),
                data.get('keyword'),
                data.get('message_text'),
                data.get('message_link'),
            ))
            await db.commit()

    async def get_stats(self) -> dict:
        """Статистика"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM matches")
            total = (await cursor.fetchone())[0]

            cursor = await db.execute(
                "SELECT COUNT(*) FROM matches WHERE date(found_at) = date('now')"
            )
            today = (await cursor.fetchone())[0]

            cursor = await db.execute("SELECT COUNT(*) FROM keywords")
            keywords_count = (await cursor.fetchone())[0]

            cursor = await db.execute("SELECT COUNT(*) FROM chats WHERE is_active = 1")
            chats_count = (await cursor.fetchone())[0]

        return {
            'total_matches': total,
            'today_matches': today,
            'keywords_count': keywords_count,
            'chats_count': chats_count
        }
