"""Admin panel handlers."""
import logging
from datetime import datetime, timedelta
from typing import Optional

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import func, select, delete
from sqlalchemy.orm import selectinload

from bot.keyboards.inline import (
    get_back_kb,
    get_categories_menu_kb,
    get_category_control_kb,
    get_check_interval_kb,
    get_confirm_kb,
    get_discount_threshold_kb,
    get_main_menu_kb,
    get_monitoring_menu_kb,
    get_settings_menu_kb,
    get_statistics_menu_kb,
)
from bot.states import AdminStates
from config import settings
from database.db import get_session
from database.models import BotSettings, Category, PriceHistory, Product
from parser.yandex_market import YandexMarketParser

logger = logging.getLogger(__name__)
router = Router()


# ==================== MAIN MENU ====================


@router.message(Command("start"))
async def cmd_start(message: Message, is_admin: bool):
    """Handle /start command."""
    if not is_admin:
        await message.answer("⛔️ У вас нет доступа к этому боту.")
        return

    await message.answer(
        "🤖 <b>Яндекс.Маркет Бот - Мониторинг Скидок</b>\n\n"
        "Добро пожаловать в панель управления!\n"
        "Бот отслеживает цены на товары и уведомляет о скидках.\n\n"
        "Выберите действие:",
        reply_markup=get_main_menu_kb(),
    )


@router.message(Command("admin"))
async def cmd_admin(message: Message, is_admin: bool):
    """Handle /admin command."""
    if not is_admin:
        await message.answer("⛔️ У вас нет доступа к админ-панели.")
        return

    await message.answer(
        "⚙️ <b>Административная панель</b>\n\n"
        "Управление ботом и мониторингом товаров:",
        reply_markup=get_main_menu_kb(),
    )


@router.callback_query(F.data == "admin:main")
async def show_main_menu(callback: CallbackQuery):
    """Show main admin menu."""
    await callback.message.edit_text(
        "⚙️ <b>Административная панель</b>\n\n"
        "Управление ботом и мониторингом товаров:",
        reply_markup=get_main_menu_kb(),
    )
    await callback.answer()


# ==================== CATEGORIES ====================


@router.callback_query(F.data == "admin:categories")
async def show_categories(callback: CallbackQuery):
    """Show categories list."""
    async with get_session() as session:
        # Get categories with product count
        result = await session.execute(
            select(Category, func.count(Product.id).label("products_count"))
            .outerjoin(Product)
            .group_by(Category.id)
            .order_by(Category.name)
        )
        categories = []
        for cat, count in result.all():
            categories.append({
                "id": cat.id,
                "name": cat.name,
                "is_active": cat.is_active,
                "products_count": count,
            })

    if not categories:
        await callback.message.edit_text(
            "📂 <b>Управление категориями</b>\n\n"
            "Категории не добавлены.\n"
            "Используйте кнопку 'Добавить категорию'.",
            reply_markup=get_categories_menu_kb([]),
        )
    else:
        await callback.message.edit_text(
            f"📂 <b>Управление категориями</b>\n\n"
            f"Всего категорий: {len(categories)}",
            reply_markup=get_categories_menu_kb(categories),
        )
    await callback.answer()


@router.callback_query(F.data.startswith("cat:page:"))
async def categories_pagination(callback: CallbackQuery):
    """Handle categories pagination."""
    page = int(callback.data.split(":")[-1])

    async with get_session() as session:
        result = await session.execute(
            select(Category, func.count(Product.id).label("products_count"))
            .outerjoin(Product)
            .group_by(Category.id)
            .order_by(Category.name)
        )
        categories = []
        for cat, count in result.all():
            categories.append({
                "id": cat.id,
                "name": cat.name,
                "is_active": cat.is_active,
                "products_count": count,
            })

    await callback.message.edit_reply_markup(
        reply_markup=get_categories_menu_kb(categories, page=page)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("cat:view:"))
