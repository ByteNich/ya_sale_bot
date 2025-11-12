"""Inline keyboards for admin panel."""
from typing import List, Optional

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_main_menu_kb() -> InlineKeyboardMarkup:
    """
    Get main admin menu keyboard.

    Returns:
        InlineKeyboardMarkup with main menu buttons
    """
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="📂 Управление категориями", callback_data="admin:categories")
    )
    builder.row(
        InlineKeyboardButton(text="📊 Статистика", callback_data="admin:statistics"),
        InlineKeyboardButton(text="⚙️ Настройки", callback_data="admin:settings"),
    )
    builder.row(
        InlineKeyboardButton(text="🔍 Мониторинг", callback_data="admin:monitoring"),
        InlineKeyboardButton(text="💰 Лучшие скидки", callback_data="admin:top_discounts"),
    )
    builder.row(
        InlineKeyboardButton(text="🔄 Обновить сейчас", callback_data="admin:force_update"),
        InlineKeyboardButton(text="📝 Логи", callback_data="admin:logs"),
    )
    builder.row(
        InlineKeyboardButton(text="❓ Помощь", callback_data="admin:help")
    )

    return builder.as_markup()


def get_categories_menu_kb(categories: List[dict], page: int = 0, per_page: int = 10) -> InlineKeyboardMarkup:
    """
    Get categories management menu keyboard.

    Args:
        categories: List of category dictionaries
        page: Current page number
        per_page: Categories per page

    Returns:
        InlineKeyboardMarkup with categories
    """
    builder = InlineKeyboardBuilder()

    start_idx = page * per_page
    end_idx = start_idx + per_page
    page_categories = categories[start_idx:end_idx]

    # Category buttons
    for cat in page_categories:
        status_icon = "✅" if cat.get("is_active") else "❌"
        products_count = cat.get("products_count", 0)
        builder.row(
            InlineKeyboardButton(
                text=f"{status_icon} {cat['name']} ({products_count} товаров)",
                callback_data=f"cat:view:{cat['id']}"
            )
        )

    # Pagination
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"cat:page:{page - 1}"))
    if end_idx < len(categories):
        nav_buttons.append(InlineKeyboardButton(text="➡️ Вперёд", callback_data=f"cat:page:{page + 1}"))

    if nav_buttons:
        builder.row(*nav_buttons)

    # Action buttons
    builder.row(
        InlineKeyboardButton(text="➕ Добавить категорию", callback_data="cat:add"),
        InlineKeyboardButton(text="🔄 Обновить все", callback_data="cat:refresh_all"),
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Главное меню", callback_data="admin:main")
    )

    return builder.as_markup()


def get_category_control_kb(category_id: int, is_active: bool) -> InlineKeyboardMarkup:
    """
    Get category control keyboard.

    Args:
        category_id: Category ID
        is_active: Whether category is active

    Returns:
        InlineKeyboardMarkup with category controls
    """
    builder = InlineKeyboardBuilder()

    # Toggle active status
    toggle_text = "⏸ Приостановить" if is_active else "▶️ Активировать"
    builder.row(
        InlineKeyboardButton(text=toggle_text, callback_data=f"cat:toggle:{category_id}")
    )

    # Actions
    builder.row(
        InlineKeyboardButton(text="🔄 Обновить товары", callback_data=f"cat:update:{category_id}"),
        InlineKeyboardButton(text="📊 Статистика", callback_data=f"cat:stats:{category_id}"),
    )
    builder.row(
        InlineKeyboardButton(text="📝 Изменить название", callback_data=f"cat:rename:{category_id}"),
        InlineKeyboardButton(text="🔗 Изменить URL", callback_data=f"cat:change_url:{category_id}"),
    )
    builder.row(
        InlineKeyboardButton(text="🗑 Удалить категорию", callback_data=f"cat:delete_confirm:{category_id}")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 К категориям", callback_data="admin:categories")
    )

    return builder.as_markup()


def get_settings_menu_kb() -> InlineKeyboardMarkup:
    """
    Get settings menu keyboard.

    Returns:
        InlineKeyboardMarkup with settings options
    """
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="⏱ Интервал проверки", callback_data="settings:interval"),
        InlineKeyboardButton(text="💯 Порог скидки", callback_data="settings:threshold"),
    )
    builder.row(
        InlineKeyboardButton(text="🔔 Уведомления", callback_data="settings:notifications"),
        InlineKeyboardButton(text="📊 Лимит товаров", callback_data="settings:product_limit"),
    )
    builder.row(
        InlineKeyboardButton(text="🗄 Очистить историю", callback_data="settings:clear_history_confirm"),
        InlineKeyboardButton(text="🗑 Удалить неактивные", callback_data="settings:cleanup_confirm"),
    )
    builder.row(
        InlineKeyboardButton(text="📤 Экспорт данных", callback_data="settings:export"),
        InlineKeyboardButton(text="📥 Импорт категорий", callback_data="settings:import"),
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Главное меню", callback_data="admin:main")
    )

    return builder.as_markup()


