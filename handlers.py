"""
Хендлеры команд Telegram-бота
"""

import logging
from aiogram import Dispatcher
from aiogram.filters import Command
from aiogram.types import Message

from database import Database
from monitor import Monitor

logger = logging.getLogger(__name__)


def register_handlers(dp: Dispatcher, db: Database, monitor: Monitor, owner_id: int):
    """Регистрация всех команд"""

    def owner_only(func):
        """Декоратор — только владелец"""
        async def wrapper(message: Message):
            if message.from_user.id != owner_id:
                await message.answer("❌ У вас нет доступа к этому боту.")
                return
            await func(message)
        return wrapper

    # ─── /start ────────────────────────────────────────────────────────────────
    @dp.message(Command("start"))
    async def cmd_start(message: Message):
        if message.from_user.id != owner_id:
            await message.answer("❌ У вас нет доступа к этому боту.")
            return
        await message.answer(
            "👋 *Telegram Monitor Bot*\n\n"
            "Бот мониторит чаты и каналы на предмет ключевых слов.\n\n"
            "📋 *Команды:*\n"
            "`/words` — список ключевых слов\n"
            "`/addword слово` — добавить слово\n"
            "`/delword слово` — удалить слово\n\n"
            "`/chats` — список чатов\n"
            "`/addchat @username` — добавить чат\n"
            "`/delchat @username` — удалить чат\n\n"
            "`/status` — статус и статистика\n"
            "`/help` — помощь",
            parse_mode="Markdown"
        )

    # ─── /help ─────────────────────────────────────────────────────────────────
    @dp.message(Command("help"))
    async def cmd_help(message: Message):
        if message.from_user.id != owner_id:
            return
        await message.answer(
            "📖 *Справка*\n\n"
            "*Ключевые слова:*\n"
            "`/addword ищу подрядчика` — добавить фразу\n"
            "`/delword ищу подрядчика` — удалить фразу\n"
            "`/words` — показать все слова\n\n"
            "*Чаты и каналы:*\n"
            "`/addchat @username` — добавить по username\n"
            "`/addchat https://t.me/...` — добавить по ссылке\n"
            "`/delchat @username` — удалить чат\n"
            "`/chats` — список всех чатов\n\n"
            "*Статистика:*\n"
            "`/status` — статус, кол-во совпадений за день\n\n"
            "💡 *Совет:* Можно добавлять целые фразы, например:\n"
            "`/addword ищу специалиста`\n"
            "`/addword нужен разработчик`\n"
            "`/addword кто может сделать`",
            parse_mode="Markdown"
        )

    # ─── KEYWORDS ──────────────────────────────────────────────────────────────

    @dp.message(Command("words"))
    async def cmd_words(message: Message):
        if message.from_user.id != owner_id:
            return
        keywords = await db.get_keywords()
        if not keywords:
            await message.answer(
                "📭 Ключевых слов нет.\n"
                "Добавьте: `/addword ваше слово`",
                parse_mode="Markdown"
            )
            return
        words_list = "\n".join([f"• `{w}`" for w in keywords])
        await message.answer(
            f"🔑 *Ключевые слова ({len(keywords)}):*\n\n{words_list}",
            parse_mode="Markdown"
        )

    @dp.message(Command("addword"))
    async def cmd_addword(message: Message):
        if message.from_user.id != owner_id:
            return
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.answer(
                "⚠️ Укажите слово или фразу:\n`/addword ищу подрядчика`",
                parse_mode="Markdown"
            )
            return

        word = args[1].strip()
        added = await db.add_keyword(word)
        if added:
            await message.answer(f"✅ Добавлено: `{word}`", parse_mode="Markdown")
        else:
            await message.answer(f"ℹ️ Слово `{word}` уже есть в списке.", parse_mode="Markdown")

    @dp.message(Command("delword"))
    async def cmd_delword(message: Message):
        if message.from_user.id != owner_id:
            return
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.answer(
                "⚠️ Укажите слово для удаления:\n`/delword ищу подрядчика`",
                parse_mode="Markdown"
            )
            return

        word = args[1].strip()
        deleted = await db.delete_keyword(word)
        if deleted:
            await message.answer(f"🗑 Удалено: `{word}`", parse_mode="Markdown")
        else:
            await message.answer(f"❌ Слово `{word}` не найдено.", parse_mode="Markdown")

    # ─── CHATS ─────────────────────────────────────────────────────────────────

    @dp.message(Command("chats"))
    async def cmd_chats(message: Message):
        if message.from_user.id != owner_id:
            return
        chats = await db.get_chats()
        if not chats:
            await message.answer(
                "📭 Чатов нет.\n"
                "Добавьте: `/addchat @username`",
                parse_mode="Markdown"
            )
            return

        lines = []
        for c in chats:
            title = c['chat_title'] or 'Без названия'
            username = f"@{c['chat_username']}" if c['chat_username'] else c['chat_id']
            lines.append(f"• *{title}* ({username})")

        chats_text = "\n".join(lines)
        await message.answer(
            f"💬 *Чаты для мониторинга ({len(chats)}):*\n\n{chats_text}",
            parse_mode="Markdown"
        )

    @dp.message(Command("addchat"))
    async def cmd_addchat(message: Message):
        if message.from_user.id != owner_id:
            return
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.answer(
                "⚠️ Укажите username или ссылку:\n"
                "`/addchat @mychat`\n"
                "`/addchat https://t.me/mychat`",
                parse_mode="Markdown"
            )
            return

        chat_identifier = args[1].strip()
        await message.answer(f"⏳ Добавляю чат `{chat_identifier}`...", parse_mode="Markdown")

        result = await monitor.join_chat(chat_identifier)

        if result['success']:
            if result['added']:
                title = result['title']
                await message.answer(
                    f"✅ Чат добавлен!\n"
                    f"📌 *{title}*\n"
                    f"ID: `{result['chat_id']}`",
                    parse_mode="Markdown"
                )
            else:
                await message.answer("ℹ️ Этот чат уже в списке мониторинга.")
        else:
            await message.answer(
                f"❌ Не удалось добавить чат.\n"
                f"Причина: `{result['error']}`\n\n"
                f"💡 Убедитесь что чат публичный или userbot уже состоит в нём.",
                parse_mode="Markdown"
            )

    @dp.message(Command("delchat"))
    async def cmd_delchat(message: Message):
        if message.from_user.id != owner_id:
            return
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.answer(
                "⚠️ Укажите username или ID чата:\n`/delchat @mychat`",
                parse_mode="Markdown"
            )
            return

        identifier = args[1].strip().lstrip('@')
        deleted = await db.delete_chat(identifier)

        # Пробуем также по полному username с @
        if not deleted:
            deleted = await db.delete_chat(f"@{identifier}")

        if deleted:
            await message.answer(f"🗑 Чат `{identifier}` удалён из мониторинга.", parse_mode="Markdown")
        else:
            await message.answer(
                f"❌ Чат не найден. Используйте `/chats` для просмотра списка.",
                parse_mode="Markdown"
            )

    # ─── /status ───────────────────────────────────────────────────────────────

    @dp.message(Command("status"))
    async def cmd_status(message: Message):
        if message.from_user.id != owner_id:
            return
        stats = await db.get_stats()
        await message.answer(
            "📊 *Статус мониторинга:*\n\n"
            f"🟢 Бот работает\n"
            f"🔑 Ключевых слов: *{stats['keywords_count']}*\n"
            f"💬 Чатов: *{stats['chats_count']}*\n\n"
            f"📈 *Статистика совпадений:*\n"
            f"• Сегодня: *{stats['today_matches']}*\n"
            f"• Всего: *{stats['total_matches']}*",
            parse_mode="Markdown"
        )
