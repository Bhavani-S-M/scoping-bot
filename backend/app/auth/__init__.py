"""
Auth package initializer.
"""

from .router import router, fastapi_users
from .manager import get_user_manager, UserManager

from .import router, db, manager
__all__ = ["router", "db", "manager"]
