"""Admin dashboard handler."""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

import config
from core.storage import BaseStorage

logger = logging.getLogger(__name__)
router = Router(name="admin_dashboard")


class SettingsSG(StatesGroup):
    editing_admin_ids = State()
    editing_faq = State()


def _is_admin(user_id: int, admin_ids: list[int]) -> bool:
    return user_id in admin_ids


def kb_admin_main() -> object:
    builder = InlineKeyboardBuilder()
    builder.button(text="👤 Пользователи", callback_data="adm:users")
    builder.button(text="📦 Тарифы", callback_data="adm:subscriptions")
    builder.button(text="🌐 Провайдеры", callback_data="adm:providers")
    builder.button(text="💳 Платежи", callback_data="adm:payments")
    builder.button(text="🏦 Реквизиты", callback_data="adm:requisites")
    builder.button(text="⚙️ Настройки", callback_data="adm:settings")
    builder.adjust(2)
    return builder.as_markup()


def kb_back_to_admin() -> object:
    builder = InlineKeyboardBuilder()
    builder.button(text="◀️ Главное меню", callback_data="adm:main")
    return builder.as_markup()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, storage_backend: BaseStorage) -> None:
    try:
        await state.clear()
        user_id = message.from_user.id
        settings = await storage_backend.get_settings()
        admin_ids = config.ADMIN_IDS or settings.admin_ids

        if not _is_admin(user_id, admin_ids):
            await message.answer("⛔️ Доступ запрещён.")
            return

        await _show_dashboard(message, storage_backend)
    except Exception:
        logger.exception("Ошибка в admin cmd_start")
        await message.answer("Произошла ошибка.")


async def _show_dashboard(message_or_cb, storage_backend: BaseStorage, is_callback: bool = False) -> None:
    users = await storage_backend.get_all_users()
    pending_payments = await storage_backend.get_payments(status="pending")
    active_subs = await storage_backend.get_all_subscriptions(active_only=True)

    text = (
        "🛡 *Панель администратора ConfigVPN*\n\n"
        f"👥 Всего пользователей: *{len(users)}*\n"
        f"💳 Ожидает подтверждения: *{len(pending_payments)}*\n"
        f"✅ Активных подписок: *{len(active_subs)}*\n\n"
        "Выберите раздел:"
    )

    if is_callback:
        await message_or_cb.message.edit_text(text, reply_markup=kb_admin_main())
        await message_or_cb.answer()
    else:
        await message_or_cb.answer(text, reply_markup=kb_admin_main())


@router.callback_query(F.data == "adm:main")
async def cb_admin_main(callback: CallbackQuery, state: FSMContext, storage_backend: BaseStorage) -> None:
    try:
        await state.clear()
        user_id = callback.from_user.id
        settings = await storage_backend.get_settings()
        admin_ids = config.ADMIN_IDS or settings.admin_ids

        if not _is_admin(user_id, admin_ids):
            await callback.answer("⛔️ Доступ запрещён.", show_alert=True)
            return

        await _show_dashboard(callback, storage_backend, is_callback=True)
    except Exception:
        logger.exception("Ошибка в cb_admin_main")
        await callback.answer("Произошла ошибка.", show_alert=True)


@router.callback_query(F.data == "adm:settings")
async def cb_admin_settings(callback: CallbackQuery, storage_backend: BaseStorage) -> None:
    try:
        settings = await storage_backend.get_settings()
        builder = InlineKeyboardBuilder()
        builder.button(text="✏️ Изменить FAQ", callback_data="adm_set:edit_faq")
        builder.button(text="👤 Список админов", callback_data="adm_set:admin_ids")
        builder.button(text="◀️ Назад", callback_data="adm:main")
        builder.adjust(1)

        admin_ids_str = ", ".join(str(i) for i in settings.admin_ids) or "—"
        text = (
            f"⚙️ *Настройки*\n\n"
            f"Бонус за реферала: *{settings.referral_bonus_gb:.0f} ГБ*\n"
            f"Username бота: {settings.bot_username or '—'}\n"
            f"Список администраторов: {admin_ids_str}\n\n"
            f"Уведомления о платежах: "
            f"{'✅' if settings.notifications.get('notify_admins_on_payment') else '❌'}"
        )

        await callback.message.edit_text(text, reply_markup=builder.as_markup())
        await callback.answer()
    except Exception:
        logger.exception("Ошибка в cb_admin_settings")
        await callback.answer("Произошла ошибка.", show_alert=True)


@router.callback_query(F.data == "adm_set:admin_ids")
async def cb_settings_admin_ids(callback: CallbackQuery, state: FSMContext) -> None:
    try:
        await state.set_state(SettingsSG.editing_admin_ids)
        await callback.message.edit_text(
            "Введите список ID администраторов через запятую:\n"
            "_Например: 123456789, 987654321_",
            reply_markup=InlineKeyboardBuilder().button(
                text="◀️ Отмена", callback_data="adm:settings"
            ).as_markup(),
        )
        await callback.answer()
    except Exception:
        logger.exception("Ошибка в cb_settings_admin_ids")
        await callback.answer("Произошла ошибка.", show_alert=True)


@router.callback_query(F.data == "adm_set:edit_faq")
async def cb_settings_edit_faq(callback: CallbackQuery, state: FSMContext) -> None:
    try:
        await state.set_state(SettingsSG.editing_faq)
        await callback.message.edit_text(
            "Введите новый текст FAQ:\n_(поддерживается Markdown)_",
            reply_markup=InlineKeyboardBuilder().button(
                text="◀️ Отмена", callback_data="adm:settings"
            ).as_markup(),
        )
        await callback.answer()
    except Exception:
        logger.exception("Ошибка в cb_settings_edit_faq")
        await callback.answer("Произошла ошибка.", show_alert=True)


@router.message(SettingsSG.editing_admin_ids)
async def handle_admin_ids_input(message: Message, state: FSMContext, storage_backend: BaseStorage) -> None:
    try:
        raw = message.text or ""
        ids = []
        for part in raw.split(","):
            part = part.strip()
            if part.isdigit():
                ids.append(int(part))

        settings = await storage_backend.get_settings()
        settings.admin_ids = ids
        await storage_backend.save_settings(settings)
        await state.clear()
        await message.answer(
            f"✅ Список администраторов обновлён: {ids}",
            reply_markup=InlineKeyboardBuilder().button(
                text="◀️ В настройки", callback_data="adm:settings"
            ).as_markup(),
        )
    except Exception:
        logger.exception("Ошибка в handle_admin_ids_input")
        await message.answer("Произошла ошибка.")
        await state.clear()


@router.message(SettingsSG.editing_faq)
async def handle_faq_input(message: Message, state: FSMContext, storage_backend: BaseStorage) -> None:
    try:
        new_faq = message.text or ""
        settings = await storage_backend.get_settings()
        settings.faq_text = new_faq
        await storage_backend.save_settings(settings)
        await state.clear()
        await message.answer(
            "✅ Текст FAQ обновлён.",
            reply_markup=InlineKeyboardBuilder().button(
                text="◀️ В настройки", callback_data="adm:settings"
            ).as_markup(),
        )
    except Exception:
        logger.exception("Ошибка в handle_faq_input")
        await message.answer("Произошла ошибка.")
        await state.clear()


@router.callback_query(F.data == "noop")
async def cb_noop(callback: CallbackQuery) -> None:
    await callback.answer()
