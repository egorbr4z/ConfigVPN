"""Subscription plans management for admin bot."""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from core.models import SubscriptionPlan
from core.storage import BaseStorage

logger = logging.getLogger(__name__)
router = Router(name="admin_subscriptions")


class PlanEditState(StatesGroup):
    entering_name = State()
    entering_type = State()
    entering_price = State()
    entering_duration = State()
    entering_traffic = State()
    entering_description = State()
    # Edit existing
    editing_field = State()


def kb_plans_list(plans: list[SubscriptionPlan]) -> object:
    builder = InlineKeyboardBuilder()
    for plan in plans:
        status = "✅" if plan.is_active else "❌"
        builder.button(
            text=f"{status} {plan.name} — {plan.price:.0f} ₽",
            callback_data=f"adm_plan:view:{plan.id}",
        )
    builder.button(text="➕ Добавить тариф", callback_data="adm_plan:add")
    builder.button(text="◀️ Назад", callback_data="adm:main")
    builder.adjust(1)
    return builder.as_markup()


def kb_plan_detail(plan: SubscriptionPlan) -> object:
    builder = InlineKeyboardBuilder()
    toggle_label = "❌ Деактивировать" if plan.is_active else "✅ Активировать"
    builder.button(text="✏️ Изменить цену", callback_data=f"adm_plan:edit_price:{plan.id}")
    builder.button(text="✏️ Изменить название", callback_data=f"adm_plan:edit_name:{plan.id}")
    builder.button(text="✏️ Изменить описание", callback_data=f"adm_plan:edit_desc:{plan.id}")
    builder.button(text=toggle_label, callback_data=f"adm_plan:toggle:{plan.id}")
    builder.button(text="🗑 Удалить", callback_data=f"adm_plan:delete:{plan.id}")
    builder.button(text="◀️ Назад", callback_data="adm:subscriptions")
    builder.adjust(1)
    return builder.as_markup()


