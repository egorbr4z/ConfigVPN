"""Build-your-own VPN server handler."""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery

from core.models import User
from core.storage import BaseStorage
from main_bot.keyboards.inline import (
    kb_custom_vpn_confirm,
    kb_custom_vpn_type,
    kb_preset_select,
    kb_provider_select,
)

logger = logging.getLogger(__name__)
router = Router(name="custom_vpn")


class CustomVPNState(StatesGroup):
    choosing_type = State()
    choosing_providers = State()
    choosing_preset = State()
    confirming = State()


@router.callback_query(F.data == "menu:custom_vpn")
async def cb_custom_vpn_menu(callback: CallbackQuery, state: FSMContext) -> None:
    try:
        await state.set_state(CustomVPNState.choosing_type)
        await callback.message.edit_text(
            "🛠 *Собрать свой VPN сервер*\n\n"
            "Выберите тип VPN, который хотите настроить:",
            reply_markup=kb_custom_vpn_type(),
        )
        await callback.answer()
    except Exception:
        logger.exception("Ошибка в cb_custom_vpn_menu")
        await callback.answer("Произошла ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("cvpn_type:"))
async def cb_cvpn_type(callback: CallbackQuery, state: FSMContext, storage_backend: BaseStorage, user: User) -> None:
    try:
        vpn_type = callback.data.split(":")[1]

        # Check subscription limit
        active_subs = await storage_backend.get_user_subscriptions(user.telegram_id, active_only=True)
        already_has = any(s.type == vpn_type for s in active_subs)
        if already_has:
            type_label = "белый список" if vpn_type == "whitelist" else "обычный"
            await callback.answer(
                f"У вас уже есть активная подписка типа «{type_label}».",
                show_alert=True,
            )
            return

        max_providers = 2 if vpn_type == "whitelist" else 1
        await state.set_state(CustomVPNState.choosing_providers)
        await state.update_data(vpn_type=vpn_type, selected_providers=[], max_providers=max_providers)

        providers = await storage_backend.get_providers(active_only=True)
        if vpn_type == "whitelist":
            providers = [p for p in providers if p.supports_whitelist]

        type_label = "белый список" if vpn_type == "whitelist" else "обычный"
        if vpn_type == "whitelist":
            hint = "Выберите 1 российский 🇷🇺 и 1 зарубежный 🌍 сервер:"
        else:
            hint = "Выберите провайдера:"

        if not providers:
            await callback.message.edit_text(
                "Провайдеры временно недоступны. Попробуйте позже.",
                reply_markup=kb_custom_vpn_type(),
            )
            await callback.answer()
            return

        await callback.message.edit_text(
            f"🛠 *Собрать свой VPN — {type_label}*\n\n{hint}",
            reply_markup=kb_provider_select(providers, [], vpn_type, max_providers),
        )
        await callback.answer()
    except Exception:
        logger.exception("Ошибка в cb_cvpn_type")
        await callback.answer("Произошла ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("prov_select:"), CustomVPNState.choosing_providers)
async def cb_prov_select(callback: CallbackQuery, state: FSMContext, storage_backend: BaseStorage) -> None:
    try:
        provider_id = callback.data.split(":")[1]
        data = await state.get_data()
        selected: list[str] = data.get("selected_providers", [])
        vpn_type: str = data.get("vpn_type", "regular")
        max_providers: int = data.get("max_providers", 1)

        if provider_id in selected:
            selected.remove(provider_id)
        elif len(selected) < max_providers:
            selected.append(provider_id)
        else:
            await callback.answer(
                f"Можно выбрать не более {max_providers} провайдера(-ов).",
                show_alert=True,
            )
            return

        await state.update_data(selected_providers=selected)
        providers = await storage_backend.get_providers(active_only=True)

        type_label = "белый список" if vpn_type == "whitelist" else "обычный"
        if vpn_type == "whitelist":
            hint = (
                f"Выберите 1 российский и 1 зарубежный сервер (выбрано: {len(selected)}/2):\n"
                f"🇷🇺 — российский, 🌍 — зарубежный"
            )
        else:
            hint = f"Выберите провайдера (выбрано: {len(selected)}/1):"

        await callback.message.edit_text(
            f"🛠 *Собрать свой VPN — {type_label}*\n\n{hint}",
            reply_markup=kb_provider_select(providers, selected, vpn_type, max_providers),
        )
        await callback.answer()
    except Exception:
        logger.exception("Ошибка в cb_prov_select")
        await callback.answer("Произошла ошибка.", show_alert=True)


@router.callback_query(F.data == "prov_confirm", CustomVPNState.choosing_providers)
async def cb_prov_confirm(callback: CallbackQuery, state: FSMContext, storage_backend: BaseStorage) -> None:
    try:
        data = await state.get_data()
        selected: list[str] = data.get("selected_providers", [])
        vpn_type: str = data.get("vpn_type", "regular")
        max_providers: int = data.get("max_providers", 1)

        if len(selected) != max_providers:
            await callback.answer(
                f"Пожалуйста, выберите ровно {max_providers} провайдера(-ов).",
                show_alert=True,
            )
            return

        if vpn_type == "whitelist":
            all_provs = await storage_backend.get_providers(active_only=True)
            prov_map = {p.id: p for p in all_provs}
            selected_provs = [prov_map[pid] for pid in selected if pid in prov_map]
            has_russian = any(p.is_russian for p in selected_provs)
            has_foreign = any(not p.is_russian for p in selected_provs)
            if not has_russian or not has_foreign:
                await callback.answer(
                    "Для белого списка необходимо выбрать 1 российский 🇷🇺 и 1 зарубежный 🌍 сервер.",
                    show_alert=True,
                )
                return

        # Find presets. For whitelist with 2 providers, show presets for first provider
        # (preset defines server specs; same spec applied to both)
        primary_provider_id = selected[0]
        presets = await storage_backend.get_presets(provider_id=primary_provider_id, active_only=True)

        if not presets:
            # Try getting presets for any provider if none found for primary
            presets = await storage_backend.get_presets(active_only=True)

        if not presets:
            await callback.message.edit_text(
                "Конфигурации серверов временно недоступны. Попробуйте позже.",
                reply_markup=kb_custom_vpn_type(),
            )
            await callback.answer()
            return

        await state.set_state(CustomVPNState.choosing_preset)

        type_label = "белый список" if vpn_type == "whitelist" else "обычный"
        await callback.message.edit_text(
            f"🛠 *Собрать свой VPN — {type_label}*\n\nВыберите конфигурацию сервера:",
            reply_markup=kb_preset_select(presets),
        )
        await callback.answer()
    except Exception:
        logger.exception("Ошибка в cb_prov_confirm")
        await callback.answer("Произошла ошибка.", show_alert=True)


@router.callback_query(F.data == "prov_back", CustomVPNState.choosing_preset)
async def cb_prov_back(callback: CallbackQuery, state: FSMContext, storage_backend: BaseStorage) -> None:
    try:
        data = await state.get_data()
        selected: list[str] = data.get("selected_providers", [])
        vpn_type: str = data.get("vpn_type", "regular")
        max_providers: int = data.get("max_providers", 1)

        await state.set_state(CustomVPNState.choosing_providers)
        providers = await storage_backend.get_providers(active_only=True)
        type_label = "белый список" if vpn_type == "whitelist" else "обычный"
        hint = f"Выберите {'2 провайдера' if max_providers == 2 else '1 провайдера'}:"

        await callback.message.edit_text(
            f"🛠 *Собрать свой VPN — {type_label}*\n\n{hint}",
            reply_markup=kb_provider_select(providers, selected, vpn_type, max_providers),
        )
        await callback.answer()
    except Exception:
        logger.exception("Ошибка в cb_prov_back")
        await callback.answer("Произошла ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("preset_select:"), CustomVPNState.choosing_preset)
async def cb_preset_select(callback: CallbackQuery, state: FSMContext, storage_backend: BaseStorage) -> None:
    try:
        preset_id = callback.data.split(":")[1]
        preset = await storage_backend.get_preset(preset_id)
        if preset is None or not preset.is_active:
            await callback.answer("Этот пресет недоступен.", show_alert=True)
            return

        data = await state.get_data()
        selected_providers: list[str] = data.get("selected_providers", [])
        vpn_type: str = data.get("vpn_type", "regular")

        await state.update_data(preset_id=preset_id)
        await state.set_state(CustomVPNState.confirming)

        # Build summary
        provider_lines = []
        for pid in selected_providers:
            prov = await storage_backend.get_provider(pid)
            if prov:
                provider_lines.append(f"• {prov.name} ({prov.location})")

        providers_text = "\n".join(provider_lines) if provider_lines else "—"
        type_label = "Белый список" if vpn_type == "whitelist" else "Обычный VPN"

        total_price = preset.price * len(selected_providers)

        text = (
            f"🛠 *Итог заказа*\n\n"
            f"Тип: {type_label}\n"
            f"Провайдеры:\n{providers_text}\n\n"
            f"Конфигурация: RAM {preset.ram_gb} ГБ / CPU {preset.cpu_count}\n"
            f"Стоимость: *{total_price:.0f} ₽/мес*\n\n"
            f"Подтвердите заказ для перехода к оплате."
        )

        await callback.message.edit_text(text, reply_markup=kb_custom_vpn_confirm(preset_id))
        await callback.answer()
    except Exception:
        logger.exception("Ошибка в cb_preset_select")
        await callback.answer("Произошла ошибка.", show_alert=True)


@router.callback_query(F.data == "preset_back", CustomVPNState.confirming)
async def cb_preset_back(callback: CallbackQuery, state: FSMContext, storage_backend: BaseStorage) -> None:
    try:
        data = await state.get_data()
        selected: list[str] = data.get("selected_providers", [])
        primary_provider_id = selected[0] if selected else None
        presets = await storage_backend.get_presets(provider_id=primary_provider_id, active_only=True)
        if not presets:
            presets = await storage_backend.get_presets(active_only=True)

        await state.set_state(CustomVPNState.choosing_preset)
        vpn_type = data.get("vpn_type", "regular")
        type_label = "белый список" if vpn_type == "whitelist" else "обычный"

        await callback.message.edit_text(
            f"🛠 *Собрать свой VPN — {type_label}*\n\nВыберите конфигурацию сервера:",
            reply_markup=kb_preset_select(presets),
        )
        await callback.answer()
    except Exception:
        logger.exception("Ошибка в cb_preset_back")
        await callback.answer("Произошла ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("cvpn_confirm:"), CustomVPNState.confirming)
async def cb_cvpn_confirm(callback: CallbackQuery, state: FSMContext, storage_backend: BaseStorage, user: User) -> None:
    """Proceed to payment for custom VPN."""
    try:
        preset_id = callback.data.split(":")[1]
        preset = await storage_backend.get_preset(preset_id)
        if preset is None:
            await callback.answer("Конфигурация недоступна.", show_alert=True)
            return

        data = await state.get_data()
        selected_providers: list[str] = data.get("selected_providers", [])
        vpn_type: str = data.get("vpn_type", "regular")

        from main_bot.handlers.payment import initiate_payment_for_custom_vpn
        await initiate_payment_for_custom_vpn(
            callback, storage_backend, user, preset, selected_providers, vpn_type, state
        )
    except Exception:
        logger.exception("Ошибка в cb_cvpn_confirm")
        await callback.answer("Произошла ошибка.", show_alert=True)
