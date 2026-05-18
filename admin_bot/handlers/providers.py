"""Provider and preset management for admin bot."""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from core.models import Preset, Provider
from core.storage import BaseStorage

logger = logging.getLogger(__name__)
router = Router(name="admin_providers")


class ProviderAddState(StatesGroup):
    entering_name = State()
    entering_location = State()
    entering_server_ip = State()
    entering_supports_whitelist = State()


class PresetAddState(StatesGroup):
    choosing_provider = State()
    entering_ram = State()
    entering_cpu = State()
    entering_price = State()


def kb_providers_list(providers: list[Provider]) -> object:
    builder = InlineKeyboardBuilder()
    for p in providers:
        status = "✅" if p.is_active else "❌"
        wl = "🔒" if p.supports_whitelist else ""
        builder.button(
            text=f"{status}{wl} {p.name} ({p.location})",
            callback_data=f"adm_prov:view:{p.id}",
        )
    builder.button(text="➕ Добавить провайдера", callback_data="adm_prov:add")
    builder.button(text="📋 Пресеты", callback_data="adm_preset:list")
    builder.button(text="◀️ Назад", callback_data="adm:main")
    builder.adjust(1)
    return builder.as_markup()


def kb_provider_detail(provider: Provider) -> object:
    builder = InlineKeyboardBuilder()
    toggle_label = "❌ Деактивировать" if provider.is_active else "✅ Активировать"
    wl_toggle = "🔓 Отключить whitelist" if provider.supports_whitelist else "🔒 Включить whitelist"
    builder.button(text=toggle_label, callback_data=f"adm_prov:toggle:{provider.id}")
    builder.button(text=wl_toggle, callback_data=f"adm_prov:toggle_wl:{provider.id}")
    builder.button(text="✏️ Изменить IP", callback_data=f"adm_prov:edit_ip:{provider.id}")
    builder.button(text="📋 Пресеты провайдера", callback_data=f"adm_preset:by_prov:{provider.id}")
    builder.button(text="🗑 Удалить", callback_data=f"adm_prov:delete:{provider.id}")
    builder.button(text="◀️ Назад", callback_data="adm:providers")
    builder.adjust(1)
    return builder.as_markup()


