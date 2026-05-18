"""FAQ handler."""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery

from core.storage import BaseStorage
from main_bot.keyboards.inline import kb_faq_back

logger = logging.getLogger(__name__)
router = Router(name="faq")


@router.callback_query(F.data == "menu:faq")
async def cb_faq(callback: CallbackQuery, storage_backend: BaseStorage) -> None:
    try:
        settings = await storage_backend.get_settings()
        faq_text = settings.faq_text or "FAQ не настроен."

        await callback.message.edit_text(faq_text, reply_markup=kb_faq_back())
        await callback.answer()
    except Exception:
        logger.exception("Ошибка в cb_faq")
        await callback.answer("Произошла ошибка.", show_alert=True)
