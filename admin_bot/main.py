"""Admin bot setup and startup."""

from __future__ import annotations

import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

import config
from core.storage import JSONStorage
from admin_bot.handlers import (
    dashboard,
    users,
    subscriptions,
    providers,
    payments,
    requisites,
)

logger = logging.getLogger(__name__)


async def main() -> None:
    bot = Bot(
        token=config.ADMIN_BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
    )
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    json_storage = JSONStorage(config.DATA_DIR)
    dp["storage_backend"] = json_storage

    # Register routers
    dp.include_router(dashboard.router)
    dp.include_router(users.router)
    dp.include_router(subscriptions.router)
    dp.include_router(providers.router)
    dp.include_router(payments.router)
    dp.include_router(requisites.router)

    logger.info("Запуск админ-бота...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)