async def view_category(callback: CallbackQuery):
    """View category details."""
    category_id = int(callback.data.split(":")[-1])

    async with get_session() as session:
        result = await session.execute(
            select(Category, func.count(Product.id).label("products_count"))
            .outerjoin(Product)
            .where(Category.id == category_id)
            .group_by(Category.id)
        )
        row = result.first()

        if not row:
            await callback.answer("❌ Категория не найдена", show_alert=True)
            return

        category, products_count = row

        # Get active products count
        active_result = await session.execute(
            select(func.count(Product.id))
            .where(Product.category_id == category_id, Product.is_available == True)
        )
        active_count = active_result.scalar() or 0

        status = "✅ Активна" if category.is_active else "❌ Приостановлена"
        updated = category.updated_at.strftime("%d.%m.%Y %H:%M") if category.updated_at else "Никогда"

        text = (
            f"📂 <b>{category.name}</b>\n\n"
            f"Статус: {status}\n"
            f"Всего товаров: {products_count}\n"
            f"Доступных: {active_count}\n"
            f"ID категории Яндекс: {category.yandex_category_id or 'Не указан'}\n"
            f"Последнее обновление: {updated}\n"
        )

        await callback.message.edit_text(
            text,
            reply_markup=get_category_control_kb(category.id, category.is_active),
        )
    await callback.answer()


@router.callback_query(F.data == "cat:add")
async def add_category_start(callback: CallbackQuery, state: FSMContext):
    """Start adding new category."""
    # Get available predefined categories
    parser = YandexMarketParser()
    available = parser.get_available_categories()

    text = "➕ <b>Добавление категории</b>\n\n"
    text += "Доступные предустановленные категории:\n\n"

    for key, url in available.items():
        text += f"• <code>{key}</code>\n"

    text += "\n📝 Отправьте название категории из списка или введите свое:"

    await callback.message.edit_text(text, reply_markup=get_back_kb("admin:categories"))
    await state.set_state(AdminStates.waiting_category_name)
    await callback.answer()


@router.callback_query(F.data.startswith("cat:toggle:"))
async def toggle_category(callback: CallbackQuery):
    """Toggle category active status."""
    category_id = int(callback.data.split(":")[-1])

    async with get_session() as session:
        result = await session.execute(
            select(Category).where(Category.id == category_id)
        )
        category = result.scalar_one_or_none()

        if not category:
            await callback.answer("❌ Категория не найдена", show_alert=True)
            return

        category.is_active = not category.is_active
        await session.commit()

        status = "активирована" if category.is_active else "приостановлена"
        await callback.answer(f"✅ Категория {status}")

        # Refresh view
        await view_category(callback)


@router.callback_query(F.data.startswith("cat:update:"))
async def update_category_products(callback: CallbackQuery):
    """Update products in category."""
    category_id = int(callback.data.split(":")[-1])

    await callback.answer("🔄 Обновление товаров...", show_alert=True)

    async with get_session() as session:
        result = await session.execute(
            select(Category).where(Category.id == category_id)
        )
        category = result.scalar_one_or_none()

        if not category:
            return

        # Parse products
        parser = YandexMarketParser()
        if category.yandex_category_id in parser.CATEGORIES:
            products_data = await parser.get_products_by_category(
                category.yandex_category_id, limit=50
            )
        else:
            products_data = []

        # Save products
        added = 0
        updated = 0
        for prod_data in products_data:
            result = await session.execute(
                select(Product).where(
                    Product.yandex_product_id == prod_data["yandex_product_id"]
                )
            )
            existing = result.scalar_one_or_none()

            if existing:
                # Update existing
                if existing.current_price != prod_data["current_price"]:
                    # Price changed - save to history
                    history = PriceHistory(
                        product_id=existing.id,
                        price=prod_data["current_price"],
                        discount_percentage=prod_data.get("discount_percentage", 0),
                    )
                    session.add(history)

                existing.current_price = prod_data["current_price"]
                existing.previous_price = prod_data.get("previous_price")
                existing.discount_percentage = prod_data.get("discount_percentage", 0)
                existing.last_checked = datetime.utcnow()
                updated += 1
            else:
                # Add new
                product = Product(
                    category_id=category.id,
                    name=prod_data["name"],
                    yandex_product_id=prod_data["yandex_product_id"],
                    url=prod_data["url"],
                    image_url=prod_data.get("image_url"),
                    current_price=prod_data["current_price"],
                    previous_price=prod_data.get("previous_price"),
                    discount_percentage=prod_data.get("discount_percentage", 0),
                    rating=prod_data.get("rating"),
                    reviews_count=prod_data.get("reviews_count", 0),
                )
                session.add(product)
                added += 1

        category.updated_at = datetime.utcnow()
        await session.commit()

    await callback.message.answer(
        f"✅ Обновление завершено!\n\n"
        f"Добавлено новых: {added}\n"
        f"Обновлено: {updated}"
    )


