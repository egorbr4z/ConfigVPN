"""Payment approval/rejection for admin bot."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from core.models import Payment, Subscription
from core.storage import BaseStorage

logger = logging.getLogger(__name__)
router = Router(name="admin_payments")

PAGE_SIZE = 8


class PaymentRejectState(StatesGroup):
    entering_reason = State()


class PaymentConfirmState(StatesGroup):
    entering_url = State()


def kb_payments_list(payments: list[Payment], page: int, total_pages: int, status: str) -> object:
    builder = InlineKeyboardBuilder()
    for p in payments:
        status_emoji = {"pending": "⏳", "confirmed": "✅", "rejected": "❌"}.get(p.status, "❓")
        builder.button(
            text=f"{status_emoji} {p.amount:.0f} ₽ — {p.created_at[:10]} (ID:{p.id[:6]})",
            callback_data=f"adm_pay:view:{p.id}",
        )
    builder.adjust(1)

    if page > 0:
        builder.button(text="⬅️", callback_data=f"adm_pay:page:{page - 1}:{status}")
    builder.button(text=f"{page + 1}/{total_pages}", callback_data="noop")
    if page < total_pages - 1:
        builder.button(text="➡️", callback_data=f"adm_pay:page:{page + 1}:{status}")

    builder.button(text="⏳ Ожидающие", callback_data="adm_pay:filter:pending")
    builder.button(text="✅ Подтверждённые", callback_data="adm_pay:filter:confirmed")
    builder.button(text="❌ Отклонённые", callback_data="adm_pay:filter:rejected")
    builder.button(text="◀️ Назад", callback_data="adm:main")
    builder.adjust(1, 3 if total_pages > 1 else 1, 3, 1)
    return builder.as_markup()


def kb_payment_detail(payment: Payment) -> object:
    builder = InlineKeyboardBuilder()
    if payment.status == "pending":
        builder.button(text="✅ Подтвердить", callback_data=f"adm_pay:confirm:{payment.id}")
        builder.button(text="❌ Отклонить", callback_data=f"adm_pay:reject:{payment.id}")
    builder.button(text="◀️ К списку платежей", callback_data="adm:payments")
    builder.adjust(2 if payment.status == "pending" else 1, 1)
    return builder.as_markup()


@router.callback_query(F.data == "adm:payments")
async def cb_payments(callback: CallbackQuery, storage_backend: BaseStorage) -> None:
    try:
        await _show_payments(callback, storage_backend, page=0, status="pending")
    except Exception:
        logger.exception("Ошибка в cb_payments")
        await callback.answer("Произошла ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("adm_pay:filter:"))
async def cb_pay_filter(callback: CallbackQuery, storage_backend: BaseStorage) -> None:
    try:
        status = callback.data.split(":")[2]
        await _show_payments(callback, storage_backend, page=0, status=status)
    except Exception:
        logger.exception("Ошибка в cb_pay_filter")
        await callback.answer("Произошла ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("adm_pay:page:"))
async def cb_pay_page(callback: CallbackQuery, storage_backend: BaseStorage) -> None:
    try:
        parts = callback.data.split(":")
        page = int(parts[2])
        status = parts[3] if len(parts) > 3 else "pending"
        await _show_payments(callback, storage_backend, page=page, status=status)
    except Exception:
        logger.exception("Ошибка в cb_pay_page")
        await callback.answer("Произошла ошибка.", show_alert=True)


async def _show_payments(callback: CallbackQuery, storage_backend: BaseStorage, page: int, status: str) -> None:
    all_payments = await storage_backend.get_payments(status=status)
    all_payments.sort(key=lambda p: p.created_at, reverse=True)
    total = len(all_payments)
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(0, min(page, total_pages - 1))
    slice_ = all_payments[page * PAGE_SIZE: (page + 1) * PAGE_SIZE]

    status_labels = {"pending": "⏳ Ожидающие", "confirmed": "✅ Подтверждённые", "rejected": "❌ Отклонённые"}
    label = status_labels.get(status, status)

    text = f"💳 *Платежи — {label}* (всего: {total})\nСтраница {page + 1}/{total_pages}:"
    await callback.message.edit_text(text, reply_markup=kb_payments_list(slice_, page, total_pages, status))
    await callback.answer()


@router.callback_query(F.data.startswith("adm_pay:view:"))
async def cb_payment_view(callback: CallbackQuery, storage_backend: BaseStorage) -> None:
    try:
        pay_id = callback.data.split(":")[2]
        payment = await storage_backend.get_payment(pay_id)
        if payment is None:
            await callback.answer("Платёж не найден.", show_alert=True)
            return

        user = await storage_backend.get_user(payment.user_id)
        user_info = (
            f"@{user.username}" if (user and user.username)
            else (user.full_name if user else str(payment.user_id))
        )
        phone = user.phone if user else "—"

        req = await storage_backend.get_requisite(payment.requisite_id)
        req_info = f"{req.type}: {req.value} ({req.holder_name})" if req else "—"

        status_labels = {"pending": "⏳ Ожидает", "confirmed": "✅ Подтверждён", "rejected": "❌ Отклонён"}
        status_text = status_labels.get(payment.status, payment.status)

        product_label = payment.product_details.get(
            "plan_name",
            f"Пресет {payment.product_details.get('preset_id', '—')}"
        )

        text = (
            f"💳 *Платёж*\n\n"
            f"ID: `{payment.id}`\n"
            f"Пользователь: {user_info} (ID: `{payment.user_id}`)\n"
            f"Телефон: {phone}\n"
            f"Продукт: {product_label}\n"
            f"Сумма: *{payment.amount:.0f} ₽*\n"
            f"Реквизиты: {req_info}\n"
            f"Последние 4 цифры: `{payment.last4 or '—'}`\n"
            f"Статус: {status_text}\n"
            f"Создан: {payment.created_at[:19].replace('T', ' ')}"
        )

        if payment.reviewed_at:
            text += f"\nПроверен: {payment.reviewed_at[:19].replace('T', ' ')}"

        await callback.message.edit_text(text, reply_markup=kb_payment_detail(payment))
        await callback.answer()
    except Exception:
        logger.exception("Ошибка в cb_payment_view")
        await callback.answer("Произошла ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("adm_pay:confirm:"))
async def cb_payment_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    try:
        pay_id = callback.data.split(":")[2]
        await state.set_state(PaymentConfirmState.entering_url)
        await state.update_data(confirm_payment_id=pay_id)

        builder = InlineKeyboardBuilder()
        builder.button(text="◀️ Отмена", callback_data=f"adm_pay:view:{pay_id}")
        await callback.message.edit_text(
            "🔗 Введите ссылку на подписку (https://...), которая будет выдана пользователю:",
            reply_markup=builder.as_markup(),
        )
        await callback.answer()
    except Exception:
        logger.exception("Ошибка в cb_payment_confirm")
        await callback.answer("Произошла ошибка.", show_alert=True)


@router.message(PaymentConfirmState.entering_url)
async def handle_confirm_url(message: Message, state: FSMContext, storage_backend: BaseStorage) -> None:
    try:
        url = (message.text or "").strip()
        data = await state.get_data()
        pay_id: str = data.get("confirm_payment_id", "")
        await state.clear()

        if not url.startswith("http"):
            builder = InlineKeyboardBuilder()
            builder.button(text="◀️ Отмена", callback_data=f"adm_pay:view:{pay_id}")
            await message.answer(
                "❌ Некорректная ссылка. Введите URL, начинающийся с https://",
                reply_markup=builder.as_markup(),
            )
            return

        payment = await storage_backend.get_payment(pay_id)
        if payment is None:
            await message.answer("Платёж не найден.")
            return

        if payment.status != "pending":
            await message.answer("Платёж уже обработан.")
            return

        payment.status = "confirmed"
        payment.reviewed_at = datetime.now(timezone.utc).isoformat()
        payment.reviewed_by = message.from_user.id
        await storage_backend.save_payment(payment)

        subscription = await _create_subscription(payment, storage_backend, subscription_url=url)
        await _apply_referral_bonus_if_needed(payment.user_id, storage_backend)

        try:
            type_label = "🔒 Белый список" if subscription.type == "whitelist" else "💰 Обычный VPN"
            expires_text = ""
            if subscription.expires_at:
                try:
                    dt = datetime.fromisoformat(subscription.expires_at.replace("Z", "+00:00"))
                    expires_text = f"\nДействует до: {dt.strftime('%d.%m.%Y')}"
                except ValueError:
                    pass

            user_text = (
                f"✅ *Ваш платёж подтверждён!*\n\n"
                f"Подписка активирована: {type_label}\n"
                f"Трафик: {subscription.traffic_gb:.0f} ГБ{expires_text}\n\n"
                f"🔗 *Ссылка на подписку:*\n`{url}`\n\n"
                f"Добавьте ссылку в ваш VPN-клиент (Hiddify, Nekobox, Shadowrocket и др.)"
            )
            await message.bot.send_message(payment.user_id, user_text, parse_mode="Markdown")
        except Exception:
            logger.warning("Не удалось уведомить пользователя %s", payment.user_id)

        builder = InlineKeyboardBuilder()
        builder.button(text="💳 К платежам", callback_data="adm:payments")
        await message.answer(
            "✅ Платёж подтверждён, подписка активирована, пользователь уведомлён.",
            reply_markup=builder.as_markup(),
        )
    except Exception:
        logger.exception("Ошибка в handle_confirm_url")
        await message.answer("Произошла ошибка.")
        await state.clear()


async def _create_subscription(
    payment: Payment, storage: BaseStorage, subscription_url: str = ""
) -> Subscription:
    details = payment.product_details
    now = datetime.now(timezone.utc)

    if payment.type == "subscription":
        plan_id = details.get("plan_id", "")
        plan_type = details.get("plan_type", "regular")
        duration_days = details.get("duration_days", 30)
        traffic_gb = details.get("traffic_gb", 100.0)
        expires_at = (now + timedelta(days=duration_days)).isoformat()

        sub = Subscription(
            id=BaseStorage.new_id(),
            user_id=payment.user_id,
            type=plan_type,
            kind="ready",
            plan_id=plan_id,
            provider_ids=[],
            preset_id=None,
            traffic_gb=traffic_gb,
            used_gb=0.0,
            expires_at=expires_at,
            is_active=True,
            subscription_url=subscription_url or None,
        )
    else:
        provider_ids = details.get("provider_ids", [])
        vpn_type = details.get("vpn_type", "regular")
        preset_id = details.get("preset_id")
        traffic_gb = 200.0

        sub = Subscription(
            id=BaseStorage.new_id(),
            user_id=payment.user_id,
            type=vpn_type,
            kind="custom",
            plan_id=None,
            provider_ids=provider_ids,
            preset_id=preset_id,
            traffic_gb=traffic_gb,
            used_gb=0.0,
            expires_at=(now + timedelta(days=30)).isoformat(),
            is_active=True,
            subscription_url=subscription_url or None,
        )

    await storage.save_subscription(sub)
    return sub


async def _apply_referral_bonus_if_needed(user_id: int, storage: BaseStorage) -> None:
    """Apply +bonus_gb to referrer if this is the referred user's first confirmed payment."""
    try:
        # Check if this is the user's first confirmed payment
        all_payments = await storage.get_user_payments(user_id)
        confirmed = [p for p in all_payments if p.status == "confirmed"]
        if len(confirmed) != 1:
            # Either no confirmed payments (shouldn't happen) or more than 1 (already applied)
            return

        # Find referral record
        referral = await storage.get_referral_by_referred(user_id)
        if referral is None or referral.bonus_applied:
            return

        # Get referrer
        referrer = await storage.get_user(referral.referrer_id)
        if referrer is None:
            return

        # Get settings for bonus amount
        settings = await storage.get_settings()
        bonus = settings.referral_bonus_gb

        # Apply bonus
        referrer.bonus_gb += bonus
        await storage.save_user(referrer)

        # Mark referral as applied
        referral.bonus_applied = True
        await storage.save_referral(referral)

        logger.info(
            "Реферальный бонус %.1f ГБ начислен пользователю %s",
            bonus,
            referral.referrer_id,
        )
    except Exception:
        logger.exception("Ошибка при начислении реферального бонуса")


