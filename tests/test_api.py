from random import randint
from typing import Generator
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from starlette.testclient import TestClient

from app.config import (
    TEST_DATABASE_URL,
    LOGIN_LOGOUT_SERVICE_HEADER_NAME,
    LOGIN_LOGOUT_SERVICE_TOKEN,
)
from app.main import app
from app.models.base import AbstractBaseModel
from app.models.sql_database import get_db
from app.models.users.user_notify_settings import UserNotifySettings
from app.models.users.user_status import UserStatus
from tests.mocks import (
    make_user_authorized_mocked,
    make_user_reset_mocked,
    mongo_client,
    mongo_collection,
)

client = TestClient(app)

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False}
    if TEST_DATABASE_URL.startswith("sqlite")
    else {},
    poolclass=StaticPool if TEST_DATABASE_URL.endswith(":memory:") else None,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override get_db function for testing purposes."""
    database = TestingSessionLocal()
    try:
        yield database
    finally:
        database.close()


app.dependency_overrides[get_db] = override_get_db


class TestAPI:
    @pytest.fixture(autouse=True, scope="function")
    def clear_all_databases(self) -> None:
        """Clear all databases before each test"""
        for database_name in mongo_client.list_database_names():
            mongo_client.drop_database(database_name)

    @pytest.fixture(scope="function")
    def db_session(self) -> Generator[Session, None, None]:
        """Create a clean mongo_database session for testing purposes."""
        # Create the mongo_database tables
        AbstractBaseModel.metadata.create_all(bind=engine)

        # Run the tests
        yield TestingSessionLocal()

        # Drop the mongo_database tables
        AbstractBaseModel.metadata.drop_all(bind=engine)

    def test_health(self):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "UP"}

    @patch("app.routers.make_user_authorized", make_user_authorized_mocked)
    @patch("app.routers.make_user_reset", make_user_reset_mocked)
    def test_user_login_logout(self, db_session: Session) -> None:
        """Test user login and logout."""
        user_telegram_id = randint(1, 1000)
        user_status = UserStatus(user_telegram_id=user_telegram_id)
        user_settings = UserNotifySettings(user_telegram_id=user_telegram_id)
        db_session.add(user_status)
        db_session.add(user_settings)
        db_session.commit()

        # Login
        cookies = {"key1": "value1", "key2": "value2"}
        response = client.patch(
            f"/user/{user_telegram_id}/login",
            json={"cookies": cookies},
            headers={LOGIN_LOGOUT_SERVICE_HEADER_NAME: LOGIN_LOGOUT_SERVICE_TOKEN},
        )
        assert response.status_code == 200
        assert response.json() == {
            "user_telegram_id": user_telegram_id,
            "authenticated": True,
        }

        # Logout
        response = client.post(
            f"/user/{user_telegram_id}/logout",
            headers={LOGIN_LOGOUT_SERVICE_HEADER_NAME: LOGIN_LOGOUT_SERVICE_TOKEN},
        )
        assert response.status_code == 204

    @patch("app.routers.make_user_authorized", make_user_authorized_mocked)
    @patch("app.routers.make_user_reset", make_user_reset_mocked)
    def test_user_login_logout_with_status(self, db_session: Session):
        # create user
        user_telegram_id = randint(1, 1000)
        user_status = UserStatus(
            user_telegram_id=user_telegram_id,
            agreement_accepted=True,
            authenticated=False,
            login_attempt_count=4,
            failed_request_count=5,
        )
        user_settings = UserNotifySettings(user_telegram_id=user_telegram_id)
        db_session.add(user_status)
        db_session.add(user_settings)
        db_session.commit()

        assert mongo_collection.count_documents({}) == 0

        # get status
        response = client.get(
            f"/user/{user_telegram_id}",
            headers={LOGIN_LOGOUT_SERVICE_HEADER_NAME: LOGIN_LOGOUT_SERVICE_TOKEN},
        )
        assert response.status_code == 200
        assert response.json() == {
            'agreement_accepted': True,
            'authenticated': False,
            'failed_request_count': 5,
            'login_attempt_count': 4,
            'user_telegram_id': user_telegram_id,
        }

        # login
        cookies = {"key1": "value1", "key2": "value2"}
        response = client.patch(
            f"/user/{user_telegram_id}/login",
            json={"cookies": cookies},
            headers={LOGIN_LOGOUT_SERVICE_HEADER_NAME: LOGIN_LOGOUT_SERVICE_TOKEN},
        )
        assert response.status_code == 200
        assert response.json() == {
            "user_telegram_id": user_telegram_id,
            "authenticated": True,
        }

        assert mongo_collection.count_documents({}) == 1

        # get status
        response = client.get(
            f"/user/{user_telegram_id}",
            headers={LOGIN_LOGOUT_SERVICE_HEADER_NAME: LOGIN_LOGOUT_SERVICE_TOKEN},
        )
        assert response.status_code == 200
        assert response.json() == {
            'agreement_accepted': True,
            'authenticated': True,
            'failed_request_count': 5,
            'login_attempt_count': 4,
            'user_telegram_id': user_telegram_id,
        }

        assert mongo_collection.count_documents({}) == 1

        # logout
        response = client.post(
            f"/user/{user_telegram_id}/logout",
            headers={LOGIN_LOGOUT_SERVICE_HEADER_NAME: LOGIN_LOGOUT_SERVICE_TOKEN},
        )
        assert response.status_code == 204

        assert mongo_collection.count_documents({}) == 0

        # get status
        response = client.get(
            f"/user/{user_telegram_id}",
            headers={LOGIN_LOGOUT_SERVICE_HEADER_NAME: LOGIN_LOGOUT_SERVICE_TOKEN},
        )
        assert response.status_code == 200
        assert response.json() == {
            'agreement_accepted': True,
            'authenticated': False,
            'failed_request_count': 5,
            'login_attempt_count': 4,
            'user_telegram_id': user_telegram_id,
        }

        assert mongo_collection.count_documents({}) == 0

        # get status one more time
        response = client.get(
            f"/user/{user_telegram_id}",
            headers={LOGIN_LOGOUT_SERVICE_HEADER_NAME: LOGIN_LOGOUT_SERVICE_TOKEN},
        )
        assert response.status_code == 200
        assert response.json() == {
            'agreement_accepted': True,
            'authenticated': False,
            'failed_request_count': 5,
            'login_attempt_count': 4,
            'user_telegram_id': user_telegram_id,
        }

        assert mongo_collection.count_documents({}) == 0

    @patch("app.routers.make_user_authorized", make_user_authorized_mocked)
    @patch("app.routers.make_user_reset", make_user_reset_mocked)
    def test_user_login_logout_multiple_users(self, db_session: Session):
        user_count = 100
        # dict[user_telegram_id, cookies]
        users: dict[int, dict[str, str]] = {}

        # 100 unique users
        user_telegram_ids = set()
        while len(user_telegram_ids) < user_count:
            user_telegram_ids.add(randint(1, 1000000))

        # create users
        for i, user_telegram_id in enumerate(user_telegram_ids):
            user_status = UserStatus(user_telegram_id=user_telegram_id)
            user_settings = UserNotifySettings(user_telegram_id=user_telegram_id)
            db_session.add(user_status)
            db_session.add(user_settings)
            db_session.commit()

            # random cookies
            cookies = {
                f"key{randint(1, 100)}": f"value{randint(1, 100)}"
                for _ in range(randint(1, 10))
            }
            users[user_telegram_id] = cookies

        assert mongo_collection.count_documents({}) == 0

        # login users
        for user_telegram_id, cookies in users.items():
            response = client.patch(
                f"/user/{user_telegram_id}/login",
                json={"cookies": cookies},
                headers={LOGIN_LOGOUT_SERVICE_HEADER_NAME: LOGIN_LOGOUT_SERVICE_TOKEN},
            )
            assert response.status_code == 200
            assert response.json() == {
                "user_telegram_id": user_telegram_id,
                "authenticated": True,
            }

        assert mongo_collection.count_documents({}) == user_count

        # get status users
        for user_telegram_id in users.keys():
            response = client.get(
                f"/user/{user_telegram_id}",
                headers={LOGIN_LOGOUT_SERVICE_HEADER_NAME: LOGIN_LOGOUT_SERVICE_TOKEN},
            )
            assert response.status_code == 200
            assert response.json() == {
                'agreement_accepted': False,
                'authenticated': True,
                'failed_request_count': 0,
                'login_attempt_count': 0,
                'user_telegram_id': user_telegram_id,
            }

        assert (
            db_session.query(UserStatus)
            .filter(UserStatus.authenticated == True)
            .count()
            == user_count
        )
        assert (
            db_session.query(UserStatus)
            .filter(UserStatus.authenticated == False)
            .count()
            == 0
        )

        # logout users
        for user_telegram_id in users.keys():
            response = client.post(
                f"/user/{user_telegram_id}/logout",
                headers={LOGIN_LOGOUT_SERVICE_HEADER_NAME: LOGIN_LOGOUT_SERVICE_TOKEN},
            )
            assert response.status_code == 204

        assert mongo_collection.count_documents({}) == 0

        # get status users
        for user_telegram_id in users.keys():
            response = client.get(
                f"/user/{user_telegram_id}",
                headers={LOGIN_LOGOUT_SERVICE_HEADER_NAME: LOGIN_LOGOUT_SERVICE_TOKEN},
            )
            assert response.status_code == 200
            assert response.json() == {
                'agreement_accepted': False,
                'authenticated': False,
                'failed_request_count': 0,
                'login_attempt_count': 0,
                'user_telegram_id': user_telegram_id,
            }

        assert db_session.query(UserStatus).count() == user_count
        assert db_session.query(UserNotifySettings).count() == user_count
        assert (
            db_session.query(UserStatus)
            .filter(UserStatus.authenticated == True)
            .count()
            == 0
        )
        assert (
            db_session.query(UserStatus)
            .filter(UserStatus.authenticated == False)
            .count()
            == user_count
        )
