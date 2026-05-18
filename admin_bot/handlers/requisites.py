"""Payment requisites management for admin bot."""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from core.models import Requisite
from core.storage import BaseStorage

logger = logging.getLogger(__name__)
router = Router(name="admin_requisites")


class RequisiteAddState(StatesGroup):
    choosing_type = State()
    entering_value = State()
    entering_holder = State()


def kb_requisites_list(requisites: list[Requisite]) -> object:
    builder = InlineKeyboardBuilder()
    for r in requisites:
        status = "✅" if r.is_active else "❌"
        type_label = "💳" if r.type == "card" else "📱"
        builder.button(
            text=f"{status} {type_label} {r.value[:12]}... ({r.holder_name})",
            callback_data=f"adm_req:view:{r.id}",
        )
    builder.button(text="➕ Добавить реквизит", callback_data="adm_req:add")
    builder.button(text="◀️ Назад", callback_data="adm:main")
    builder.adjust(1)
    return builder.as_markup()


def kb_requisite_detail(req: Requisite) -> object:
    builder = InlineKeyboardBuilder()
    toggle_label = "❌ Деактивировать" if req.is_active else "✅ Активировать"
    builder.button(text=toggle_label, callback_data=f"adm_req:toggle:{req.id}")
    builder.button(text="🗑 Удалить", callback_data=f"adm_req:delete:{req.id}")
    builder.button(text="◀️ Назад", callback_data="adm:requisites")
    builder.adjust(1)
    return builder.as_markup()


@router.callback_query(F.data == "adm:requisites")
async def cb_requisites(callback: CallbackQuery, storage_backend: BaseStorage) -> None:
    try:
        reqs = await storage_backend.get_requisites(active_only=False)
        await callback.message.edit_text(
            f"🏦 *Реквизиты для оплаты* (всего: {len(reqs)})",
            reply_markup=kb_requisites_list(reqs),
        )
        await callback.answer()
    except Exception:
        logger.exception("Ошибка в cb_requisites")
        await callback.answer("Произошла ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("adm_req:view:"))
async def cb_requisite_view(callback: CallbackQuery, storage_backend: BaseStorage) -> None:
    try:
        req_id = callback.data.split(":")[2]
        req = await storage_backend.get_requisite(req_id)
        if req is None:
            await callback.answer("Реквизит не найден.", show_alert=True)
            return

        type_label = "Банковская карта" if req.type == "card" else "Телефон (СБП)"
        status = "✅ Активен" if req.is_active else "❌ Неактивен"

        text = (
            f"🏦 *Реквизит*\n\n"
            f"Тип: {type_label}\n"
            f"Значение: `{req.value}`\n"
            f"Держатель: {req.holder_name}\n"
            f"Статус: {status}"
        )

        await callback.message.edit_text(text, reply_markup=kb_requisite_detail(req))
        await callback.answer()
    except Exception:
        logger.exception("Ошибка в cb_requisite_view")
        await callback.answer("Произошла ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("adm_req:toggle:"))
async def cb_requisite_toggle(callback: CallbackQuery, storage_backend: BaseStorage) -> None:
    try:
        req_id = callback.data.split(":")[2]
        req = await storage_backend.get_requisite(req_id)
        if req is None:
            await callback.answer("Реквизит не найден.", show_alert=True)
            return

        req.is_active = not req.is_active
        await storage_backend.save_requisite(req)
        status = "активирован" if req.is_active else "деактивирован"
        await callback.answer(f"Реквизит {status}.", show_alert=True)
        await cb_requisite_view(callback, storage_backend)
    except Exception:
        logger.exception("Ошибка в cb_requisite_toggle")
        await callback.answer("Произошла ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("adm_req:delete:"))
async def cb_requisite_delete(callback: CallbackQuery, storage_backend: BaseStorage) -> None:
    try:
        req_id = callback.data.split(":")[2]
        await storage_backend.delete_requisite(req_id)
        await callback.answer("✅ Реквизит удалён.", show_alert=True)

        reqs = await storage_backend.get_requisites(active_only=False)
        await callback.message.edit_text(
            f"🏦 *Реквизиты для оплаты* (всего: {len(reqs)})",
            reply_markup=kb_requisites_list(reqs),
        )
    except Exception:
        logger.exception("Ошибка в cb_requisite_delete")
        await callback.answer("Произошла ошибка.", show_alert=True)


@router.callback_query(F.data == "adm_req:add")
async def cb_requisite_add(callback: CallbackQuery, state: FSMContext) -> None:
    try:
        await state.set_state(RequisiteAddState.choosing_type)
        builder = InlineKeyboardBuilder()
        builder.button(text="💳 Банковская карта", callback_data="req_type_pick:card")
        builder.button(text="📱 Телефон (СБП)", callback_data="req_type_pick:phone")
        builder.button(text="◀️ Отмена", callback_data="adm:requisites")
        builder.adjust(2, 1)

        await callback.message.edit_text(
            "➕ *Новый реквизит*\n\nВыберите тип реквизита:",
            reply_markup=builder.as_markup(),
        )
        await callback.answer()
    except Exception:
        logger.exception("Ошибка в cb_requisite_add")
        await callback.answer("Произошла ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("req_type_pick:"), RequisiteAddState.choosing_type)
async def handle_req_type(callback: CallbackQuery, state: FSMContext) -> None:
    try:
        req_type = callback.data.split(":")[1]
        await state.update_data(req_type=req_type)
        await state.set_state(RequisiteAddState.entering_value)

        type_label = "номер карты (например: 4276 1234 5678 9012)" if req_type == "card" else "номер телефона (например: +7 900 123 45 67)"
        await callback.message.edit_text(f"Введите {type_label}:")
        await callback.answer()
    except Exception:
        logger.exception("Ошибка в handle_req_type")
        await callback.answer("Произошла ошибка.", show_alert=True)


@router.message(RequisiteAddState.entering_value)
async def handle_req_value(message: Message, state: FSMContext) -> None:
    value = (message.text or "").strip()
    if not value:
        await message.answer("Значение не может быть пустым. Введите снова:")
        return
    await state.update_data(req_value=value)
    await state.set_state(RequisiteAddState.entering_holder)
    await message.answer("Введите имя держателя (ФИО владельца карты/счёта):")


@router.message(RequisiteAddState.entering_holder)
async def handle_req_holder(message: Message, state: FSMContext, storage_backend: BaseStorage) -> None:
    try:
        holder = (message.text or "").strip()
        if not holder:
            await message.answer("Имя не может быть пустым. Введите снова:")
            return

        data = await state.get_data()
        await state.clear()

        req = Requisite(
            id=BaseStorage.new_id(),
            type=data["req_type"],
            value=data["req_value"],
            holder_name=holder,
            is_active=True,
        )
        await storage_backend.save_requisite(req)

        builder = InlineKeyboardBuilder()
        builder.button(text="🏦 К реквизитам", callback_data="adm:requisites")
        type_label = "Карта" if req.type == "card" else "Телефон"
        await message.answer(
            f"✅ Реквизит добавлен!\n{type_label}: `{req.value}` ({req.holder_name})",
            reply_markup=builder.as_markup(),
        )
    except Exception:
        logger.exception("Ошибка в handle_req_holder")
        await message.answer("Произошла ошибка.")
        await state.clear()
