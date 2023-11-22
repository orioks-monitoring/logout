from pydantic import PositiveInt
from sqlalchemy.orm import Session

from app.models.users.user_notify_settings import UserNotifySettings
from app.models.users.user_status import UserStatus


def reset_user(
    db: Session,
    user: UserStatus,
    user_settings: UserNotifySettings,
    user_telegram_id: PositiveInt,
    *,
    refresh_after_commit: bool = False,
) -> None:
    """
    Transactional function for reset user status and user notify settings.
    """

    user.authenticated = False
    db.add(user)
    user_settings.fill(user_telegram_id=user_telegram_id)
    db.add(user_settings)
    db.commit()

    if refresh_after_commit:
        db.refresh(user)
        db.refresh(user_settings)