def get_monitoring_menu_kb() -> InlineKeyboardMarkup:
    """
    Get monitoring menu keyboard.

    Returns:
        InlineKeyboardMarkup with monitoring options
    """
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="▶️ Запустить", callback_data="monitor:start"),
        InlineKeyboardButton(text="⏸ Остановить", callback_data="monitor:stop"),
    )
    builder.row(
        InlineKeyboardButton(text="📊 Статус", callback_data="monitor:status"),
        InlineKeyboardButton(text="⏱ Последнее обновление", callback_data="monitor:last_update"),
    )
    builder.row(
        InlineKeyboardButton(text="🔄 Обновить сейчас", callback_data="monitor:force_check"),
        InlineKeyboardButton(text="📈 Активность", callback_data="monitor:activity"),
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Главное меню", callback_data="admin:main")
    )

    return builder.as_markup()


def get_statistics_menu_kb() -> InlineKeyboardMarkup:
    """
    Get statistics menu keyboard.

    Returns:
        InlineKeyboardMarkup with statistics options
    """
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="📊 Общая статистика", callback_data="stats:general"),
        InlineKeyboardButton(text="📈 По категориям", callback_data="stats:by_category"),
    )
    builder.row(
        InlineKeyboardButton(text="💰 Топ скидок", callback_data="stats:top_discounts"),
        InlineKeyboardButton(text="📉 История цен", callback_data="stats:price_history"),
    )
    builder.row(
        InlineKeyboardButton(text="🏆 Лучшие предложения", callback_data="stats:best_deals"),
        InlineKeyboardButton(text="⭐️ Популярные товары", callback_data="stats:popular"),
    )
    builder.row(
        InlineKeyboardButton(text="📅 За сегодня", callback_data="stats:today"),
        InlineKeyboardButton(text="📅 За неделю", callback_data="stats:week"),
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Главное меню", callback_data="admin:main")
    )

    return builder.as_markup()


def get_confirm_kb(action: str, data: Optional[str] = None) -> InlineKeyboardMarkup:
    """
    Get confirmation keyboard.

    Args:
        action: Action to confirm
        data: Additional data for callback

    Returns:
        InlineKeyboardMarkup with confirmation buttons
    """
    builder = InlineKeyboardBuilder()

    callback_data = f"confirm:{action}"
    if data:
        callback_data += f":{data}"

    builder.row(
        InlineKeyboardButton(text="✅ Да", callback_data=callback_data),
        InlineKeyboardButton(text="❌ Нет", callback_data="cancel"),
    )

    return builder.as_markup()


def get_back_kb(callback_data: str = "admin:main") -> InlineKeyboardMarkup:
    """
    Get back button keyboard.

    Args:
        callback_data: Callback data for back button

    Returns:
        InlineKeyboardMarkup with back button
    """
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data=callback_data))
    return builder.as_markup()


def get_discount_threshold_kb() -> InlineKeyboardMarkup:
    """
    Get discount threshold selection keyboard.

    Returns:
        InlineKeyboardMarkup with threshold options
    """
    builder = InlineKeyboardBuilder()

    thresholds = [5, 10, 15, 20, 25, 30, 40, 50]

    for i in range(0, len(thresholds), 2):
        buttons = [
            InlineKeyboardButton(
                text=f"{thresholds[i]}%",
                callback_data=f"settings:threshold:set:{thresholds[i]}"
            )
        ]
        if i + 1 < len(thresholds):
            buttons.append(
                InlineKeyboardButton(
                    text=f"{thresholds[i + 1]}%",
                    callback_data=f"settings:threshold:set:{thresholds[i + 1]}"
                )
            )
        builder.row(*buttons)

    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="admin:settings")
    )

    return builder.as_markup()


def get_check_interval_kb() -> InlineKeyboardMarkup:
    """
    Get check interval selection keyboard.

    Returns:
        InlineKeyboardMarkup with interval options
    """
    builder = InlineKeyboardBuilder()

    intervals = [
        ("1 минута", 60),
        ("2 минуты", 120),
        ("5 минут", 300),
        ("10 минут", 600),
        ("30 минут", 1800),
        ("1 час", 3600),
    ]

    for text, seconds in intervals:
        builder.row(
            InlineKeyboardButton(
                text=text,
                callback_data=f"settings:interval:set:{seconds}"
            )
        )

    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="admin:settings")
    )

    return builder.as_markup()
