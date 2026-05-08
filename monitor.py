"""
Монитор — слушает сообщения из добавленных чатов,
проверяет ключевые слова и отправляет уведомления.
"""

import logging
import re
from telethon import TelegramClient, events
from telethon.tl.types import User, Channel, Chat
from aiogram import Bot

from database import Database

logger = logging.getLogger(__name__)


class Monitor:
    def __init__(self, userbot: TelegramClient, bot: Bot, db: Database, owner_id: int):
        self.userbot = userbot
        self.bot = bot
        self.db = db
        self.owner_id = owner_id
        self._handler = None

    async def start(self):
        """Запустить мониторинг"""
        await self._register_handler()
        logger.info("✅ Мониторинг запущен")

    async def _register_handler(self):
        """Регистрируем обработчик новых сообщений"""
        # Удаляем старый хендлер если есть
        if self._handler:
            self.userbot.remove_event_handler(self._handler)

        @self.userbot.on(events.NewMessage)
        async def handler(event):
            await self._on_message(event)

        self._handler = handler

    async def _on_message(self, event):
        """Обработка каждого нового сообщения"""
        try:
            if not event.message or not event.message.text:
                return

            # Проверяем что чат в нашем списке
            chat_ids = await self.db.get_chat_ids()
            if not chat_ids:
                return

            chat = await event.get_chat()
            current_chat_id = str(event.chat_id)

            # Проверяем по ID и по username
            chat_username = getattr(chat, 'username', None)
            is_monitored = (
                current_chat_id in chat_ids or
                f"-100{abs(event.chat_id)}" in chat_ids or
                (chat_username and f"@{chat_username}" in chat_ids) or
                (chat_username and chat_username in chat_ids)
            )

            if not is_monitored:
                return

            message_text = event.message.text
            keywords = await self.db.get_keywords()

            if not keywords:
                return

            # Ищем ключевые слова (без учёта регистра, целые слова/вхождения)
            found_keywords = []
            text_lower = message_text.lower()
            for keyword in keywords:
                if keyword in text_lower:
                    found_keywords.append(keyword)

            if not found_keywords:
                return

            # Получаем инфо об отправителе
            sender = await event.get_sender()
            sender_name, sender_username, sender_contact = self._get_sender_info(sender)

            # Название чата
            chat_title = getattr(chat, 'title', None) or getattr(chat, 'first_name', 'Неизвестно')

            # Ссылка на сообщение
            message_link = self._build_message_link(chat, event.message.id)

            # Сохраняем в БД
            match_data = {
                'chat_id': current_chat_id,
                'chat_title': chat_title,
                'message_id': event.message.id,
                'sender_name': sender_name,
                'sender_username': sender_username,
                'keyword': ', '.join(found_keywords),
                'message_text': message_text[:4000],
                'message_link': message_link,
            }
            await self.db.save_match(match_data)

            # Отправляем уведомление
            await self._send_notification(match_data, found_keywords, sender_contact)

        except Exception as e:
            logger.error(f"Ошибка при обработке сообщения: {e}")

    def _get_sender_info(self, sender) -> tuple[str, str, str]:
        """Извлечь имя, username и контакт отправителя"""
        if sender is None:
            return "Аноним", None, "Аноним"

        if isinstance(sender, User):
            first = sender.first_name or ""
            last = sender.last_name or ""
            name = f"{first} {last}".strip() or "Без имени"
            username = sender.username

            if username:
                contact = f"@{username}"
            elif sender.phone:
                contact = f"+{sender.phone}"
            else:
                contact = f"[ID: {sender.id}](tg://user?id={sender.id})"

            return name, username, contact

        elif isinstance(sender, (Channel, Chat)):
            title = getattr(sender, 'title', 'Канал')
            username = getattr(sender, 'username', None)
            contact = f"@{username}" if username else title
            return title, username, contact

        return "Неизвестно", None, "Неизвестно"

    def _build_message_link(self, chat, message_id: int) -> str:
        """Построить ссылку на сообщение"""
        username = getattr(chat, 'username', None)
        if username:
            return f"https://t.me/{username}/{message_id}"

        chat_id = getattr(chat, 'id', None)
        if chat_id:
            # Для приватных чатов/каналов
            clean_id = str(chat_id).lstrip('-')
            return f"https://t.me/c/{clean_id}/{message_id}"

        return "Ссылка недоступна"

    async def _send_notification(self, data: dict, keywords: list, sender_contact: str):
        """Отправить уведомление владельцу бота"""
        keywords_str = " | ".join([f"`{k}`" for k in keywords])
        text_preview = data['message_text']
        if len(text_preview) > 1000:
            text_preview = text_preview[:1000] + "..."

        message = (
            f"🔔 *Найдено совпадение!*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🔑 *Ключевые слова:* {keywords_str}\n"
            f"💬 *Чат:* {data['chat_title']}\n"
            f"👤 *Автор:* {sender_contact}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📝 *Сообщение:*\n{text_preview}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🔗 [Перейти к сообщению]({data['message_link']})"
        )

        await self.bot.send_message(
            self.owner_id,
            message,
            parse_mode="Markdown",
            disable_web_page_preview=True
        )
        logger.info(f"✅ Уведомление отправлено: {keywords} в {data['chat_title']}")

    async def join_chat(self, chat_identifier: str) -> dict:
        """
        Вступить в чат/канал и добавить в мониторинг.
        chat_identifier — username (@mychat) или ссылка (https://t.me/...)
        """
        try:
            entity = await self.userbot.get_entity(chat_identifier)
            chat_id = str(entity.id)
            title = getattr(entity, 'title', None) or getattr(entity, 'first_name', 'Неизвестно')
            username = getattr(entity, 'username', None)

            # Пробуем вступить (для каналов/групп)
            try:
                from telethon.tl.functions.channels import JoinChannelRequest
                await self.userbot(JoinChannelRequest(entity))
            except Exception:
                pass  # Уже состоим или не требуется

            added = await self.db.add_chat(chat_id, title, username)
            return {
                'success': True,
                'added': added,
                'chat_id': chat_id,
                'title': title,
                'username': username
            }
        except Exception as e:
            logger.error(f"Ошибка при добавлении чата {chat_identifier}: {e}")
            return {'success': False, 'error': str(e)}
