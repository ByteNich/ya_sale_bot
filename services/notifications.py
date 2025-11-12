"""Notification service for sending alerts."""
import logging
from typing import Optional

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

from config import settings
from database.models import Product

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for sending notifications to admins."""

    def __init__(self, bot: Bot):
        """
        Initialize notification service.

        Args:
            bot: Telegram bot instance
        """
        self.bot = bot

    async def send_discount_alert(
        self,
        product: Product,
        old_price: Optional[float],
        new_price: float,
        discount_pct: float,
    ):
        """
        Send discount alert to all admins.

        Args:
            product: Product with discount
            old_price: Previous price
            new_price: New price
            discount_pct: Discount percentage
        """
        # Prepare message
        text = "🔥 <b>СКИДКА ОБНАРУЖЕНА!</b> 🔥\n\n"

        text += f"📦 <b>{product.name}</b>\n\n"

        if old_price:
            text += f"💵 Старая цена: <s>{old_price:.0f} ₽</s>\n"
            text += f"💰 Новая цена: <b>{new_price:.0f} ₽</b>\n"
            text += f"📉 Скидка: <b>{discount_pct:.1f}%</b>\n"
            savings = old_price - new_price
            text += f"💸 Экономия: <b>{savings:.0f} ₽</b>\n\n"
        else:
            text += f"💰 Цена: <b>{new_price:.0f} ₽</b>\n"
            if discount_pct > 0:
                text += f"📉 Скидка: <b>{discount_pct:.1f}%</b>\n\n"

        if product.rating:
            text += f"⭐️ Рейтинг: {product.rating}\n"
        if product.reviews_count:
            text += f"💬 Отзывов: {product.reviews_count}\n"

        text += f"\n🔗 <a href='{product.url}'>Перейти к товару</a>"

        # Send to all admins
        for admin_id in settings.admin_list:
            try:
                # Try to send with photo if available
                if product.image_url:
                    try:
                        await self.bot.send_photo(
                            chat_id=admin_id,
                            photo=product.image_url,
                            caption=text,
                        )
                    except TelegramAPIError:
                        # If photo fails, send text only
                        await self.bot.send_message(
                            chat_id=admin_id,
                            text=text,
                            disable_web_page_preview=False,
                        )
                else:
                    await self.bot.send_message(
                        chat_id=admin_id,
                        text=text,
                        disable_web_page_preview=False,
                    )

                logger.info(f"Discount alert sent to admin {admin_id}")

            except TelegramAPIError as e:
                logger.error(f"Failed to send notification to {admin_id}: {e}")

    async def send_system_message(self, message: str):
        """
        Send system message to all admins.

        Args:
            message: Message text
        """
        for admin_id in settings.admin_list:
            try:
                await self.bot.send_message(chat_id=admin_id, text=message)
            except TelegramAPIError as e:
                logger.error(f"Failed to send system message to {admin_id}: {e}")
