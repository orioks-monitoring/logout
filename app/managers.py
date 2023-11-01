from pydantic import PositiveInt

from app.config import db_session
from app.models.users import UserStatus, UserNotifySettings


def reset_user(user: UserStatus, user_settings: UserNotifySettings, user_telegram_id: PositiveInt) -> None:
    with db_session() as session:
        user.authenticated = False
        user.save()
        user_settings.fill(user_telegram_id=user_telegram_id)
        user_settings.save()

        session.refresh(user)
        session.refresh(user_settings)
