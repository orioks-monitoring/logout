import logging

from fastapi import Depends, FastAPI, HTTPException, Path, status
from pydantic import PositiveInt
from pymongo.errors import DuplicateKeyError
from sqlalchemy.orm import Session

from app.utils.managers import make_user_reset, make_user_authorized
from app.middlewares import AuthValidationMiddleware
from app.models.sql_database import get_db
from app.models.users.user_status import UserStatus
from app.schemas import (
    UserStatusSchema,
    UserLoginBodySchema,
    UserStatusAuthenticatedSchema,
    AppStatusSchema,
)
from app.utils.utils import get_user_status_and_user_settings_by_id_with_raise

app = FastAPI(
    title="Logout service",
    description="Service for logout user from system.",
)

app.add_middleware(AuthValidationMiddleware)

logger = logging.getLogger(__name__)


@app.get("/health")
async def health() -> AppStatusSchema:
    return AppStatusSchema(status="UP")


@app.get("/user/{user_telegram_id}")
async def get_user_status(
    user_telegram_id: PositiveInt = Path(ge=1, title="UserStatus Telegram ID"),
    db_session: Session = Depends(get_db),
) -> UserStatusSchema:
    logger.info("Request get user status for user with id: %s", user_telegram_id)
    user = UserStatus.find_one(db_session, user_telegram_id=user_telegram_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User doesn't exist in user_status table",
        )
    return UserStatusSchema(**user.as_dict())


@app.post("/user/{user_telegram_id}/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout_user(
    user_telegram_id: PositiveInt = Path(ge=1, title="UserStatus Telegram ID"),
    db_session: Session = Depends(get_db),
) -> None:
    logger.info("Request logout user with id: %s", user_telegram_id)
    user_status, user_settings = get_user_status_and_user_settings_by_id_with_raise(
        db_session, user_telegram_id
    )
    logger.debug("Resetting user %s...", user_status)
    await make_user_reset(db_session, user_status, user_settings, user_telegram_id)
    logger.info("UserStatus %s reset", user_status)
    return None


@app.patch("/user/{user_telegram_id}/login", status_code=status.HTTP_200_OK)
async def login_user(
    user_login_body: UserLoginBodySchema,
    user_telegram_id: PositiveInt = Path(ge=1, title="UserStatus Telegram ID"),
    db_session: Session = Depends(get_db),
) -> UserStatusAuthenticatedSchema:
    logger.info("Request login user with id: %s", user_telegram_id)
    user_status, user_settings = get_user_status_and_user_settings_by_id_with_raise(
        db_session, user_telegram_id
    )
    if not user_login_body.cookies:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Cookies is empty"
        )
    logger.debug("Login user %s...", user_status)
    try:
        await make_user_authorized(
            db_session,
            user_status,
            user_telegram_id,
            user_login_body.cookies,
            refresh_after_commit=True,
        )
    except DuplicateKeyError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="User already logged in"
        )
    logger.info("UserStatus %s login", user_status)
    return UserStatusAuthenticatedSchema(
        user_telegram_id=user_telegram_id, authenticated=user_status.authenticated
    )
