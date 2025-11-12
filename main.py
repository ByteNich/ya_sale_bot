"""Main bot application."""
import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot.handlers import admin
from bot.middlewares import AdminMiddleware, MonitorMiddleware
from config import settings
from database.db import init_db
from services.monitor import PriceMonitor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("bot.log"),
    ],
)

logger = logging.getLogger(__name__)


async def main():
    """Main application entry point."""
    logger.info("Starting Yandex Market Discount Bot...")

    # Initialize database
    try:
        await init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        sys.exit(1)

    # Initialize bot and dispatcher
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    # Initialize price monitor
    monitor = PriceMonitor(bot)

    # Register middlewares
    admin.router.message.middleware(AdminMiddleware())
    admin.router.callback_query.middleware(AdminMiddleware())
    admin.router.message.middleware(MonitorMiddleware(monitor))
    admin.router.callback_query.middleware(MonitorMiddleware(monitor))

    # Register routers
    dp.include_router(admin.router)

    # Start price monitoring
    await monitor.start()
    logger.info("Price monitoring started")

    # Start polling
    try:
        logger.info("Bot started successfully")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        # Cleanup
        await monitor.stop()
        await bot.session.close()
        logger.info("Bot stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)