@router.callback_query(F.data == "adm:providers")
async def cb_providers(callback: CallbackQuery, storage_backend: BaseStorage) -> None:
    try:
        providers = await storage_backend.get_providers(active_only=False)
        await callback.message.edit_text(
            f"🌐 *Провайдеры* (всего: {len(providers)})",
            reply_markup=kb_providers_list(providers),
        )
        await callback.answer()
    except Exception:
        logger.exception("Ошибка в cb_providers")
        await callback.answer("Произошла ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("adm_prov:view:"))
async def cb_provider_view(callback: CallbackQuery, storage_backend: BaseStorage) -> None:
    try:
        prov_id = callback.data.split(":")[2]
        prov = await storage_backend.get_provider(prov_id)
        if prov is None:
            await callback.answer("Провайдер не найден.", show_alert=True)
            return

        status = "✅ Активен" if prov.is_active else "❌ Неактивен"
        wl = "✅ Поддерживается" if prov.supports_whitelist else "❌ Не поддерживается"
        presets = await storage_backend.get_presets(provider_id=prov_id, active_only=False)

        text = (
            f"🌐 *Провайдер*\n\n"
            f"Название: {prov.name}\n"
            f"Локация: {prov.location}\n"
            f"IP сервера: `{prov.server_ip}`\n"
            f"Статус: {status}\n"
            f"Белый список: {wl}\n"
            f"Пресетов: {len(presets)}"
        )

        await callback.message.edit_text(text, reply_markup=kb_provider_detail(prov))
        await callback.answer()
    except Exception:
        logger.exception("Ошибка в cb_provider_view")
        await callback.answer("Произошла ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("adm_prov:toggle:"))
async def cb_provider_toggle(callback: CallbackQuery, storage_backend: BaseStorage) -> None:
    try:
        prov_id = callback.data.split(":")[2]
        prov = await storage_backend.get_provider(prov_id)
        if prov is None:
            await callback.answer("Провайдер не найден.", show_alert=True)
            return
        prov.is_active = not prov.is_active
        await storage_backend.save_provider(prov)
        status = "активирован" if prov.is_active else "деактивирован"
        await callback.answer(f"Провайдер {status}.", show_alert=True)
        await cb_provider_view(callback, storage_backend)
    except Exception:
        logger.exception("Ошибка в cb_provider_toggle")
        await callback.answer("Произошла ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("adm_prov:toggle_wl:"))
async def cb_provider_toggle_wl(callback: CallbackQuery, storage_backend: BaseStorage) -> None:
    try:
        prov_id = callback.data.split(":")[2]
        prov = await storage_backend.get_provider(prov_id)
        if prov is None:
            await callback.answer("Провайдер не найден.", show_alert=True)
            return
        prov.supports_whitelist = not prov.supports_whitelist
        await storage_backend.save_provider(prov)
        status = "включена" if prov.supports_whitelist else "отключена"
        await callback.answer(f"Поддержка белых списков {status}.", show_alert=True)
        await cb_provider_view(callback, storage_backend)
    except Exception:
        logger.exception("Ошибка в cb_provider_toggle_wl")
        await callback.answer("Произошла ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("adm_prov:delete:"))
async def cb_provider_delete(callback: CallbackQuery, storage_backend: BaseStorage) -> None:
    try:
        prov_id = callback.data.split(":")[2]
        await storage_backend.delete_provider(prov_id)
        await callback.answer("✅ Провайдер удалён.", show_alert=True)
        providers = await storage_backend.get_providers(active_only=False)
        await callback.message.edit_text(
            f"🌐 *Провайдеры* (всего: {len(providers)})",
            reply_markup=kb_providers_list(providers),
        )
    except Exception:
        logger.exception("Ошибка в cb_provider_delete")
        await callback.answer("Произошла ошибка.", show_alert=True)


# ------- Edit IP -------

class ProviderEditState(StatesGroup):
    editing_ip = State()


@router.callback_query(F.data.startswith("adm_prov:edit_ip:"))
async def cb_edit_ip(callback: CallbackQuery, state: FSMContext) -> None:
    try:
        prov_id = callback.data.split(":")[2]
        await state.set_state(ProviderEditState.editing_ip)
        await state.update_data(prov_id=prov_id)
        builder = InlineKeyboardBuilder()
        builder.button(text="◀️ Отмена", callback_data=f"adm_prov:view:{prov_id}")
        await callback.message.edit_text(
            "Введите новый IP-адрес сервера:", reply_markup=builder.as_markup()
        )
        await callback.answer()
    except Exception:
        logger.exception("Ошибка в cb_edit_ip")
        await callback.answer("Произошла ошибка.", show_alert=True)


@router.message(ProviderEditState.editing_ip)
async def handle_edit_ip(message: Message, state: FSMContext, storage_backend: BaseStorage) -> None:
    try:
        new_ip = (message.text or "").strip()
        data = await state.get_data()
        prov_id = data.get("prov_id")
        await state.clear()

        prov = await storage_backend.get_provider(prov_id)
        if prov is None:
            await message.answer("Провайдер не найден.")
            return

        prov.server_ip = new_ip
        await storage_backend.save_provider(prov)

        builder = InlineKeyboardBuilder()
        builder.button(text="◀️ К провайдеру", callback_data=f"adm_prov:view:{prov_id}")
        await message.answer(f"✅ IP-адрес обновлён: `{new_ip}`", reply_markup=builder.as_markup())
    except Exception:
        logger.exception("Ошибка в handle_edit_ip")
        await message.answer("Произошла ошибка.")
        await state.clear()


# ------- Add provider -------

@router.callback_query(F.data == "adm_prov:add")
async def cb_provider_add(callback: CallbackQuery, state: FSMContext) -> None:
    try:
        await state.set_state(ProviderAddState.entering_name)
        builder = InlineKeyboardBuilder()
        builder.button(text="◀️ Отмена", callback_data="adm:providers")
        await callback.message.edit_text(
            "➕ *Новый провайдер*\n\nВведите название провайдера:",
            reply_markup=builder.as_markup(),
        )
        await callback.answer()
    except Exception:
        logger.exception("Ошибка в cb_provider_add")
        await callback.answer("Произошла ошибка.", show_alert=True)


@router.message(ProviderAddState.entering_name)
async def handle_prov_name(message: Message, state: FSMContext) -> None:
    await state.update_data(name=(message.text or "").strip())
    await state.set_state(ProviderAddState.entering_location)
    await message.answer("Введите локацию (например: Нидерланды, Амстердам):")


@router.message(ProviderAddState.entering_location)
async def handle_prov_location(message: Message, state: FSMContext) -> None:
    await state.update_data(location=(message.text or "").strip())
    await state.set_state(ProviderAddState.entering_server_ip)
    await message.answer("Введите IP-адрес сервера:")


@router.message(ProviderAddState.entering_server_ip)
async def handle_prov_ip(message: Message, state: FSMContext) -> None:
    await state.update_data(server_ip=(message.text or "").strip())
    await state.set_state(ProviderAddState.entering_supports_whitelist)
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да", callback_data="prov_wl_choice:yes")
    builder.button(text="❌ Нет", callback_data="prov_wl_choice:no")
    await message.answer("Поддерживает белые списки?", reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith("prov_wl_choice:"), ProviderAddState.entering_supports_whitelist)
async def handle_prov_wl_choice(callback: CallbackQuery, state: FSMContext, storage_backend: BaseStorage) -> None:
    try:
        supports_wl = callback.data.split(":")[1] == "yes"
        data = await state.get_data()
        await state.clear()

        prov = Provider(
            id=BaseStorage.new_id(),
            name=data["name"],
            location=data["location"],
            server_ip=data["server_ip"],
            is_active=True,
            supports_whitelist=supports_wl,
        )
        await storage_backend.save_provider(prov)

        builder = InlineKeyboardBuilder()
        builder.button(text="📋 К провайдерам", callback_data="adm:providers")
        await callback.message.edit_text(
            f"✅ Провайдер *{prov.name}* добавлен!",
            reply_markup=builder.as_markup(),
        )
        await callback.answer()
    except Exception:
        logger.exception("Ошибка в handle_prov_wl_choice")
        await callback.answer("Произошла ошибка.", show_alert=True)


# ------- Presets -------

def kb_presets_list(presets: list[Preset], provider_id: str | None = None) -> object:
    builder = InlineKeyboardBuilder()
    for p in presets:
        status = "✅" if p.is_active else "❌"
        builder.button(
            text=f"{status} RAM {p.ram_gb}ГБ / CPU {p.cpu_count} — {p.price:.0f} ₽",
            callback_data=f"adm_preset:view:{p.id}",
        )
    builder.button(text="➕ Добавить пресет", callback_data="adm_preset:add")
    back_target = f"adm_prov:view:{provider_id}" if provider_id else "adm:providers"
    builder.button(text="◀️ Назад", callback_data=back_target)
    builder.adjust(1)
    return builder.as_markup()


@router.callback_query(F.data == "adm_preset:list")
async def cb_presets_list(callback: CallbackQuery, storage_backend: BaseStorage) -> None:
    try:
        presets = await storage_backend.get_presets(active_only=False)
        await callback.message.edit_text(
            f"📋 *Пресеты* (всего: {len(presets)})",
            reply_markup=kb_presets_list(presets),
        )
        await callback.answer()
    except Exception:
        logger.exception("Ошибка в cb_presets_list")
        await callback.answer("Произошла ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("adm_preset:by_prov:"))
async def cb_presets_by_provider(callback: CallbackQuery, storage_backend: BaseStorage) -> None:
    try:
        prov_id = callback.data.split(":")[2]
        presets = await storage_backend.get_presets(provider_id=prov_id, active_only=False)
        prov = await storage_backend.get_provider(prov_id)
        prov_name = prov.name if prov else prov_id

        await callback.message.edit_text(
            f"📋 *Пресеты провайдера {prov_name}* (всего: {len(presets)})",
            reply_markup=kb_presets_list(presets, provider_id=prov_id),
        )
        await callback.answer()
    except Exception:
        logger.exception("Ошибка в cb_presets_by_provider")
        await callback.answer("Произошла ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("adm_preset:view:"))
async def cb_preset_view(callback: CallbackQuery, storage_backend: BaseStorage) -> None:
    try:
        preset_id = callback.data.split(":")[2]
        preset = await storage_backend.get_preset(preset_id)
        if preset is None:
            await callback.answer("Пресет не найден.", show_alert=True)
            return

        prov = await storage_backend.get_provider(preset.provider_id)
        prov_name = prov.name if prov else preset.provider_id
        status = "✅ Активен" if preset.is_active else "❌ Неактивен"

        builder = InlineKeyboardBuilder()
        toggle = "❌ Деактивировать" if preset.is_active else "✅ Активировать"
        builder.button(text=toggle, callback_data=f"adm_preset:toggle:{preset_id}")
        builder.button(text="🗑 Удалить", callback_data=f"adm_preset:delete:{preset_id}")
        builder.button(text="◀️ Назад", callback_data="adm_preset:list")
        builder.adjust(1)

        text = (
            f"📋 *Пресет*\n\n"
            f"Провайдер: {prov_name}\n"
            f"RAM: {preset.ram_gb} ГБ\n"
            f"CPU: {preset.cpu_count} ядра\n"
            f"Цена: *{preset.price:.0f} ₽/мес*\n"
            f"Статус: {status}"
        )

        await callback.message.edit_text(text, reply_markup=builder.as_markup())
        await callback.answer()
    except Exception:
        logger.exception("Ошибка в cb_preset_view")
        await callback.answer("Произошла ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("adm_preset:toggle:"))
async def cb_preset_toggle(callback: CallbackQuery, storage_backend: BaseStorage) -> None:
    try:
        preset_id = callback.data.split(":")[2]
        preset = await storage_backend.get_preset(preset_id)
        if preset is None:
            await callback.answer("Пресет не найден.", show_alert=True)
            return
        preset.is_active = not preset.is_active
        await storage_backend.save_preset(preset)
        status = "активирован" if preset.is_active else "деактивирован"
        await callback.answer(f"Пресет {status}.", show_alert=True)
        await cb_preset_view(callback, storage_backend)
    except Exception:
        logger.exception("Ошибка в cb_preset_toggle")
        await callback.answer("Произошла ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("adm_preset:delete:"))
async def cb_preset_delete(callback: CallbackQuery, storage_backend: BaseStorage) -> None:
    try:
        preset_id = callback.data.split(":")[2]
        await storage_backend.delete_preset(preset_id)
        await callback.answer("✅ Пресет удалён.", show_alert=True)
        presets = await storage_backend.get_presets(active_only=False)
        await callback.message.edit_text(
            f"📋 *Пресеты* (всего: {len(presets)})",
            reply_markup=kb_presets_list(presets),
        )
    except Exception:
        logger.exception("Ошибка в cb_preset_delete")
        await callback.answer("Произошла ошибка.", show_alert=True)


@router.callback_query(F.data == "adm_preset:add")
async def cb_preset_add(callback: CallbackQuery, state: FSMContext, storage_backend: BaseStorage) -> None:
    try:
        providers = await storage_backend.get_providers(active_only=True)
        if not providers:
            await callback.answer("Нет доступных провайдеров.", show_alert=True)
            return

        await state.set_state(PresetAddState.choosing_provider)
        builder = InlineKeyboardBuilder()
        for p in providers:
            builder.button(text=p.name, callback_data=f"preset_prov_pick:{p.id}")
        builder.button(text="◀️ Отмена", callback_data="adm_preset:list")
        builder.adjust(1)

        await callback.message.edit_text(
            "➕ *Новый пресет*\n\nВыберите провайдера:",
            reply_markup=builder.as_markup(),
        )
        await callback.answer()
    except Exception:
        logger.exception("Ошибка в cb_preset_add")
        await callback.answer("Произошла ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("preset_prov_pick:"), PresetAddState.choosing_provider)
async def handle_preset_prov(callback: CallbackQuery, state: FSMContext) -> None:
    try:
        prov_id = callback.data.split(":")[1]
        await state.update_data(provider_id=prov_id)
        await state.set_state(PresetAddState.entering_ram)
        await callback.message.edit_text("Введите объём RAM в ГБ (например: 2):")
        await callback.answer()
    except Exception:
        logger.exception("Ошибка в handle_preset_prov")
        await callback.answer("Произошла ошибка.", show_alert=True)


@router.message(PresetAddState.entering_ram)
async def handle_preset_ram(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip()
    if not raw.isdigit() or int(raw) <= 0:
        await message.answer("Введите целое положительное число:")
        return
    await state.update_data(ram_gb=int(raw))
    await state.set_state(PresetAddState.entering_cpu)
    await message.answer("Введите количество ядер CPU (например: 2):")


@router.message(PresetAddState.entering_cpu)
async def handle_preset_cpu(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip()
    if not raw.isdigit() or int(raw) <= 0:
        await message.answer("Введите целое положительное число:")
        return
    await state.update_data(cpu_count=int(raw))
    await state.set_state(PresetAddState.entering_price)
    await message.answer("Введите цену в рублях в месяц (например: 500):")


@router.message(PresetAddState.entering_price)
async def handle_preset_price(message: Message, state: FSMContext, storage_backend: BaseStorage) -> None:
    try:
        raw = (message.text or "").strip().replace(",", ".")
        try:
            price = float(raw)
            if price <= 0:
                raise ValueError
        except ValueError:
            await message.answer("Введите корректную цену:")
            return

        data = await state.get_data()
        await state.clear()

        preset = Preset(
            id=BaseStorage.new_id(),
            provider_id=data["provider_id"],
            ram_gb=data["ram_gb"],
            cpu_count=data["cpu_count"],
            price=price,
            is_active=True,
        )
        await storage_backend.save_preset(preset)

        builder = InlineKeyboardBuilder()
        builder.button(text="📋 К пресетам", callback_data="adm_preset:list")
        await message.answer(
            f"✅ Пресет добавлен: RAM {preset.ram_gb} ГБ / CPU {preset.cpu_count} — {preset.price:.0f} ₽/мес",
            reply_markup=builder.as_markup(),
        )
    except Exception:
        logger.exception("Ошибка в handle_preset_price")
        await message.answer("Произошла ошибка.")
        await state.clear()
