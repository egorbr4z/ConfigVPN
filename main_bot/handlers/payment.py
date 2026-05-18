"""Payment flow handler for the main bot."""

from __future__ import annotations

import logging
import random
from datetime import datetime, timezone

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

import config
from core.models import Payment, Preset, Requisite, SubscriptionPlan, User
from core.storage import BaseStorage
from main_bot.keyboards.inline import kb_main_menu, kb_payment_cancel, kb_payment_status

logger = logging.getLogger(__name__)
router = Router(name="payment")


class PaymentState(StatesGroup):
    waiting_for_last4 = State()


def _format_requisite(req: Requisite) -> str:
    type_label = "Карта" if req.type == "card" else "Телефон (СБП)"
    return f"{type_label}: `{req.value}` ({req.holder_name})"


async def _pick_requisite(storage: BaseStorage) -> Requisite | None:
    reqs = await storage.get_requisites(active_only=True)
    return random.choice(reqs) if reqs else None


async def _notify_admins(bot, admin_ids: list[int], text: str) -> None:
    for admin_id in admin_ids:
        try:
            await bot.send_message(admin_id, text, parse_mode="Markdown")
        except Exception:
            logger.warning("Не удалось уведомить администратора %s", admin_id)


async def initiate_payment_for_plan(
    callback: CallbackQuery,
    state: FSMContext,
    storage: BaseStorage,
    user: User,
    plan: SubscriptionPlan,
) -> None:
    """Start payment flow for a ready subscription plan."""
    requisite = await _pick_requisite(storage)
    if requisite is None:
        await callback.message.edit_text(
            "❌ Реквизиты для оплаты временно недоступны. Попробуйте позже.",
            reply_markup=kb_main_menu(),
        )
        await callback.answer()
        return

    payment = Payment(
        id=BaseStorage.new_id(),
        user_id=user.telegram_id,
        amount=plan.price,
        type="subscription",
        product_ref=plan.id,
        product_details={
            "plan_id": plan.id,
            "plan_name": plan.name,
            "plan_type": plan.type,
            "duration_days": plan.duration_days,
            "traffic_gb": plan.traffic_gb,
        },
        requisite_id=requisite.id,
        last4=None,
        status="pending",
        created_at=datetime.now(timezone.utc).isoformat(),
        reviewed_at=None,
        reviewed_by=None,
    )
    await storage.save_payment(payment)

    await state.set_state(PaymentState.waiting_for_last4)
    await state.update_data(payment_id=payment.id)

    await callback.message.edit_text(
        f"💳 *Оплата подписки*\n\n"
        f"Тариф: *{plan.name}*\n"
        f"Сумма: *{plan.price:.0f} ₽*\n\n"
        f"Переведите указанную сумму на:\n{_format_requisite(requisite)}\n\n"
        f"После оплаты введите *последние 4 цифры* номера карты или телефона, "
        f"с которого выполнен перевод:\n\n"
        f"_(Для отмены нажмите кнопку ниже)_",
        reply_markup=kb_payment_cancel(),
    )
    await callback.answer()


async def initiate_payment_for_custom_vpn(
    callback: CallbackQuery,
    storage: BaseStorage,
    user: User,
    preset: Preset,
    provider_ids: list[str],
    vpn_type: str,
    state: FSMContext,
) -> None:
    """Start payment flow for custom VPN server."""
    requisite = await _pick_requisite(storage)
    if requisite is None:
        await callback.message.edit_text(
            "❌ Реквизиты для оплаты временно недоступны. Попробуйте позже.",
            reply_markup=kb_main_menu(),
        )
        await callback.answer()
        return

    total_amount = preset.price * len(provider_ids)

    provider_names = []
    for pid in provider_ids:
        prov = await storage.get_provider(pid)
        if prov:
            provider_names.append(f"{prov.name} ({prov.location})")

    payment = Payment(
        id=BaseStorage.new_id(),
        user_id=user.telegram_id,
        amount=total_amount,
        type="custom_vpn",
        product_ref=preset.id,
        product_details={
            "preset_id": preset.id,
            "provider_ids": provider_ids,
            "provider_names": provider_names,
            "vpn_type": vpn_type,
            "ram_gb": preset.ram_gb,
            "cpu_count": preset.cpu_count,
            "price_per_server": preset.price,
        },
        requisite_id=requisite.id,
        last4=None,
        status="pending",
        created_at=datetime.now(timezone.utc).isoformat(),
        reviewed_at=None,
        reviewed_by=None,
    )
    await storage.save_payment(payment)

    providers_text = "\n".join(f"• {n}" for n in provider_names) if provider_names else "—"

    await state.set_state(PaymentState.waiting_for_last4)
    await state.update_data(payment_id=payment.id)

    await callback.message.edit_text(
        f"💳 *Оплата VPN сервера*\n\n"
        f"Провайдеры:\n{providers_text}\n"
        f"Конфигурация: RAM {preset.ram_gb} ГБ / CPU {preset.cpu_count}\n"
        f"Сумма: *{total_amount:.0f} ₽/мес*\n\n"
        f"Переведите указанную сумму на:\n{_format_requisite(requisite)}\n\n"
        f"После оплаты введите *последние 4 цифры* номера карты или телефона, "
        f"с которого выполнен перевод:\n\n"
        f"_(Для отмены нажмите кнопку ниже)_",
        reply_markup=kb_payment_cancel(),
    )
    await callback.answer()