# ==================== SETTINGS ====================


@router.callback_query(F.data == "admin:settings")
async def show_settings(callback: CallbackQuery):
    """Show settings menu."""
    async with get_session() as session:
        # Get current settings
        result = await session.execute(
            select(BotSettings).where(BotSettings.key == "check_interval")
        )
        interval_setting = result.scalar_one_or_none()
        interval = int(interval_setting.value) if interval_setting else settings.CHECK_INTERVAL

        result = await session.execute(
            select(BotSettings).where(BotSettings.key == "discount_threshold")
        )
        threshold_setting = result.scalar_one_or_none()
        threshold = int(threshold_setting.value) if threshold_setting else settings.DISCOUNT_THRESHOLD

    text = (
        "⚙️ <b>Настройки бота</b>\n\n"
        f"⏱ Интервал проверки: {interval // 60} мин\n"
        f"💯 Порог скидки: {threshold}%\n\n"
        "Выберите параметр для изменения:"
    )

    await callback.message.edit_text(text, reply_markup=get_settings_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "settings:interval")
async def settings_interval(callback: CallbackQuery):
    """Show interval selection."""
    await callback.message.edit_text(
        "⏱ <b>Интервал проверки цен</b>\n\n"
        "Выберите как часто проверять цены:",
        reply_markup=get_check_interval_kb(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("settings:interval:set:"))
async def set_interval(callback: CallbackQuery):
    """Set check interval."""
    interval = int(callback.data.split(":")[-1])

    async with get_session() as session:
        result = await session.execute(
            select(BotSettings).where(BotSettings.key == "check_interval")
        )
        setting = result.scalar_one_or_none()

        if setting:
            setting.value = str(interval)
        else:
            setting = BotSettings(
                key="check_interval",
                value=str(interval),
                description="Интервал проверки цен в секундах",
            )
            session.add(setting)

        await session.commit()

    await callback.answer(f"✅ Интервал установлен: {interval // 60} мин")
    await show_settings(callback)


@router.callback_query(F.data == "settings:threshold")
async def settings_threshold(callback: CallbackQuery):
    """Show threshold selection."""
    await callback.message.edit_text(
        "💯 <b>Порог скидки для уведомлений</b>\n\n"
        "Выберите минимальный процент скидки:",
        reply_markup=get_discount_threshold_kb(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("settings:threshold:set:"))
async def set_threshold(callback: CallbackQuery):
    """Set discount threshold."""
    threshold = int(callback.data.split(":")[-1])

    async with get_session() as session:
        result = await session.execute(
            select(BotSettings).where(BotSettings.key == "discount_threshold")
        )
        setting = result.scalar_one_or_none()

        if setting:
            setting.value = str(threshold)
        else:
            setting = BotSettings(
                key="discount_threshold",
                value=str(threshold),
                description="Минимальный процент скидки для уведомлений",
            )
            session.add(setting)

        await session.commit()

    await callback.answer(f"✅ Порог установлен: {threshold}%")
    await show_settings(callback)


# ==================== MONITORING ====================


@router.callback_query(F.data == "admin:monitoring")
async def show_monitoring(callback: CallbackQuery):
    """Show monitoring menu."""
    # Get monitoring status from bot data
    bot_data = callback.bot.get("monitor_running", False)
    status = "✅ Запущен" if bot_data else "❌ Остановлен"

    text = (
        "🔍 <b>Мониторинг цен</b>\n\n"
        f"Статус: {status}\n\n"
        "Управление автоматическим мониторингом:"
    )

    await callback.message.edit_text(text, reply_markup=get_monitoring_menu_kb())
    await callback.answer()


# ==================== STATISTICS ====================


@router.callback_query(F.data == "admin:statistics")
async def show_statistics(callback: CallbackQuery):
    """Show statistics menu."""
    await callback.message.edit_text(
        "📊 <b>Статистика</b>\n\n"
        "Выберите раздел:",
        reply_markup=get_statistics_menu_kb(),
    )
    await callback.answer()


@router.callback_query(F.data == "stats:general")
async def stats_general(callback: CallbackQuery):
    """Show general statistics."""
    async with get_session() as session:
        # Total categories
        cat_result = await session.execute(select(func.count(Category.id)))
        total_categories = cat_result.scalar() or 0

        # Active categories
        active_cat_result = await session.execute(
            select(func.count(Category.id)).where(Category.is_active == True)
        )
        active_categories = active_cat_result.scalar() or 0

        # Total products
        prod_result = await session.execute(select(func.count(Product.id)))
        total_products = prod_result.scalar() or 0

        # Products with discounts
        discount_result = await session.execute(
            select(func.count(Product.id)).where(Product.discount_percentage > 0)
        )
        discounted_products = discount_result.scalar() or 0

        # Average discount
        avg_discount_result = await session.execute(
            select(func.avg(Product.discount_percentage)).where(
                Product.discount_percentage > 0
            )
        )
        avg_discount = avg_discount_result.scalar() or 0

    text = (
        "📊 <b>Общая статистика</b>\n\n"
        f"📂 Категорий: {total_categories}\n"
        f"✅ Активных: {active_categories}\n\n"
        f"🛍 Товаров: {total_products}\n"
        f"💰 Со скидками: {discounted_products}\n"
        f"📉 Средняя скидка: {avg_discount:.1f}%\n"
    )

    await callback.message.edit_text(text, reply_markup=get_back_kb("admin:statistics"))
    await callback.answer()


@router.callback_query(F.data == "admin:top_discounts")
async def show_top_discounts(callback: CallbackQuery):
    """Show top discounted products."""
    async with get_session() as session:
        result = await session.execute(
            select(Product)
            .where(Product.discount_percentage > 0)
            .order_by(Product.discount_percentage.desc())
            .limit(10)
        )
        products = result.scalars().all()

    if not products:
        await callback.answer("💰 Нет товаров со скидками", show_alert=True)
        return

    text = "💰 <b>Топ 10 скидок</b>\n\n"
    for i, prod in enumerate(products, 1):
        text += (
            f"{i}. <b>{prod.name[:50]}...</b>\n"
            f"   💵 {prod.current_price:.0f} ₽"
        )
        if prod.previous_price:
            text += f" (было {prod.previous_price:.0f} ₽)"
        text += f"\n   📉 Скидка: {prod.discount_percentage:.1f}%\n"
        text += f"   🔗 <a href='{prod.url}'>Смотреть</a>\n\n"

    await callback.message.edit_text(text, reply_markup=get_back_kb("admin:main"), disable_web_page_preview=True)
    await callback.answer()


@router.callback_query(F.data == "admin:help")
async def show_help(callback: CallbackQuery):
    """Show help information."""
    text = (
        "❓ <b>Помощь</b>\n\n"
        "<b>Команды:</b>\n"
        "/start - Главное меню\n"
        "/admin - Админ панель\n\n"
        "<b>Описание функций:</b>\n\n"
        "📂 <b>Категории</b>\n"
        "Управление категориями товаров для мониторинга\n\n"
        "📊 <b>Статистика</b>\n"
        "Просмотр статистики по товарам и скидкам\n\n"
        "⚙️ <b>Настройки</b>\n"
        "Интервал проверки и порог скидок\n\n"
        "🔍 <b>Мониторинг</b>\n"
        "Управление автоматической проверкой цен\n\n"
        "Бот автоматически уведомит вас о новых скидках!"
    )

    await callback.message.edit_text(text, reply_markup=get_back_kb("admin:main"))
    await callback.answer()


@router.callback_query(F.data == "cancel")
async def cancel_action(callback: CallbackQuery, state: FSMContext):
    """Cancel current action."""
    await state.clear()
    await callback.answer("❌ Отменено")
    await show_main_menu(callback)


# ==================== MONITORING CONTROLS ====================


@router.callback_query(F.data == "monitor:start")
async def monitor_start(callback: CallbackQuery, monitor):
    """Start price monitoring."""
    if not monitor:
        await callback.answer("❌ Монитор не инициализирован", show_alert=True)
        return

    if monitor.is_running:
        await callback.answer("⚠️ Мониторинг уже запущен", show_alert=True)
        return

    await monitor.start()
    await callback.answer("✅ Мониторинг запущен!")
    await show_monitoring(callback)


@router.callback_query(F.data == "monitor:stop")
async def monitor_stop(callback: CallbackQuery, monitor):
    """Stop price monitoring."""
    if not monitor:
        await callback.answer("❌ Монитор не инициализирован", show_alert=True)
        return

    if not monitor.is_running:
        await callback.answer("⚠️ Мониторинг уже остановлен", show_alert=True)
        return

    await monitor.stop()
    await callback.answer("✅ Мониторинг остановлен!")
    await show_monitoring(callback)


@router.callback_query(F.data == "monitor:status")
async def monitor_status(callback: CallbackQuery, monitor):
    """Show monitoring status."""
    if not monitor:
        await callback.answer("❌ Монитор не инициализирован", show_alert=True)
        return

    status = "✅ Работает" if monitor.is_running else "❌ Остановлен"
    interval = monitor._check_interval

    text = (
        "🔍 <b>Статус мониторинга</b>\n\n"
        f"Статус: {status}\n"
        f"Интервал проверки: {interval // 60} мин ({interval} сек)\n"
    )

    await callback.message.edit_text(text, reply_markup=get_back_kb("admin:monitoring"))
    await callback.answer()


@router.callback_query(F.data == "monitor:force_check")
async def monitor_force_check(callback: CallbackQuery, monitor):
    """Force immediate price check."""
    if not monitor:
        await callback.answer("❌ Монитор не инициализирован", show_alert=True)
        return

    await callback.answer("🔄 Запуск проверки цен...", show_alert=True)
    await monitor.force_check()
    await callback.message.answer("✅ Проверка цен завершена!")


@router.callback_query(F.data == "admin:force_update")
async def force_update(callback: CallbackQuery, monitor):
    """Force update all categories."""
    await callback.answer("🔄 Запуск обновления...", show_alert=True)
    if monitor:
        await monitor.force_check()
        await callback.message.answer("✅ Обновление завершено!")
    else:
        await callback.answer("❌ Монитор не доступен", show_alert=True)


# ==================== CATEGORY FSM HANDLERS ====================


@router.message(StateFilter(AdminStates.waiting_category_name))
async def process_category_name(message: Message, state: FSMContext):
    """Process category name input."""
    category_name = message.text.strip()

    parser = YandexMarketParser()
    available = parser.get_available_categories()

    # Check if it's a predefined category
    if category_name in available:
        yandex_id = category_name
        url_path = available[category_name]
        display_name = category_name.replace("_", " ").title()
    else:
        # Custom category
        yandex_id = None
        url_path = None
        display_name = category_name

    # Save to database
    async with get_session() as session:
        # Check if category already exists
        result = await session.execute(
            select(Category).where(Category.name == display_name)
        )
        existing = result.scalar_one_or_none()

        if existing:
            await message.answer("❌ Категория с таким названием уже существует!")
            await state.clear()
            return

        category = Category(
            name=display_name,
            yandex_category_id=yandex_id,
            url_path=url_path,
            is_active=True,
        )
        session.add(category)
        await session.commit()

    await message.answer(
        f"✅ Категория '<b>{display_name}</b>' успешно добавлена!",
        reply_markup=get_back_kb("admin:categories"),
    )
    await state.clear()
