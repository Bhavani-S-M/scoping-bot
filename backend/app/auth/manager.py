import uuid
import logging
from fastapi import Depends, Request, HTTPException
from sqlalchemy.exc import IntegrityError
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
    verification_token_lifetime_seconds = 60 * 60 * 24 * 3  # 3 days

    #  Restrict registration to specific domain(s)
    ALLOWED_DOMAINS = ["sigmoidanalytics.com"]

    async def create(self, user_create, safe: bool = False, request: Request | None = None):
        """Custom create to restrict domain and handle duplicate users gracefully."""
        email_domain = user_create.email.split("@")[-1].lower()
        if email_domain not in self.ALLOWED_DOMAINS:
            raise HTTPException(
                status_code=400,
                detail=f"Registration is restricted to {', '.join(self.ALLOWED_DOMAINS)} email addresses."
            )

        try:
            # Proceed with normal creation
            user = await super().create(user_create, safe, request)
            logger.info(f"User {user.email} successfully registered.")
            return user

        except IntegrityError as e:
            msg = str(e.orig)
            logger.warning(f" IntegrityError during registration: {msg}")

            if "ix_users_username" in msg:
                raise HTTPException(status_code=400, detail="Username already exists.")
            elif "ix_users_email" in msg:
                raise HTTPException(status_code=400, detail="Email already registered.")
            else:
                raise HTTPException(status_code=400, detail="Database constraint violation during registration.")

    async def on_after_register(self, user: User, request: Request | None = None):
        logger.info(f"User {user.email} has registered.")
        await self.request_verify(user, request)

    async def on_after_forgot_password(self, user: User, token: str, request: Request | None = None):
        send_reset_password_email(None, user.email, token)
        logger.info(f"Password reset email sent to {user.email}")

    async def on_after_request_verify(self, user: User, token: str, request: Request | None = None):
        send_verification_email(None, user.email, token)
        logger.info(f"Verification email sent to {user.email}")

    async def on_after_verify(self, user: User, request: Request | None = None):
        logger.info(f"User {user.email} has been verified.")
        await self.user_db.update(user, {"is_verified": True})


async def get_user_manager(user_db=Depends(get_user_db)):
    yield UserManager(user_db)