@router.callback_query(F.data == "adm:subscriptions")
async def cb_subscriptions(callback: CallbackQuery, storage_backend: BaseStorage) -> None:
    try:
        plans = await storage_backend.get_subscription_plans(active_only=False)
        await callback.message.edit_text(
            f"📦 *Тарифы* (всего: {len(plans)})",
            reply_markup=kb_plans_list(plans),
        )
        await callback.answer()
    except Exception:
        logger.exception("Ошибка в cb_subscriptions")
        await callback.answer("Произошла ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("adm_plan:view:"))
async def cb_plan_view(callback: CallbackQuery, storage_backend: BaseStorage) -> None:
    try:
        plan_id = callback.data.split(":")[2]
        plan = await storage_backend.get_subscription_plan(plan_id)
        if plan is None:
            await callback.answer("Тариф не найден.", show_alert=True)
            return

        type_label = "🔒 Белый список" if plan.type == "whitelist" else "💰 Обычный VPN"
        status = "✅ Активен" if plan.is_active else "❌ Неактивен"

        text = (
            f"📦 *Тариф*\n\n"
            f"Название: {plan.name}\n"
            f"Тип: {type_label}\n"
            f"Цена: *{plan.price:.0f} ₽*\n"
            f"Длительность: {plan.duration_days} дн.\n"
            f"Трафик: {plan.traffic_gb:.0f} ГБ\n"
            f"Статус: {status}\n\n"
            f"Описание: {plan.description}"
        )

        await callback.message.edit_text(text, reply_markup=kb_plan_detail(plan))
        await callback.answer()
    except Exception:
        logger.exception("Ошибка в cb_plan_view")
        await callback.answer("Произошла ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("adm_plan:toggle:"))
async def cb_plan_toggle(callback: CallbackQuery, storage_backend: BaseStorage) -> None:
    try:
        plan_id = callback.data.split(":")[2]
        plan = await storage_backend.get_subscription_plan(plan_id)
        if plan is None:
            await callback.answer("Тариф не найден.", show_alert=True)
            return

        plan.is_active = not plan.is_active
        await storage_backend.save_subscription_plan(plan)
        status = "активирован" if plan.is_active else "деактивирован"
        await callback.answer(f"Тариф {status}.", show_alert=True)
        await cb_plan_view(callback, storage_backend)
    except Exception:
        logger.exception("Ошибка в cb_plan_toggle")
        await callback.answer("Произошла ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("adm_plan:delete:"))
async def cb_plan_delete(callback: CallbackQuery, storage_backend: BaseStorage) -> None:
    try:
        plan_id = callback.data.split(":")[2]
        await storage_backend.delete_subscription_plan(plan_id)
        await callback.answer("✅ Тариф удалён.", show_alert=True)

        plans = await storage_backend.get_subscription_plans(active_only=False)
        await callback.message.edit_text(
            f"📦 *Тарифы* (всего: {len(plans)})",
            reply_markup=kb_plans_list(plans),
        )
    except Exception:
        logger.exception("Ошибка в cb_plan_delete")
        await callback.answer("Произошла ошибка.", show_alert=True)


# ------- Add new plan (multi-step FSM) -------

@router.callback_query(F.data == "adm_plan:add")
async def cb_plan_add(callback: CallbackQuery, state: FSMContext) -> None:
    try:
        await state.set_state(PlanEditState.entering_name)
        await state.update_data(is_new=True)
        builder = InlineKeyboardBuilder()
        builder.button(text="◀️ Отмена", callback_data="adm:subscriptions")
        await callback.message.edit_text(
            "➕ *Новый тариф*\n\nВведите название тарифа:",
            reply_markup=builder.as_markup(),
        )
        await callback.answer()
    except Exception:
        logger.exception("Ошибка в cb_plan_add")
        await callback.answer("Произошла ошибка.", show_alert=True)


@router.message(PlanEditState.entering_name)
async def handle_plan_name(message: Message, state: FSMContext) -> None:
    try:
        name = (message.text or "").strip()
        if not name:
            await message.answer("Название не может быть пустым. Введите название тарифа:")
            return
        await state.update_data(name=name)
        await state.set_state(PlanEditState.entering_type)

        builder = InlineKeyboardBuilder()
        builder.button(text="🔒 Белый список", callback_data="plan_type_choice:whitelist")
        builder.button(text="💰 Обычный VPN", callback_data="plan_type_choice:regular")
        await message.answer("Выберите тип тарифа:", reply_markup=builder.as_markup())
    except Exception:
        logger.exception("Ошибка в handle_plan_name")
        await message.answer("Произошла ошибка.")


@router.callback_query(F.data.startswith("plan_type_choice:"), PlanEditState.entering_type)
async def handle_plan_type(callback: CallbackQuery, state: FSMContext) -> None:
    try:
        vpn_type = callback.data.split(":")[1]
        await state.update_data(vpn_type=vpn_type)
        await state.set_state(PlanEditState.entering_price)
        await callback.message.edit_text("Введите цену тарифа в рублях (например: 299):")
        await callback.answer()
    except Exception:
        logger.exception("Ошибка в handle_plan_type")
        await callback.answer("Произошла ошибка.", show_alert=True)


@router.message(PlanEditState.entering_price)
async def handle_plan_price(message: Message, state: FSMContext) -> None:
    try:
        raw = (message.text or "").strip().replace(",", ".")
        try:
            price = float(raw)
            if price <= 0:
                raise ValueError
        except ValueError:
            await message.answer("Введите корректную цену (положительное число):")
            return
        await state.update_data(price=price)
        await state.set_state(PlanEditState.entering_duration)
        await message.answer("Введите длительность тарифа в днях (например: 30):")
    except Exception:
        logger.exception("Ошибка в handle_plan_price")
        await message.answer("Произошла ошибка.")


@router.message(PlanEditState.entering_duration)
async def handle_plan_duration(message: Message, state: FSMContext) -> None:
    try:
        raw = (message.text or "").strip()
        if not raw.isdigit() or int(raw) <= 0:
            await message.answer("Введите корректное количество дней (целое положительное число):")
            return
        await state.update_data(duration_days=int(raw))
        await state.set_state(PlanEditState.entering_traffic)
        await message.answer("Введите объём трафика в ГБ (например: 100):")
    except Exception:
        logger.exception("Ошибка в handle_plan_duration")
        await message.answer("Произошла ошибка.")


@router.message(PlanEditState.entering_traffic)
async def handle_plan_traffic(message: Message, state: FSMContext) -> None:
    try:
        raw = (message.text or "").strip().replace(",", ".")
        try:
            traffic = float(raw)
            if traffic <= 0:
                raise ValueError
        except ValueError:
            await message.answer("Введите корректный объём трафика:")
            return
        await state.update_data(traffic_gb=traffic)
        await state.set_state(PlanEditState.entering_description)
        await message.answer("Введите описание тарифа:")
    except Exception:
        logger.exception("Ошибка в handle_plan_traffic")
        await message.answer("Произошла ошибка.")


@router.message(PlanEditState.entering_description)
async def handle_plan_description(message: Message, state: FSMContext, storage_backend: BaseStorage) -> None:
    try:
        description = (message.text or "").strip()
        data = await state.get_data()
        await state.clear()

        plan = SubscriptionPlan(
            id=BaseStorage.new_id(),
            name=data["name"],
            type=data["vpn_type"],
            price=data["price"],
            duration_days=data["duration_days"],
            traffic_gb=data["traffic_gb"],
            description=description,
            is_active=True,
        )
        await storage_backend.save_subscription_plan(plan)

        builder = InlineKeyboardBuilder()
        builder.button(text="📋 К тарифам", callback_data="adm:subscriptions")
        await message.answer(
            f"✅ Тариф *{plan.name}* успешно добавлен!",
            reply_markup=builder.as_markup(),
        )
    except Exception:
        logger.exception("Ошибка в handle_plan_description")
        await message.answer("Произошла ошибка.")
        await state.clear()


# ------- Edit existing plan fields -------

@router.callback_query(F.data.startswith("adm_plan:edit_price:"))
async def cb_edit_price(callback: CallbackQuery, state: FSMContext) -> None:
    try:
        plan_id = callback.data.split(":")[2]
        await state.set_state(PlanEditState.editing_field)
        await state.update_data(edit_field="price", edit_plan_id=plan_id)
        builder = InlineKeyboardBuilder()
        builder.button(text="◀️ Отмена", callback_data=f"adm_plan:view:{plan_id}")
        await callback.message.edit_text(
            "Введите новую цену в рублях:",
            reply_markup=builder.as_markup(),
        )
        await callback.answer()
    except Exception:
        logger.exception("Ошибка в cb_edit_price")
        await callback.answer("Произошла ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("adm_plan:edit_name:"))
async def cb_edit_name(callback: CallbackQuery, state: FSMContext) -> None:
    try:
        plan_id = callback.data.split(":")[2]
        await state.set_state(PlanEditState.editing_field)
        await state.update_data(edit_field="name", edit_plan_id=plan_id)
        builder = InlineKeyboardBuilder()
        builder.button(text="◀️ Отмена", callback_data=f"adm_plan:view:{plan_id}")
        await callback.message.edit_text("Введите новое название:", reply_markup=builder.as_markup())
        await callback.answer()
    except Exception:
        logger.exception("Ошибка в cb_edit_name")
        await callback.answer("Произошла ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("adm_plan:edit_desc:"))
async def cb_edit_desc(callback: CallbackQuery, state: FSMContext) -> None:
    try:
        plan_id = callback.data.split(":")[2]
        await state.set_state(PlanEditState.editing_field)
        await state.update_data(edit_field="description", edit_plan_id=plan_id)
        builder = InlineKeyboardBuilder()
        builder.button(text="◀️ Отмена", callback_data=f"adm_plan:view:{plan_id}")
        await callback.message.edit_text("Введите новое описание:", reply_markup=builder.as_markup())
        await callback.answer()
    except Exception:
        logger.exception("Ошибка в cb_edit_desc")
        await callback.answer("Произошла ошибка.", show_alert=True)


@router.message(PlanEditState.editing_field)
async def handle_edit_field(message: Message, state: FSMContext, storage_backend: BaseStorage) -> None:
    try:
        data = await state.get_data()
        field = data.get("edit_field")
        plan_id = data.get("edit_plan_id")
        await state.clear()

        plan = await storage_backend.get_subscription_plan(plan_id)
        if plan is None:
            await message.answer("Тариф не найден.")
            return

        raw = (message.text or "").strip()
        if field == "price":
            try:
                plan.price = float(raw.replace(",", "."))
            except ValueError:
                await message.answer("Некорректная цена.")
                return
        elif field == "name":
            plan.name = raw
        elif field == "description":
            plan.description = raw

        await storage_backend.save_subscription_plan(plan)

        builder = InlineKeyboardBuilder()
        builder.button(text="◀️ К тарифу", callback_data=f"adm_plan:view:{plan_id}")
        await message.answer(f"✅ Поле обновлено.", reply_markup=builder.as_markup())
    except Exception:
        logger.exception("Ошибка в handle_edit_field")
        await message.answer("Произошла ошибка.")
        await state.clear()
