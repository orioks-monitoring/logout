from typing import NamedTuple

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.users.user_notify_settings import UserNotifySettings
from app.models.users.user_status import UserStatus


class UserModels(NamedTuple):
    user_status: UserStatus
    user_settings: UserNotifySettings


def get_user_status_and_user_settings_by_id_with_raise(
    db_session: Session, user_telegram_id: int
) -> UserModels:
    """
    Get user status and user settings by user telegram id. If user doesn't exist in user_status table or
    user_settings table, raise HTTPException with status code 404. Use this function in FastAPI path operation
    functions.
    """
    user_status = UserStatus.find_one(db_session, user_telegram_id=user_telegram_id)
    user_settings = UserNotifySettings.find_one(
        db_session, user_telegram_id=user_telegram_id
    )
    if user_status is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User doesn't exist in user_status table",
        )
    if user_settings is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User doesn't exist in user_settings table",
        )
    return UserModels(user_status, user_settings)
