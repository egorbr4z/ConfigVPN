"""My account handler."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from aiogram import F, Router
from aiogram.types import CallbackQuery

from core.models import Subscription, User
from core.storage import BaseStorage
from main_bot.keyboards.inline import (
    kb_account,
    kb_account_configs_back,
    kb_account_subscriptions,
)

logger = logging.getLogger(__name__)
router = Router(name="account")


def _format_subscription(sub: Subscription) -> str:
    type_label = "🔒 Белый список" if sub.type == "whitelist" else "💰 Обычный VPN"
    kind_label = "Готовая" if sub.kind == "ready" else "Собственный сервер"
    status = "✅ Активна" if sub.is_active else "❌ Неактивна"

    expires = "—"
    if sub.expires_at:
        try:
            dt = datetime.fromisoformat(sub.expires_at.replace("Z", "+00:00"))
            expires = dt.strftime("%d.%m.%Y")
        except ValueError:
            expires = sub.expires_at

    total_gb = sub.traffic_gb
    used_gb = sub.used_gb
    remaining_gb = max(0.0, total_gb - used_gb)

    return (
        f"*{type_label}* ({kind_label})\n"
        f"Статус: {status}\n"
        f"Истекает: {expires}\n"
        f"Трафик: {used_gb:.1f} / {total_gb:.1f} ГБ (остаток: {remaining_gb:.1f} ГБ)"
    )


@router.callback_query(F.data == "menu:account")
async def cb_account(callback: CallbackQuery, storage_backend: BaseStorage, user: User) -> None:
    try:
        referrals = await storage_backend.get_referrals_by_referrer(user.telegram_id)
        settings = await storage_backend.get_settings()
        bonus_applied_count = sum(1 for r in referrals if r.bonus_applied)

        text = (
            f"👤 *Мой аккаунт*\n\n"
            f"Имя: {user.full_name}\n"
            f"Телефон: {user.phone}\n"
            f"Username: {'@' + user.username if user.username else '—'}\n\n"
            f"🎁 Бонусный трафик: *{user.bonus_gb:.1f} ГБ*\n"
            f"👥 Приглашено друзей: {len(referrals)}\n"
            f"   ├ Получено бонусов за: {bonus_applied_count} чел.\n"
            f"   └ Итого бонусов: {bonus_applied_count * settings.referral_bonus_gb:.0f} ГБ\n\n"
            f"Реферальный код: `{user.referral_code}`"
        )

        await callback.message.edit_text(text, reply_markup=kb_account())
        await callback.answer()
    except Exception:
        logger.exception("Ошибка в cb_account")
        await callback.answer("Произошла ошибка.", show_alert=True)


@router.callback_query(F.data == "account:subscriptions")
async def cb_account_subscriptions(callback: CallbackQuery, storage_backend: BaseStorage, user: User) -> None:
    try:
        all_subs = await storage_backend.get_user_subscriptions(user.telegram_id, active_only=False)
        active_subs = [s for s in all_subs if s.is_active]
        inactive_subs = [s for s in all_subs if not s.is_active]

        has_configs = any(s.subscription_url is not None for s in active_subs)

        if not all_subs:
            text = (
                "📋 *Мои подписки*\n\n"
                "У вас пока нет подписок.\n"
                "Перейдите в раздел «Готовые VPN подписки» или «Собрать свой VPN»."
            )
        else:
            lines = ["📋 *Мои подписки*\n"]

            if active_subs:
                lines.append("*Активные:*")
                for sub in active_subs:
                    lines.append(_format_subscription(sub))
                    lines.append("")

            if inactive_subs:
                lines.append("*Неактивные:*")
                for sub in inactive_subs[:3]:  # Show last 3 inactive
                    lines.append(_format_subscription(sub))
                    lines.append("")

            text = "\n".join(lines).strip()

        await callback.message.edit_text(
            text,
            reply_markup=kb_account_subscriptions(has_configs=has_configs),
        )
        await callback.answer()
    except Exception:
        logger.exception("Ошибка в cb_account_subscriptions")
        await callback.answer("Произошла ошибка.", show_alert=True)


@router.callback_query(F.data == "account:configs")
async def cb_account_configs(callback: CallbackQuery, storage_backend: BaseStorage, user: User) -> None:
    try:
        active_subs = await storage_backend.get_user_subscriptions(user.telegram_id, active_only=True)
        configs_subs = [s for s in active_subs if s.subscription_url is not None]

        if not configs_subs:
            await callback.message.edit_text(
                "🔗 *Мои подписки*\n\nСсылки на подписки пока недоступны.",
                reply_markup=kb_account_configs_back(),
            )
            await callback.answer()
            return

        lines = ["🔗 *Ссылки на подписки*\n"]
        for sub in configs_subs:
            type_label = "🔒 Белый список" if sub.type == "whitelist" else "💰 Обычный VPN"
            lines.append(f"*{type_label}:*")
            lines.append(f"`{sub.subscription_url}`")
            lines.append("")

        lines.append(
            "_Добавьте ссылку в VPN-клиент: Hiddify, Nekobox (Android), "
            "Shadowrocket, Streisand (iOS), Hiddify (Windows/Mac)._"
        )

        await callback.message.edit_text(
            "\n".join(lines),
            reply_markup=kb_account_configs_back(),
        )
        await callback.answer()
    except Exception:
        logger.exception("Ошибка в cb_account_configs")
        await callback.answer("Произошла ошибка.", show_alert=True)
