"""States package."""
from aiogram.fsm.state import State, StatesGroup


class AdminStates(StatesGroup):
    """Admin panel states."""

    # Category management
    waiting_category_name = State()
    waiting_category_url = State()
    waiting_category_rename = State()

    # Settings
    waiting_threshold = State()
    waiting_interval = State()
    waiting_product_limit = State()


__all__ = ["AdminStates"]
