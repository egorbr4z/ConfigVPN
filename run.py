"""Запуск основного бота и админ-бота одновременно."""

import asyncio
import logging

from main_bot.main import main as main_bot
from admin_bot.main import main as admin_bot


async def run_all() -> None:
    await asyncio.gather(
        main_bot(),
        admin_bot(),
    )


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    asyncio.run(run_all())
