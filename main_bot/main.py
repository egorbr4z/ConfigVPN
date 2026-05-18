"""Main bot setup and startup."""

from __future__ import annotations

import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

import config
from core.storage import JSONStorage
from main_bot.handlers import start, subscriptions, custom_vpn, referral, payment, account, faq
from main_bot.middlewares.auth import RegistrationMiddleware

logger = logging.getLogger(__name__)


async def main() -> None:
    bot = Bot(
        token=config.MAIN_BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
    )
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    json_storage = JSONStorage(config.DATA_DIR)

    # Attach storage to dispatcher workflow data
    dp["storage_backend"] = json_storage

    # Register middleware
    dp.message.middleware(RegistrationMiddleware(json_storage))
    dp.callback_query.middleware(RegistrationMiddleware(json_storage))

    # Register routers
    dp.include_router(start.router)
    dp.include_router(subscriptions.router)
    dp.include_router(custom_vpn.router)
    dp.include_router(referral.router)
    dp.include_router(payment.router)
    dp.include_router(account.router)
    dp.include_router(faq.router)

    logger.info("Запуск основного бота...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)
