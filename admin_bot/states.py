"""FSM states for the admin bot."""

from aiogram.fsm.state import State, StatesGroup


class AddPlanSG(StatesGroup):
    name = State()
    type = State()
    price = State()
    duration = State()
    traffic = State()
    description = State()


class EditPlanSG(StatesGroup):
    field = State()
    value = State()


class AddProviderSG(StatesGroup):
    name = State()
    location = State()
    server_ip = State()
    supports_whitelist = State()


class AddPresetSG(StatesGroup):
    provider_id = State()
    ram_gb = State()
    cpu_count = State()
    price = State()


class AddRequisiteSG(StatesGroup):
    type = State()
    value = State()
    holder_name = State()


class UserBonusSG(StatesGroup):
    amount = State()


class RejectPaymentSG(StatesGroup):
    reason = State()


class EditFAQSG(StatesGroup):
    text = State()


class AddAdminSG(StatesGroup):
    admin_id = State()
