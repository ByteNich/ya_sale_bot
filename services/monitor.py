"""Price monitoring service."""
import asyncio
import logging
from datetime import datetime
from typing import Optional

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from config import settings
from database.db import get_session
from database.models import BotSettings, Category, PriceHistory, Product
from parser.yandex_market import YandexMarketParser
from services.notifications import NotificationService

logger = logging.getLogger(__name__)


class PriceMonitor:
    """Service for monitoring price changes."""

    def __init__(self, bot: Bot):
        """
        Initialize price monitor.

        Args:
            bot: Telegram bot instance
        """
        self.bot = bot
        self.scheduler = AsyncIOScheduler()
        self.parser = YandexMarketParser()
        self.notification_service = NotificationService(bot)
        self.is_running = False
        self._check_interval = settings.CHECK_INTERVAL

    async def start(self):
        """Start price monitoring."""
        if self.is_running:
            logger.warning("Monitor is already running")
            return

        # Get check interval from database
        async with get_session() as session:
            result = await session.execute(
                select(BotSettings).where(BotSettings.key == "check_interval")
            )
            setting = result.scalar_one_or_none()
            if setting:
                self._check_interval = int(setting.value)

        self.scheduler.add_job(
            self._check_prices,
            "interval",
            seconds=self._check_interval,
            id="price_check",
            replace_existing=True,
        )
        self.scheduler.start()
        self.is_running = True
        logger.info(f"Price monitor started (interval: {self._check_interval}s)")

    async def stop(self):
        """Stop price monitoring."""
        if not self.is_running:
            logger.warning("Monitor is not running")
            return

        self.scheduler.shutdown()
        self.is_running = False
        logger.info("Price monitor stopped")

    async def force_check(self):
        """Force immediate price check."""
        logger.info("Forcing price check...")
        await self._check_prices()

    async def _check_prices(self):
        """Check prices for all active categories."""
        logger.info("Starting price check...")

        try:
            async with get_session() as session:
                # Get active categories
                result = await session.execute(
                    select(Category).where(Category.is_active == True)
                )
                categories = result.scalars().all()

                if not categories:
                    logger.info("No active categories to monitor")
                    return

                total_updated = 0
                total_new = 0
                total_discounts = 0

                for category in categories:
                    updated, new, discounts = await self._check_category(category, session)
                    total_updated += updated
                    total_new += new
                    total_discounts += discounts

                    # Small delay between categories
                    await asyncio.sleep(2)

                await session.commit()

                logger.info(
                    f"Price check completed: {total_new} new, {total_updated} updated, "
                    f"{total_discounts} discounts found"
                )

        except Exception as e:
            logger.error(f"Error during price check: {e}", exc_info=True)

    async def _check_category(self, category: Category, session) -> tuple[int, int, int]:
        """
        Check prices for a category.

        Args:
            category: Category to check
            session: Database session

        Returns:
            Tuple of (updated_count, new_count, discount_count)
        """
        logger.info(f"Checking category: {category.name}")

        try:
            # Parse products
            if category.yandex_category_id in self.parser.CATEGORIES:
                products_data = await self.parser.get_products_by_category(
                    category.yandex_category_id, limit=50
                )
            elif category.url_path:
                products_data = await self.parser.parse_category_page(
                    category.url_path, limit=50
                )
            else:
                logger.warning(f"Category {category.name} has no URL configured")
                return 0, 0, 0

            if not products_data:
                logger.warning(f"No products found for category {category.name}")
                return 0, 0, 0

            # Get discount threshold
            threshold_result = await session.execute(
                select(BotSettings).where(BotSettings.key == "discount_threshold")
            )
            threshold_setting = threshold_result.scalar_one_or_none()
            discount_threshold = (
                int(threshold_setting.value)
                if threshold_setting
                else settings.DISCOUNT_THRESHOLD
            )

            updated_count = 0
            new_count = 0
            discount_count = 0

            for prod_data in products_data:
                if not prod_data.get("yandex_product_id"):
                    continue

                # Check if product exists
                result = await session.execute(
                    select(Product).where(
                        Product.yandex_product_id == prod_data["yandex_product_id"]
                    )
                )
                existing = result.scalar_one_or_none()

                if existing:
                    # Check for price change
                    old_price = existing.current_price
                    new_price = prod_data["current_price"]

                    if old_price != new_price:
                        # Calculate discount
                        discount_pct = 0
                        if new_price < old_price:
                            discount_pct = round(((old_price - new_price) / old_price) * 100, 2)

                        # Save price history
                        history = PriceHistory(
                            product_id=existing.id,
                            price=new_price,
                            discount_percentage=discount_pct,
                        )
                        session.add(history)

                        # Update product
                        existing.previous_price = old_price
                        existing.current_price = new_price
                        existing.discount_percentage = discount_pct
                        existing.last_checked = datetime.utcnow()

                        updated_count += 1

                        # Send notification if discount is significant
                        if discount_pct >= discount_threshold:
                            await self.notification_service.send_discount_alert(
                                product=existing,
                                old_price=old_price,
                                new_price=new_price,
                                discount_pct=discount_pct,
                            )
                            discount_count += 1
                            logger.info(
                                f"Discount alert sent for {existing.name}: "
                                f"{discount_pct}% off"
                            )
                    else:
                        # Just update last checked time
                        existing.last_checked = datetime.utcnow()

                else:
                    # Add new product
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
                    new_count += 1

                    # Send notification for new product with good discount
                    if product.discount_percentage >= discount_threshold:
                        # We need to flush to get the ID
                        await session.flush()
                        await self.notification_service.send_discount_alert(
                            product=product,
                            old_price=product.previous_price,
                            new_price=product.current_price,
                            discount_pct=product.discount_percentage,
                        )
                        discount_count += 1

            # Update category timestamp
            category.updated_at = datetime.utcnow()

            logger.info(
                f"Category {category.name}: {new_count} new, {updated_count} updated, "
                f"{discount_count} discounts"
            )

            return updated_count, new_count, discount_count

        except Exception as e:
            logger.error(f"Error checking category {category.name}: {e}", exc_info=True)
            return 0, 0, 0

    async def update_interval(self, new_interval: int):
        """
        Update check interval.

        Args:
            new_interval: New interval in seconds
        """
        self._check_interval = new_interval

        if self.is_running:
            # Reschedule job
            self.scheduler.reschedule_job(
                "price_check", trigger="interval", seconds=new_interval
            )
            logger.info(f"Check interval updated to {new_interval}s")
