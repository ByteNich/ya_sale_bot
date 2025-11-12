"""Middlewares package."""
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User

from config import settings


class AdminMiddleware(BaseMiddleware):
    """Middleware to check if user is admin."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        """Check if user is admin."""
        user: User = data.get("event_from_user")

        if user and user.id in settings.admin_list:
            data["is_admin"] = True
        else:
            data["is_admin"] = False

        return await handler(event, data)


class MonitorMiddleware(BaseMiddleware):
    """Middleware to inject monitor into handlers."""

    def __init__(self, monitor):
        """Initialize with monitor instance."""
        super().__init__()
        self.monitor = monitor

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        """Inject monitor into data."""
        data["monitor"] = self.monitor
        return await handler(event, data)


__all__ = ["AdminMiddleware", "MonitorMiddleware"]
