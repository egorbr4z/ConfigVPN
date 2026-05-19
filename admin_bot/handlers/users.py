"""User management for admin bot."""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from core.models import User
from core.storage import BaseStorage

logger = logging.getLogger(__name__)
router = Router(name="admin_users")

PAGE_SIZE = 10


class UserMgmtState(StatesGroup):
    searching = State()
    adding_bonus = State()


def kb_users_list(users: list[User], page: int, total_pages: int) -> object:
    builder = InlineKeyboardBuilder()
    for u in users:
        status = "🔴" if u.is_blocked else "🟢"
        label = f"{status} {u.full_name} ({u.phone})"
        builder.button(text=label, callback_data=f"adm_usr:view:{u.telegram_id}")

    nav_buttons = 0
    if page > 0:
        builder.button(text="⬅️", callback_data=f"adm_usr:page:{page - 1}")
        nav_buttons += 1
    if total_pages > 1:
        builder.button(text=f"{page + 1}/{total_pages}", callback_data="noop")
        nav_buttons += 1
    if page < total_pages - 1:
        builder.button(text="➡️", callback_data=f"adm_usr:page:{page + 1}")
        nav_buttons += 1

    builder.button(text="🔍 Поиск", callback_data="adm_usr:search")
    builder.button(text="◀️ Назад", callback_data="adm:main")

    row_sizes = [1] * len(users)
    if nav_buttons:
        row_sizes.append(nav_buttons)
    row_sizes += [1, 1]
    builder.adjust(*row_sizes)
    return builder.as_markup()


def kb_user_detail(user_id: int, is_blocked: bool) -> object:
    builder = InlineKeyboardBuilder()
    block_label = "🔓 Разблокировать" if is_blocked else "🔒 Заблокировать"
    builder.button(text=block_label, callback_data=f"adm_usr:toggle_block:{user_id}")
    builder.button(text="🎁 Добавить бонус ГБ", callback_data=f"adm_usr:add_bonus:{user_id}")
    builder.button(text="📋 Подписки", callback_data=f"adm_usr:subs:{user_id}")
    builder.button(text="💳 Платежи", callback_data=f"adm_usr:payments:{user_id}")
    builder.button(text="◀️ К списку", callback_data="adm:users")
    builder.adjust(1)
    return builder.as_markup()


