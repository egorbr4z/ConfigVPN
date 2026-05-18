"""All inline and reply keyboards for the main bot."""

from __future__ import annotations

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from core.models import Provider, Preset, SubscriptionPlan


# ---------------------------------------------------------------------------
# Reply keyboards
# ---------------------------------------------------------------------------

def kb_request_phone() -> ReplyKeyboardMarkup:
    """Keyboard to request user phone number."""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Поделиться номером телефона", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def kb_remove() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()


# ---------------------------------------------------------------------------
# Main menu
# ---------------------------------------------------------------------------

def kb_main_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📦 Готовые VPN подписки", callback_data="menu:subscriptions")
    builder.button(text="🛠 Собрать свой VPN", callback_data="menu:custom_vpn")
    builder.button(text="👥 Реферальная программа", callback_data="menu:referral")
    builder.button(text="👤 Мой аккаунт", callback_data="menu:account")
    builder.button(text="❓ FAQ", callback_data="menu:faq")
    builder.adjust(1)
    return builder.as_markup()


def kb_back_to_main() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="◀️ Главное меню", callback_data="menu:main")
    return builder.as_markup()


# ---------------------------------------------------------------------------
# Subscription tabs
# ---------------------------------------------------------------------------

def kb_subscription_tabs() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🔒 Белые списки", callback_data="sub_tab:whitelist")
    builder.button(text="💰 Обычные", callback_data="sub_tab:regular")
    builder.button(text="◀️ Назад", callback_data="menu:main")
    builder.adjust(2, 1)
    return builder.as_markup()


def kb_subscription_plans(plans: list[SubscriptionPlan]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for plan in plans:
        builder.button(
            text=f"{plan.name} — {plan.price:.0f} ₽",
            callback_data=f"sub_plan:{plan.id}",
        )
    builder.button(text="◀️ Назад", callback_data="menu:subscriptions")
    builder.adjust(1)
    return builder.as_markup()


def kb_plan_detail(plan_id: str, plan_type: str = "regular") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="💳 Купить", callback_data=f"sub_buy:{plan_id}")
    builder.button(text="◀️ Назад", callback_data=f"sub_tab:{plan_type}")
    builder.adjust(1)
    return builder.as_markup()


# ---------------------------------------------------------------------------
# Custom VPN
# ---------------------------------------------------------------------------

def kb_custom_vpn_type() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🔒 Белые списки", callback_data="cvpn_type:whitelist")
    builder.button(text="💰 Обычный VPN", callback_data="cvpn_type:regular")
    builder.button(text="◀️ Назад", callback_data="menu:main")
    builder.adjust(2, 1)
    return builder.as_markup()


def kb_provider_select(
    providers: list[Provider],
    selected_ids: list[str],
    vpn_type: str,
    max_select: int,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for prov in providers:
        if vpn_type == "whitelist" and not prov.supports_whitelist:
            continue
        check = "✅ " if prov.id in selected_ids else ""
        flag = "🇷🇺" if prov.is_russian else "🌍"
        builder.button(
            text=f"{check}{flag} {prov.name} ({prov.location})",
            callback_data=f"prov_select:{prov.id}",
        )
    if len(selected_ids) == max_select:
        builder.button(text="➡️ Далее", callback_data="prov_confirm")
    builder.button(text="◀️ Назад", callback_data=f"cvpn_type:{vpn_type}")
    builder.adjust(1)
    return builder.as_markup()


def kb_preset_select(presets: list[Preset]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for preset in presets:
        builder.button(
            text=f"RAM {preset.ram_gb} ГБ / CPU {preset.cpu_count} — {preset.price:.0f} ₽/мес",
            callback_data=f"preset_select:{preset.id}",
        )
    builder.button(text="◀️ Назад", callback_data="prov_back")
    builder.adjust(1)
    return builder.as_markup()


def kb_custom_vpn_confirm(preset_id: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Подтвердить и оплатить", callback_data=f"cvpn_confirm:{preset_id}")
    builder.button(text="◀️ Назад", callback_data="preset_back")
    builder.adjust(1)
    return builder.as_markup()


# ---------------------------------------------------------------------------
# Payment
# ---------------------------------------------------------------------------

def kb_payment_cancel() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отменить оплату", callback_data="payment:cancel")
    return builder.as_markup()


def kb_payment_status() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="◀️ Главное меню", callback_data="menu:main")
    return builder.as_markup()


# ---------------------------------------------------------------------------
# Referral
# ---------------------------------------------------------------------------

def kb_referral_back() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="◀️ Назад", callback_data="menu:main")
    return builder.as_markup()


# ---------------------------------------------------------------------------
# Account
# ---------------------------------------------------------------------------

def kb_account() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📋 Мои подписки", callback_data="account:subscriptions")
    builder.button(text="◀️ Главное меню", callback_data="menu:main")
    builder.adjust(1)
    return builder.as_markup()


def kb_account_subscriptions(has_configs: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if has_configs:
        builder.button(text="🔑 Мои конфигурации", callback_data="account:configs")
    builder.button(text="◀️ Назад", callback_data="menu:account")
    builder.adjust(1)
    return builder.as_markup()


def kb_account_configs_back() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="◀️ Назад", callback_data="account:subscriptions")
    return builder.as_markup()


# ---------------------------------------------------------------------------
# FAQ
# ---------------------------------------------------------------------------

def kb_faq_back() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="◀️ Назад", callback_data="menu:main")
    return builder.as_markup()
