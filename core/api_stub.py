"""
Future API integration stub.

When the backend API is ready, implement this class to replace JSONStorage.
All method signatures are identical to BaseStorage so the swap is seamless.
"""

from __future__ import annotations

from core.models import (
    User,
    SubscriptionPlan,
    Provider,
    Preset,
    Subscription,
    Requisite,
    Payment,
    Referral,
    Settings,
)
from core.storage import BaseStorage


class APIStorage(BaseStorage):
    """
    Skeleton implementation – replace each ``...`` with real HTTP calls
    (e.g. using ``aiohttp`` or ``httpx``) to the backend REST API.
    """

    def __init__(self, base_url: str, api_key: str) -> None:
        self._base_url = base_url
        self._api_key = api_key

    # ------------------------------------------------------------------
    # Users
    # ------------------------------------------------------------------

    async def get_user(self, telegram_id: int) -> User | None:
        raise NotImplementedError

    async def save_user(self, user: User) -> None:
        raise NotImplementedError

    async def get_all_users(self) -> list[User]:
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Subscription plans
    # ------------------------------------------------------------------

    async def get_subscription_plans(self, active_only: bool = True) -> list[SubscriptionPlan]:
        raise NotImplementedError

    async def get_subscription_plan(self, plan_id: str) -> SubscriptionPlan | None:
        raise NotImplementedError

    async def save_subscription_plan(self, plan: SubscriptionPlan) -> None:
        raise NotImplementedError

    async def delete_subscription_plan(self, plan_id: str) -> None:
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Providers
    # ------------------------------------------------------------------

    async def get_providers(self, active_only: bool = True) -> list[Provider]:
        raise NotImplementedError

    async def get_provider(self, provider_id: str) -> Provider | None:
        raise NotImplementedError

    async def save_provider(self, provider: Provider) -> None:
        raise NotImplementedError

    async def delete_provider(self, provider_id: str) -> None:
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Presets
    # ------------------------------------------------------------------

    async def get_presets(self, provider_id: str | None = None, active_only: bool = True) -> list[Preset]:
        raise NotImplementedError

    async def get_preset(self, preset_id: str) -> Preset | None:
        raise NotImplementedError

    async def save_preset(self, preset: Preset) -> None:
        raise NotImplementedError

    async def delete_preset(self, preset_id: str) -> None:
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Subscriptions
    # ------------------------------------------------------------------

    async def get_user_subscriptions(self, user_id: int, active_only: bool = False) -> list[Subscription]:
        raise NotImplementedError

    async def get_subscription(self, subscription_id: str) -> Subscription | None:
        raise NotImplementedError

    async def save_subscription(self, subscription: Subscription) -> None:
        raise NotImplementedError

    async def get_all_subscriptions(self, active_only: bool = False) -> list[Subscription]:
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Requisites
    # ------------------------------------------------------------------

    async def get_requisites(self, active_only: bool = True) -> list[Requisite]:
        raise NotImplementedError

    async def get_requisite(self, requisite_id: str) -> Requisite | None:
        raise NotImplementedError

    async def save_requisite(self, requisite: Requisite) -> None:
        raise NotImplementedError

    async def delete_requisite(self, requisite_id: str) -> None:
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Payments
    # ------------------------------------------------------------------

    async def get_payments(self, status: str | None = None) -> list[Payment]:
        raise NotImplementedError

    async def get_payment(self, payment_id: str) -> Payment | None:
        raise NotImplementedError

    async def save_payment(self, payment: Payment) -> None:
        raise NotImplementedError

    async def get_user_payments(self, user_id: int) -> list[Payment]:
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Referrals
    # ------------------------------------------------------------------

    async def get_referral_by_code(self, code: str) -> User | None:
        raise NotImplementedError

    async def save_referral(self, referral: Referral) -> None:
        raise NotImplementedError

    async def get_referrals_by_referrer(self, referrer_id: int) -> list[Referral]:
        raise NotImplementedError

    async def get_referral_by_referred(self, referred_id: int) -> Referral | None:
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------

    async def get_settings(self) -> Settings:
        raise NotImplementedError

    async def save_settings(self, settings: Settings) -> None:
        raise NotImplementedError