@router.message(PaymentState.waiting_for_last4)
async def handle_last4_input(message: Message, state: FSMContext, storage_backend: BaseStorage) -> None:
    try:
        text = (message.text or "").strip()

        if not text.isdigit() or len(text) != 4:
            await message.answer(
                "❌ Неверный формат. Введите ровно *4 цифры* — "
                "последние 4 цифры номера карты или телефона, с которого вы переводили."
            )
            return

        fsm_data = await state.get_data()
        payment_id: str | None = fsm_data.get("payment_id")

        if not payment_id:
            await message.answer(
                "Не удалось найти ваш платёж. Пожалуйста, начните процесс оплаты заново.",
                reply_markup=kb_main_menu(),
            )
            await state.clear()
            return

        payment = await storage_backend.get_payment(payment_id)
        if payment is None:
            await message.answer(
                "Платёж не найден. Попробуйте ещё раз.",
                reply_markup=kb_main_menu(),
            )
            await state.clear()
            return

        payment.last4 = text
        await storage_backend.save_payment(payment)
        await state.clear()

        # Notify admins
        settings = await storage_backend.get_settings()
        if settings.notifications.get("notify_admins_on_payment"):
            user = await storage_backend.get_user(payment.user_id)
            user_info = (
                f"@{user.username}" if (user and user.username) else
                (user.full_name if user else str(payment.user_id))
            )
            phone = user.phone if user else "—"
            product_label = payment.product_details.get(
                "plan_name",
                f"Пресет {payment.product_details.get('preset_id', '—')}"
            )
            admin_text = (
                f"💰 *Новый платёж на подтверждение*\n\n"
                f"Пользователь: {user_info} (ID: `{payment.user_id}`)\n"
                f"Телефон: {phone}\n"
                f"Продукт: {product_label}\n"
                f"Сумма: {payment.amount:.0f} ₽\n"
                f"Последние 4 цифры: `{text}`\n"
                f"ID платежа: `{payment.id}`\n\n"
                f"Перейдите в AdminBot → раздел Платежи для подтверждения."
            )
            admin_ids = config.ADMIN_IDS or settings.admin_ids
            await _notify_admins(message.bot, admin_ids, admin_text)

        await message.answer(
            "✅ *Данные об оплате приняты!*\n\n"
            "Ваш платёж отправлен на проверку администратору.\n"
            "Мы уведомим вас сразу после подтверждения.\n\n"
            "Обычно проверка занимает не более 30 минут.",
            reply_markup=kb_payment_status(),
        )
    except Exception:
        logger.exception("Ошибка в handle_last4_input")
        await message.answer(
            "Произошла ошибка. Попробуйте ещё раз или обратитесь в поддержку.",
            reply_markup=kb_main_menu(),
        )
        await state.clear()


@router.callback_query(F.data == "payment:cancel")
async def cb_payment_cancel(callback: CallbackQuery, state: FSMContext, storage_backend: BaseStorage) -> None:
    try:
        fsm_data = await state.get_data()
        payment_id: str | None = fsm_data.get("payment_id")

        if payment_id:
            payment = await storage_backend.get_payment(payment_id)
            if payment and payment.status == "pending" and payment.last4 is None:
                payment.status = "rejected"
                payment.reviewed_at = datetime.now(timezone.utc).isoformat()
                await storage_backend.save_payment(payment)

        await state.clear()
        await callback.message.edit_text(
            "❌ Оплата отменена.\n\nВы можете вернуться в главное меню.",
            reply_markup=kb_main_menu(),
        )
        await callback.answer()
    except Exception:
        logger.exception("Ошибка в cb_payment_cancel")
        await callback.answer("Произошла ошибка.", show_alert=True)
