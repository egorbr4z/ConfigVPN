"""Referral program handler."""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery

import config
from core.models import User
from core.storage import BaseStorage
from main_bot.keyboards.inline import kb_referral_back

logger = logging.getLogger(__name__)
router = Router(name="referral")


@router.callback_query(F.data == "menu:referral")
async def cb_referral(callback: CallbackQuery, storage_backend: BaseStorage, user: User) -> None:
    try:
        settings = await storage_backend.get_settings()
        bot_username = config.BOT_USERNAME or settings.bot_username or "YourVPNBot"

        referral_link = f"https://t.me/{bot_username}?start={user.referral_code}"

        referrals = await storage_backend.get_referrals_by_referrer(user.telegram_id)
        total_invited = len(referrals)
        bonus_applied = sum(1 for r in referrals if r.bonus_applied)
        bonus_gb = bonus_applied * settings.referral_bonus_gb

        text = (
            f"👥 *Реферальная программа*\n\n"
            f"Приглашайте друзей и получайте бонусы!\n\n"
            f"🔗 *Ваша реферальная ссылка:*\n"
            f"`{referral_link}`\n\n"
            f"📊 *Статистика:*\n"
            f"• Приглашено: {total_invited} чел.\n"
            f"• Бонус получен за: {bonus_applied} чел.\n"
            f"• Бонусный трафик: {bonus_gb:.0f} ГБ\n\n"
            f"🎁 *Условия:*\n"
            f"За каждого приглашённого, совершившего первую покупку, "
            f"вы получаете *+{settings.referral_bonus_gb:.0f} ГБ трафика*.\n\n"
            f"Поделитесь ссылкой с друзьями — и ваш интернет станет быстрее!"
        )

        await callback.message.edit_text(text, reply_markup=kb_referral_back())
        await callback.answer()
    except Exception:
        logger.exception("Ошибка в cb_referral")
        await callback.answer("Произошла ошибка.", show_alert=True)
