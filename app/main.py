import logging

from fastapi import Depends, FastAPI, HTTPException, Path, status
from pydantic import PositiveInt
from sqlalchemy.orm import Session

from app.managers import reset_user
from app.middlewares import AuthValidationMiddleware
from app.models.database import get_db
from app.models.users.user_notify_settings import UserNotifySettings
from app.models.users.user_status import UserStatus
from app.schemas import User

app = FastAPI(
    title="Logout service",
    description="Service for logout user from system.",
)

app.add_middleware(AuthValidationMiddleware)

logger = logging.getLogger(__name__)


@app.get("/user/{user_telegram_id}")
async def get_user_status(
    user_telegram_id: PositiveInt = Path(ge=1, title="User Telegram ID"),
    db: Session = Depends(get_db),
) -> User:
    logger.info("Request get user status for user with id: %s", user_telegram_id)
    user = UserStatus.find_one(db, user_telegram_id=user_telegram_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return User(**user.as_dict())


@app.post("/user/{user_telegram_id}/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout_user(
    user_telegram_id: PositiveInt = Path(ge=1, title="User Telegram ID"),
    db: Session = Depends(get_db),
) -> None:
    logger.info("Request logout user with id: %s", user_telegram_id)

    user = UserStatus.find_one(db, user_telegram_id=user_telegram_id)
    user_settings = UserNotifySettings.find_one(db, user_telegram_id=user_telegram_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    if user_settings is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User settings not found"
        )

    logger.debug("Resetting user %s...", user)
    reset_user(db, user, user_settings, user_telegram_id)
    logger.info("User %s reset", user)
    return None
