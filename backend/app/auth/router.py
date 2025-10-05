from fastapi import APIRouter
from fastapi_users import FastAPIUsers
from fastapi_users.authentication import (JWTStrategy,AuthenticationBackend,BearerTransport,)
import uuid
from app.models import User
from app.auth.manager import get_user_manager
from app.schemas import UserRead, UserCreate, UserUpdate
from app.config import config

# Transport definition (Bearer tokens)
bearer_transport = BearerTransport(tokenUrl="auth/jwt/login")


def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(
        secret=config.SECRET_KEY,
        lifetime_seconds=config.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)

# FastAPIUsers Initialization
fastapi_users = FastAPIUsers[User, uuid.UUID](
    get_user_manager,
    [auth_backend],
)

# Routers
router = APIRouter(prefix="/api")

#  Require email verification before login
router.include_router(
    fastapi_users.get_auth_router(auth_backend, requires_verification=True),
    prefix="/auth/jwt",
    tags=["Auth"],
)

# Register new users
router.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["Auth"],
)

# Reset password flow
router.include_router(
    fastapi_users.get_reset_password_router(),
    prefix="/auth",
    tags=["Auth"],
)

# Email verification flow
router.include_router(
    fastapi_users.get_verify_router(UserRead),
    prefix="/auth",
    tags=["Auth"],
)

# Users management
router.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/users",
    tags=["Users"],
)
