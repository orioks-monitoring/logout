import mongomock
from mongomock.helpers import ASCENDING
from pydantic import PositiveInt
from sqlalchemy.orm import Session

from app.models.users.user_notify_settings import UserNotifySettings
from app.models.users.user_status import UserStatus

mongo_client = mongomock.MongoClient()
mongo_database = mongo_client.pymongo_test
mongo_collection = mongo_database.posts


async def make_user_authorized_mocked(
    db_session: Session,
    user_status: UserStatus,
    user_telegram_id: PositiveInt,
    cookies: dict[str, str],
    *,
    refresh_after_commit: bool = False,
) -> None:
    user_status.authenticated = True
    db_session.add(user_status)
    db_session.commit()

    if refresh_after_commit:
        db_session.refresh(user_status)

    # Mocked behavior for the MongoDB insertion
    mongo_collection.insert_one(
        {"user_telegram_id": user_telegram_id, "cookies": cookies}
    )
    # create index for user_telegram_id
    mongo_collection.create_index([('user_telegram_id', ASCENDING)], unique=True)


async def make_user_reset_mocked(
    db_session: Session,
    user_status: UserStatus,
    user_settings: UserNotifySettings,
    user_telegram_id: PositiveInt,
    *,
    refresh_after_commit: bool = False,
) -> None:
    user_status.authenticated = False
    db_session.add(user_status)
    user_settings.fill(user_telegram_id=user_telegram_id)
    db_session.add(user_settings)
    db_session.commit()

    if refresh_after_commit:
        db_session.refresh(user_status)
        db_session.refresh(user_settings)

    # Mocked behavior for the MongoDB deletion
    mongo_collection.delete_one({"user_telegram_id": user_telegram_id})


def make_user_reset_without_mongo_deletion_mocked(
    db_session: Session,
    user_status: UserStatus,
    user_settings: UserNotifySettings,
    user_telegram_id: PositiveInt,
    *,
    refresh_after_commit: bool = False,
) -> None:
    user_status.authenticated = False
    db_session.add(user_status)
    user_settings.fill(user_telegram_id=user_telegram_id)
    db_session.add(user_settings)
    db_session.commit()

    if refresh_after_commit:
        db_session.refresh(user_status)
        db_session.refresh(user_settings)

    # Logic for the MongoDB deletion is mocked
    pass
