"""Registration check middleware for the main bot."""

from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject

from core.storage import BaseStorage

logger = logging.getLogger(__name__)

# Handlers that do NOT require registration
EXEMPT_COMMANDS = {"/start"}


class RegistrationMiddleware(BaseMiddleware):
    """Block unregistered users from accessing the bot (except /start)."""

    def __init__(self, storage: BaseStorage) -> None:
        self._storage = storage
        super().__init__()

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        # Determine telegram_id and whether to exempt
        telegram_id: int | None = None
        is_exempt = False

        if isinstance(event, Message):
            telegram_id = event.from_user.id if event.from_user else None
            if event.text and any(event.text.startswith(cmd) for cmd in EXEMPT_COMMANDS):
                is_exempt = True
            # Also allow contact messages (used during registration)
            if event.contact is not None:
                is_exempt = True

        elif isinstance(event, CallbackQuery):
            telegram_id = event.from_user.id if event.from_user else None

        if telegram_id is None:
            return await handler(event, data)

        if not is_exempt:
            try:
                user = await self._storage.get_user(telegram_id)
                if user is None:
                    # Not registered — prompt to start
                    if isinstance(event, Message):
                        await event.answer(
                            "Вы ещё не зарегистрированы. Пожалуйста, отправьте /start для регистрации."
                        )
                    elif isinstance(event, CallbackQuery):
                        await event.answer(
                            "Вы ещё не зарегистрированы. Отправьте /start.", show_alert=True
                        )
                    return None

                if user.is_blocked:
                    if isinstance(event, Message):
                        await event.answer("Ваш аккаунт заблокирован. Обратитесь в поддержку.")
                    elif isinstance(event, CallbackQuery):
                        await event.answer("Ваш аккаунт заблокирован.", show_alert=True)
                    return None

                # Inject user into handler data
                data["user"] = user
            except Exception:
                logger.exception("Ошибка в RegistrationMiddleware")

        # Inject storage into all handlers
        data["storage_backend"] = self._storage
        return await handler(event, data)