@router.callback_query(F.data.startswith("adm_pay:reject:"))
async def cb_payment_reject_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    try:
        pay_id = callback.data.split(":")[2]
        await state.set_state(PaymentRejectState.entering_reason)
        await state.update_data(reject_payment_id=pay_id)

        builder = InlineKeyboardBuilder()
        builder.button(text="◀️ Отмена", callback_data=f"adm_pay:view:{pay_id}")
        await callback.message.edit_text(
            "Введите причину отклонения платежа (будет отправлена пользователю):",
            reply_markup=builder.as_markup(),
        )
        await callback.answer()
    except Exception:
        logger.exception("Ошибка в cb_payment_reject_prompt")
        await callback.answer("Произошла ошибка.", show_alert=True)


@router.message(PaymentRejectState.entering_reason)
async def handle_reject_reason(message: Message, state: FSMContext, storage_backend: BaseStorage) -> None:
    try:
        reason = (message.text or "").strip()
        data = await state.get_data()
        pay_id: str = data.get("reject_payment_id", "")
        await state.clear()

        payment = await storage_backend.get_payment(pay_id)
        if payment is None:
            await message.answer("Платёж не найден.")
            return

        if payment.status != "pending":
            await message.answer("Платёж уже обработан.")
            return

        payment.status = "rejected"
        payment.reviewed_at = datetime.now(timezone.utc).isoformat()
        payment.reviewed_by = message.from_user.id
        await storage_backend.save_payment(payment)

        # Notify user
        try:
            user_text = (
                f"❌ *Ваш платёж отклонён.*\n\n"
                f"Сумма: {payment.amount:.0f} ₽\n"
                f"Причина: {reason}\n\n"
                f"Если у вас есть вопросы, обратитесь в поддержку."
            )
            await message.bot.send_message(payment.user_id, user_text, parse_mode="Markdown")
        except Exception:
            logger.warning("Не удалось уведомить пользователя %s", payment.user_id)

        builder = InlineKeyboardBuilder()
        builder.button(text="💳 К платежам", callback_data="adm:payments")
        await message.answer("✅ Платёж отклонён, пользователь уведомлён.", reply_markup=builder.as_markup())
    except Exception:
        logger.exception("Ошибка в handle_reject_reason")
        await message.answer("Произошла ошибка.")
        await state.clear()
