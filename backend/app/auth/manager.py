# User Manager for FastAPI Users.
import uuid
import logging
from fastapi import Depends, Request
from fastapi_users import BaseUserManager, UUIDIDMixin
from app.models import User
from app.auth.db import get_user_db
from app.config import config
from app.utils.emails import send_reset_password_email, send_verification_email

logger = logging.getLogger(__name__)
SECRET = config.SECRET_KEY


class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    reset_password_token_secret = SECRET
    verification_token_secret = SECRET

    # Token validity (3 days)
    verification_token_lifetime_seconds = 60 * 60 * 24 * 3  

    async def on_after_register(self, user: User, request: Request | None = None):
        logger.info(f" User {user.email} has registered.")
        await self.request_verify(user, request)

    async def on_after_forgot_password(self, user: User, token: str, request: Request | None = None):
        send_reset_password_email(None, user.email, token)
        logger.info(f" Password reset email sent to {user.email}")

    async def on_after_request_verify(self, user: User, token: str, request: Request | None = None):
        send_verification_email(None, user.email, token)
        logger.info(f" Verification email sent to {user.email}")

    async def on_after_verify(self, user: User, request: Request | None = None):
        logger.info(f" User {user.email} has been verified.")
        await self.user_db.update(user, {"is_verified": True})

async def get_user_manager(user_db=Depends(get_user_db)):
    yield UserManager(user_db)
