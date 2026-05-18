"""Registration and /start handler for the main bot."""

from __future__ import annotations

import logging
import random
import string
from datetime import datetime, timezone

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

import config
from core.models import Referral, User
from core.storage import BaseStorage
from main_bot.keyboards.inline import kb_main_menu, kb_request_phone, kb_remove

logger = logging.getLogger(__name__)
router = Router(name="start")


def _generate_referral_code() -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=8))


async def _show_main_menu(message: Message, is_new: bool = False) -> None:
    greeting = "🎉 Добро пожаловать! Вы успешно зарегистрированы.\n\n" if is_new else ""
    text = (
        f"{greeting}"
        "Добро пожаловать в *ConfigVPN*!\n\n"
        "Выберите нужный раздел:"
    )
    await message.answer(text, reply_markup=kb_main_menu())


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, storage_backend: BaseStorage) -> None:
    try:
        await state.clear()
        user_id = message.from_user.id

        # Check if /start has a referral parameter
        args = message.text.split(maxsplit=1)
        ref_code: str | None = args[1].strip() if len(args) > 1 else None

        existing_user = await storage_backend.get_user(user_id)

        if existing_user is not None:
            if existing_user.is_blocked:
                await message.answer("Ваш аккаунт заблокирован. Обратитесь в поддержку.")
                return
            await message.answer(
                "С возвращением! Рады видеть вас снова.",
                reply_markup=kb_remove(),
            )
            await _show_main_menu(message)
            return

        # New user — request phone number; persist ref_code in FSM
        if ref_code:
            await state.update_data(pending_ref_code=ref_code)

        await message.answer(
            "👋 Добро пожаловать в *ConfigVPN*!\n\n"
            "Для регистрации нам нужен ваш номер телефона.\n"
            "Нажмите кнопку ниже, чтобы поделиться номером.",
            reply_markup=kb_request_phone(),
        )
    except Exception:
        logger.exception("Ошибка в cmd_start")
        await message.answer("Произошла ошибка. Попробуйте позже.")


@router.message(F.contact)
async def handle_contact(message: Message, state: FSMContext, storage_backend: BaseStorage) -> None:
    try:
        if message.contact is None or message.from_user is None:
            return

        # Security: make sure the contact belongs to the sender
        if message.contact.user_id != message.from_user.id:
            await message.answer(
                "Пожалуйста, используйте кнопку для отправки своего номера телефона.",
                reply_markup=kb_request_phone(),
            )
            return

        user_id = message.from_user.id
        phone = message.contact.phone_number
        if not phone.startswith("+"):
            phone = "+" + phone

        # Check again (race condition guard)
        existing = await storage_backend.get_user(user_id)
        if existing is not None:
            await message.answer("Вы уже зарегистрированы!", reply_markup=kb_remove())
            await _show_main_menu(message)
            return

        # Retrieve pending referral code from FSM
        fsm_data = await state.get_data()
        ref_code: str | None = fsm_data.get("pending_ref_code")
        await state.clear()

        # Resolve referral
        referred_by: str | None = None
        referrer: User | None = None
        if ref_code:
            referrer = await storage_backend.get_referral_by_code(ref_code)
            if referrer and referrer.telegram_id != user_id:
                referred_by = ref_code

        # Create user
        new_user = User(
            telegram_id=user_id,
            phone=phone,
            username=message.from_user.username,
            full_name=message.from_user.full_name,
            referral_code=_generate_referral_code(),
            referred_by=referred_by,
            bonus_gb=0.0,
            is_blocked=False,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        await storage_backend.save_user(new_user)

        # Save referral record
        if referrer and referred_by:
            referral = Referral(
                id=BaseStorage.new_id(),
                referrer_id=referrer.telegram_id,
                referred_id=user_id,
                bonus_applied=False,
                created_at=datetime.now(timezone.utc).isoformat(),
            )
            await storage_backend.save_referral(referral)

        await message.answer("✅ Номер телефона подтверждён!", reply_markup=kb_remove())
        await _show_main_menu(message, is_new=True)
    except Exception:
        logger.exception("Ошибка в handle_contact")
        await message.answer("Произошла ошибка при регистрации. Попробуйте позже.")


# Menu navigation back to main
from aiogram.types import CallbackQuery  # noqa: E402 (late import avoids circular)


@router.callback_query(F.data == "menu:main")
async def cb_main_menu(callback: CallbackQuery, state: FSMContext) -> None:
    try:
        await state.clear()
        await callback.message.edit_text(
            "Добро пожаловать в *ConfigVPN*!\n\nВыберите нужный раздел:",
            reply_markup=kb_main_menu(),
        )
        await callback.answer()
    except Exception:
        logger.exception("Ошибка в cb_main_menu")
        await callback.answer("Ошибка. Попробуйте ещё раз.", show_alert=True)