@router.callback_query(F.data == "adm:users")
async def cb_users_list(callback: CallbackQuery, storage_backend: BaseStorage) -> None:
    try:
        await _show_users_page(callback, storage_backend, page=0)
    except Exception:
        logger.exception("Ошибка в cb_users_list")
        await callback.answer("Произошла ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("adm_usr:page:"))
async def cb_users_page(callback: CallbackQuery, storage_backend: BaseStorage) -> None:
    try:
        page = int(callback.data.split(":")[2])
        await _show_users_page(callback, storage_backend, page=page)
    except Exception:
        logger.exception("Ошибка в cb_users_page")
        await callback.answer("Произошла ошибка.", show_alert=True)


async def _show_users_page(callback: CallbackQuery, storage_backend: BaseStorage, page: int) -> None:
    all_users = await storage_backend.get_all_users()
    all_users.sort(key=lambda u: u.created_at, reverse=True)
    total = len(all_users)
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(0, min(page, total_pages - 1))
    slice_ = all_users[page * PAGE_SIZE: (page + 1) * PAGE_SIZE]

    text = f"👤 *Пользователи* (всего: {total})\nСтраница {page + 1} из {total_pages}:"
    await callback.message.edit_text(text, reply_markup=kb_users_list(slice_, page, total_pages))
    await callback.answer()


@router.callback_query(F.data.startswith("adm_usr:view:"))
async def cb_user_view(callback: CallbackQuery, storage_backend: BaseStorage) -> None:
    try:
        user_id = int(callback.data.split(":")[2])
        user = await storage_backend.get_user(user_id)
        if user is None:
            await callback.answer("Пользователь не найден.", show_alert=True)
            return

        active_subs = await storage_backend.get_user_subscriptions(user_id, active_only=True)
        referrals = await storage_backend.get_referrals_by_referrer(user_id)

        status = "🔴 Заблокирован" if user.is_blocked else "🟢 Активен"
        sub_info = f"{len(active_subs)} активных" if active_subs else "нет"

        text = (
            f"👤 *Пользователь*\n\n"
            f"ID: `{user.telegram_id}`\n"
            f"Имя: {user.full_name}\n"
            f"Username: {'@' + user.username if user.username else '—'}\n"
            f"Телефон: {user.phone}\n"
            f"Статус: {status}\n"
            f"Реф. код: `{user.referral_code}`\n"
            f"Приглашён по коду: {user.referred_by or '—'}\n"
            f"Бонусный трафик: *{user.bonus_gb:.1f} ГБ*\n"
            f"Приглашено: {len(referrals)} чел.\n"
            f"Подписки: {sub_info}\n"
            f"Регистрация: {user.created_at[:10]}"
        )

        await callback.message.edit_text(
            text,
            reply_markup=kb_user_detail(user_id, user.is_blocked),
        )
        await callback.answer()
    except Exception:
        logger.exception("Ошибка в cb_user_view")
        await callback.answer("Произошла ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("adm_usr:toggle_block:"))
async def cb_toggle_block(callback: CallbackQuery, storage_backend: BaseStorage) -> None:
    try:
        user_id = int(callback.data.split(":")[2])
        user = await storage_backend.get_user(user_id)
        if user is None:
            await callback.answer("Пользователь не найден.", show_alert=True)
            return

        user.is_blocked = not user.is_blocked
        await storage_backend.save_user(user)

        action = "заблокирован" if user.is_blocked else "разблокирован"
        await callback.answer(f"Пользователь {action}.", show_alert=True)

        # Refresh view
        active_subs = await storage_backend.get_user_subscriptions(user_id, active_only=True)
        referrals = await storage_backend.get_referrals_by_referrer(user_id)
        status = "🔴 Заблокирован" if user.is_blocked else "🟢 Активен"
        sub_info = f"{len(active_subs)} активных" if active_subs else "нет"

        text = (
            f"👤 *Пользователь*\n\n"
            f"ID: `{user.telegram_id}`\n"
            f"Имя: {user.full_name}\n"
            f"Username: {'@' + user.username if user.username else '—'}\n"
            f"Телефон: {user.phone}\n"
            f"Статус: {status}\n"
            f"Реф. код: `{user.referral_code}`\n"
            f"Приглашён по коду: {user.referred_by or '—'}\n"
            f"Бонусный трафик: *{user.bonus_gb:.1f} ГБ*\n"
            f"Приглашено: {len(referrals)} чел.\n"
            f"Подписки: {sub_info}\n"
            f"Регистрация: {user.created_at[:10]}"
        )
        await callback.message.edit_text(
            text,
            reply_markup=kb_user_detail(user_id, user.is_blocked),
        )
    except Exception:
        logger.exception("Ошибка в cb_toggle_block")
        await callback.answer("Произошла ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("adm_usr:add_bonus:"))
async def cb_add_bonus_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    try:
        user_id = int(callback.data.split(":")[2])
        await state.set_state(UserMgmtState.adding_bonus)
        await state.update_data(target_user_id=user_id)

        builder = InlineKeyboardBuilder()
        builder.button(text="◀️ Отмена", callback_data=f"adm_usr:view:{user_id}")

        await callback.message.edit_text(
            f"Введите количество ГБ для добавления пользователю `{user_id}`:\n"
            f"_(например: 50)_",
            reply_markup=builder.as_markup(),
        )
        await callback.answer()
    except Exception:
        logger.exception("Ошибка в cb_add_bonus_prompt")
        await callback.answer("Произошла ошибка.", show_alert=True)


@router.message(UserMgmtState.adding_bonus)
async def handle_bonus_input(message: Message, state: FSMContext, storage_backend: BaseStorage) -> None:
    try:
        raw = (message.text or "").strip().replace(",", ".")
        try:
            bonus = float(raw)
            if bonus <= 0:
                raise ValueError
        except ValueError:
            await message.answer("Введите положительное число (например: 50 или 100.5).")
            return

        data = await state.get_data()
        user_id: int = data["target_user_id"]
        user = await storage_backend.get_user(user_id)
        if user is None:
            await message.answer("Пользователь не найден.")
            await state.clear()
            return

        user.bonus_gb += bonus
        await storage_backend.save_user(user)
        await state.clear()

        builder = InlineKeyboardBuilder()
        builder.button(text="◀️ К пользователю", callback_data=f"adm_usr:view:{user_id}")

        await message.answer(
            f"✅ Пользователю `{user_id}` добавлено *{bonus:.1f} ГБ*.\n"
            f"Итого бонусов: *{user.bonus_gb:.1f} ГБ*.",
            reply_markup=builder.as_markup(),
        )
    except Exception:
        logger.exception("Ошибка в handle_bonus_input")
        await message.answer("Произошла ошибка.")
        await state.clear()


@router.callback_query(F.data.startswith("adm_usr:subs:"))
async def cb_user_subscriptions(callback: CallbackQuery, storage_backend: BaseStorage) -> None:
    try:
        user_id = int(callback.data.split(":")[2])
        subs = await storage_backend.get_user_subscriptions(user_id, active_only=False)

        builder = InlineKeyboardBuilder()
        for sub in subs:
            type_label = "WL" if sub.type == "whitelist" else "REG"
            status = "✅" if sub.is_active else "❌"
            builder.button(
                text=f"{status} [{type_label}] {sub.id[:8]}...",
                callback_data=f"adm_sub_mgmt:view:{sub.id}",
            )
        builder.button(text="◀️ Назад", callback_data=f"adm_usr:view:{user_id}")
        builder.adjust(1)

        text = f"📋 *Подписки пользователя `{user_id}`*\n\nВсего: {len(subs)}"
        await callback.message.edit_text(text, reply_markup=builder.as_markup())
        await callback.answer()
    except Exception:
        logger.exception("Ошибка в cb_user_subscriptions")
        await callback.answer("Произошла ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("adm_sub_mgmt:view:"))
async def cb_sub_view(callback: CallbackQuery, storage_backend: BaseStorage) -> None:
    try:
        sub_id = callback.data.split(":")[2]
        sub = await storage_backend.get_subscription(sub_id)
        if sub is None:
            await callback.answer("Подписка не найдена.", show_alert=True)
            return

        user_id = sub.user_id
        type_label = "Белый список" if sub.type == "whitelist" else "Обычный VPN"
        status = "✅ Активна" if sub.is_active else "❌ Неактивна"

        builder = InlineKeyboardBuilder()
        if sub.is_active:
            builder.button(
                text="❌ Деактивировать",
                callback_data=f"adm_sub_mgmt:deact:{sub_id}",
            )
        builder.button(
            text="📅 Продлить на 30 дней",
            callback_data=f"adm_sub_mgmt:ext:{sub_id}",
        )
        builder.button(text="◀️ Назад", callback_data=f"adm_usr:subs:{user_id}")
        builder.adjust(1)

        text = (
            f"📋 *Подписка*\n\n"
            f"ID: `{sub.id}`\n"
            f"Тип: {type_label}\n"
            f"Статус: {status}\n"
            f"Трафик: {sub.used_gb:.1f} / {sub.traffic_gb:.1f} ГБ\n"
            f"Истекает: {sub.expires_at or '—'}"
        )

        await callback.message.edit_text(text, reply_markup=builder.as_markup())
        await callback.answer()
    except Exception:
        logger.exception("Ошибка в cb_sub_view")
        await callback.answer("Произошла ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("adm_sub_mgmt:deact:"))
async def cb_sub_deactivate(callback: CallbackQuery, storage_backend: BaseStorage) -> None:
    try:
        sub_id = callback.data.split(":")[2]
        sub = await storage_backend.get_subscription(sub_id)
        if sub is None:
            await callback.answer("Подписка не найдена.", show_alert=True)
            return

        user_id = sub.user_id
        await storage_backend.delete_subscription(sub_id)
        await callback.answer("✅ Подписка удалена.", show_alert=True)

        subs = await storage_backend.get_user_subscriptions(user_id, active_only=False)
        builder = InlineKeyboardBuilder()
        for s in subs:
            type_label = "WL" if s.type == "whitelist" else "REG"
            builder.button(
                text=f"✅ [{type_label}] {s.id[:8]}...",
                callback_data=f"adm_sub_mgmt:view:{s.id}",
            )
        builder.button(text="◀️ Назад", callback_data=f"adm_usr:view:{user_id}")
        builder.adjust(1)
        await callback.message.edit_text(
            f"📋 *Подписки пользователя `{user_id}`*\n\nВсего: {len(subs)}",
            reply_markup=builder.as_markup(),
        )
    except Exception:
        logger.exception("Ошибка в cb_sub_deactivate")
        await callback.answer("Произошла ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("adm_sub_mgmt:ext:"))
async def cb_sub_extend(callback: CallbackQuery, storage_backend: BaseStorage) -> None:
    try:
        from datetime import datetime, timedelta, timezone
        sub_id = callback.data.split(":")[2]
        sub = await storage_backend.get_subscription(sub_id)
        if sub is None:
            await callback.answer("Подписка не найдена.", show_alert=True)
            return

        if sub.expires_at:
            try:
                current_expiry = datetime.fromisoformat(sub.expires_at.replace("Z", "+00:00"))
            except ValueError:
                current_expiry = datetime.now(timezone.utc)
        else:
            current_expiry = datetime.now(timezone.utc)

        new_expiry = current_expiry + timedelta(days=30)
        sub.expires_at = new_expiry.isoformat()
        if not sub.is_active:
            sub.is_active = True
        await storage_backend.save_subscription(sub)

        await callback.answer(
            f"✅ Подписка продлена до {new_expiry.strftime('%d.%m.%Y')}.",
            show_alert=True,
        )
        await cb_sub_view(callback, storage_backend)
    except Exception:
        logger.exception("Ошибка в cb_sub_extend")
        await callback.answer("Произошла ошибка.", show_alert=True)


@router.callback_query(F.data == "adm_usr:search")
async def cb_user_search(callback: CallbackQuery, state: FSMContext) -> None:
    try:
        await state.set_state(UserMgmtState.searching)

        builder = InlineKeyboardBuilder()
        builder.button(text="◀️ Отмена", callback_data="adm:users")

        await callback.message.edit_text(
            "🔍 *Поиск пользователя*\n\nВведите номер телефона или Telegram ID:",
            reply_markup=builder.as_markup(),
        )
        await callback.answer()
    except Exception:
        logger.exception("Ошибка в cb_user_search")
        await callback.answer("Произошла ошибка.", show_alert=True)


@router.message(UserMgmtState.searching)
async def handle_user_search(message: Message, state: FSMContext, storage_backend: BaseStorage) -> None:
    try:
        query = (message.text or "").strip()
        all_users = await storage_backend.get_all_users()

        found: list[User] = []
        if query.isdigit():
            user = await storage_backend.get_user(int(query))
            if user:
                found = [user]
        else:
            # Search by phone
            found = [u for u in all_users if query in u.phone]

        await state.clear()

        if not found:
            builder = InlineKeyboardBuilder()
            builder.button(text="◀️ К списку", callback_data="adm:users")
            await message.answer(
                f"Пользователи по запросу «{query}» не найдены.",
                reply_markup=builder.as_markup(),
            )
            return

        builder = InlineKeyboardBuilder()
        for u in found[:10]:
            status = "🔴" if u.is_blocked else "🟢"
            builder.button(
                text=f"{status} {u.full_name} ({u.phone})",
                callback_data=f"adm_usr:view:{u.telegram_id}",
            )
        builder.button(text="◀️ К списку", callback_data="adm:users")
        builder.adjust(1)

        await message.answer(
            f"Результаты поиска: найдено {len(found)}",
            reply_markup=builder.as_markup(),
        )
    except Exception:
        logger.exception("Ошибка в handle_user_search")
        await message.answer("Произошла ошибка.")
        await state.clear()


@router.callback_query(F.data.startswith("adm_usr:payments:"))
async def cb_user_payments(callback: CallbackQuery, storage_backend: BaseStorage) -> None:
    try:
        user_id = int(callback.data.split(":")[2])
        payments = await storage_backend.get_user_payments(user_id)
        payments.sort(key=lambda p: p.created_at, reverse=True)

        lines = [f"💳 *Платежи пользователя `{user_id}`*\n"]
        for p in payments[:10]:
            status_emoji = {"pending": "⏳", "confirmed": "✅", "rejected": "❌"}.get(p.status, "❓")
            lines.append(
                f"{status_emoji} {p.amount:.0f} ₽ — {p.created_at[:10]} "
                f"(`{p.id[:8]}...`)"
            )

        if not payments:
            lines.append("Платежей нет.")

        builder = InlineKeyboardBuilder()
        builder.button(text="◀️ Назад", callback_data=f"adm_usr:view:{user_id}")

        await callback.message.edit_text("\n".join(lines), reply_markup=builder.as_markup())
        await callback.answer()
    except Exception:
        logger.exception("Ошибка в cb_user_payments")
        await callback.answer("Произошла ошибка.", show_alert=True)
