"""Ready VPN subscription handlers."""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from core.models import User
from core.storage import BaseStorage
from main_bot.keyboards.inline import (
    kb_plan_detail,
    kb_subscription_plans,
    kb_subscription_tabs,
)

logger = logging.getLogger(__name__)
router = Router(name="subscriptions")


@router.callback_query(F.data == "menu:subscriptions")
async def cb_subscriptions_menu(callback: CallbackQuery) -> None:
    try:
        await callback.message.edit_text(
            "📦 *Готовые VPN подписки*\n\n"
            "Выберите тип подписки:",
            reply_markup=kb_subscription_tabs(),
        )
        await callback.answer()
    except Exception:
        logger.exception("Ошибка в cb_subscriptions_menu")
        await callback.answer("Произошла ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("sub_tab:"))
async def cb_subscription_tab(callback: CallbackQuery, storage_backend: BaseStorage, user: User) -> None:
    try:
        tab = callback.data.split(":")[1]
        vpn_type = "whitelist" if tab == "whitelist" else "regular"
        label = "🔒 Белые списки" if vpn_type == "whitelist" else "💰 Обычный VPN"

        plans = await storage_backend.get_subscription_plans(active_only=True)
        plans = [p for p in plans if p.type == vpn_type]

        # Check if user already has an active subscription of this type
        active_subs = await storage_backend.get_user_subscriptions(user.telegram_id, active_only=True)
        already_has = any(s.type == vpn_type for s in active_subs)

        warning = ""
        if already_has:
            warning = (
                "\n\n⚠️ *У вас уже есть активная подписка этого типа.*\n"
                "Приобрести новую можно только после истечения текущей."
            )

        if not plans:
            await callback.message.edit_text(
                f"{label}\n\nПланы в этой категории временно недоступны.{warning}",
                reply_markup=kb_subscription_tabs(),
            )
            await callback.answer()
            return

        await callback.message.edit_text(
            f"{label}\n\nВыберите план подписки:{warning}",
            reply_markup=kb_subscription_plans(plans),
        )
        await callback.answer()
    except Exception:
        logger.exception("Ошибка в cb_subscription_tab")
        await callback.answer("Произошла ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("sub_plan:"))
async def cb_subscription_plan(callback: CallbackQuery, storage_backend: BaseStorage, user: User) -> None:
    try:
        plan_id = callback.data.split(":", 1)[1]
        plan = await storage_backend.get_subscription_plan(plan_id)

        if plan is None or not plan.is_active:
            await callback.answer("Этот план недоступен.", show_alert=True)
            return

        # Check subscription limit
        active_subs = await storage_backend.get_user_subscriptions(user.telegram_id, active_only=True)
        already_has = any(s.type == plan.type for s in active_subs)

        type_label = "белый список" if plan.type == "whitelist" else "обычный VPN"
        duration_label = f"{plan.duration_days} дн." if plan.duration_days != 30 else "1 месяц"
        if plan.duration_days == 90:
            duration_label = "3 месяца"

        traffic_month = "♾ Безлимит" if plan.monthly_traffic_gb == 0 else f"{plan.monthly_traffic_gb:.0f} ГБ"
        connections = f"{plan.max_connections} уст." if plan.max_connections == 1 else f"{plan.max_connections} уст. одновременно"

        text = (
            f"📋 *{plan.name}*\n\n"
            f"Тип: {type_label}\n"
            f"Срок: {duration_label}\n"
            f"Трафик в месяц: {traffic_month}\n"
            f"Подключений: {connections}\n"
            f"Цена: *{plan.price:.0f} ₽*\n\n"
            f"{plan.description}"
        )

        if already_has:
            text += (
                "\n\n⚠️ *У вас уже есть активная подписка этого типа.*\n"
                "Вы не можете приобрести новую до её истечения."
            )

        await callback.message.edit_text(text, reply_markup=kb_plan_detail(plan_id))
        await callback.answer()
    except Exception:
        logger.exception("Ошибка в cb_subscription_plan")
        await callback.answer("Произошла ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("sub_buy:"))
async def cb_subscription_buy(
    callback: CallbackQuery,
    state: FSMContext,
    storage_backend: BaseStorage,
    user: User,
) -> None:
    """Redirect to payment flow for a ready subscription."""
    try:
        plan_id = callback.data.split(":", 1)[1]
        plan = await storage_backend.get_subscription_plan(plan_id)

        if plan is None or not plan.is_active:
            await callback.answer("Этот план недоступен.", show_alert=True)
            return

        # Check subscription limit
        active_subs = await storage_backend.get_user_subscriptions(user.telegram_id, active_only=True)
        already_has = any(s.type == plan.type for s in active_subs)
        if already_has:
            await callback.answer(
                "У вас уже есть активная подписка этого типа.",
                show_alert=True,
            )
            return

        from main_bot.handlers.payment import initiate_payment_for_plan
        await initiate_payment_for_plan(callback, state, storage_backend, user, plan)
    except Exception:
        logger.exception("Ошибка в cb_subscription_buy")
        await callback.answer("Произошла ошибка.", show_alert=True)
