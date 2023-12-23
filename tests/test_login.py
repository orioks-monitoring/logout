from random import randint
from typing import Generator
from unittest.mock import patch

import mongomock
import pytest
from pymongo.results import InsertOneResult, InsertManyResult
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from starlette.testclient import TestClient

from app.config import (
    TEST_DATABASE_URL,
    LOGOUT_SERVICE_HEADER_NAME,
    LOGOUT_SERVICE_TOKEN,
)
from app.main import app
from app.models.base import AbstractBaseModel
from app.models.sql_database import get_db
from app.models.users.user_notify_settings import UserNotifySettings
from app.models.users.user_status import UserStatus
from tests.mocks import (
    make_user_authorized_mocked,
    mongo_client,
    mongo_database,
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


class TestLogin:
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

    def test_mongo_is_mocked(self):
        assert isinstance(mongo_client, mongomock.MongoClient)

    def test_mongo_basic(self):
        # is empty
        assert mongo_client.list_database_names() == []
        assert mongo_database.list_collection_names() == []
        assert mongo_collection.count_documents({}) == 0

        # insert one
        result: InsertOneResult = mongo_collection.insert_one({"some": "data"})
        assert result.acknowledged
        assert result.inserted_id is not None
        assert mongo_collection.count_documents({}) == 1

        # find one
        result: dict | None = mongo_collection.find_one({})
        assert result is not None
        assert result["some"] == "data"

        # find many
        result: dict | None = mongo_collection.find({})
        assert result is not None
        assert len(list(result)) == 1
        assert mongo_collection.count_documents({}) == 1

        # insert many
        result: InsertManyResult = mongo_collection.insert_many(
            [{"some": "data"}, {"some": "data"}]
        )
        assert result.acknowledged
        assert result.inserted_ids is not None
        assert len(result.inserted_ids) == 2
        assert mongo_collection.count_documents({}) == 3

        # find many
        result: dict | None = mongo_collection.find({})
        assert result is not None
        assert len(list(result)) == 3
        assert mongo_collection.count_documents({}) == 3

        # find many with filter
        result: dict | None = mongo_collection.find({"some": "data"})
        assert result is not None
        assert len(list(result)) == 3
        assert mongo_collection.count_documents({}) == 3

    def test_mongo_still_empty_after_another_test_completed(self):
        # is empty
        assert mongo_client.list_database_names() == []
        assert mongo_database.list_collection_names() == []
        assert mongo_collection.count_documents({}) == 0

    def test_tables_are_empty(self, db_session: Session):
        """Test that all tables are empty after the mongo_database is created."""
        for table in AbstractBaseModel.metadata.tables.values():
            print(table.name)
            assert db_session.query(table).count() == 0

    def test_login_user_not_found(self, db_session: Session):
        # db is empty
        for table in AbstractBaseModel.metadata.tables.values():
            assert db_session.query(table).count() == 0

        user_telegram_id = 1
        headers = {LOGOUT_SERVICE_HEADER_NAME: LOGOUT_SERVICE_TOKEN}
        user_login_body = {"cookies": {"example_cookie": "example_value"}}

        response = client.patch(
            f"/user/{user_telegram_id}/login", headers=headers, json=user_login_body
        )

        assert response.status_code == 404
        assert response.json() == {"detail": "User doesn't exist in user_status table"}

        # db is empty
        for table in AbstractBaseModel.metadata.tables.values():
            assert db_session.query(table).count() == 0

        # mongo is empty
        assert mongo_collection.count_documents({}) == 0

    def test_login_user_settings_not_found(self, db_session: Session):
        # db is empty
        for table in AbstractBaseModel.metadata.tables.values():
            assert db_session.query(table).count() == 0

        user_telegram_id = 1
        headers = {LOGOUT_SERVICE_HEADER_NAME: LOGOUT_SERVICE_TOKEN}
        user_login_body = {"cookies": {"example_cookie": "example_value"}}

        # insert user_status
        user_status = UserStatus(user_telegram_id=user_telegram_id, authenticated=False)
        db_session.add(user_status)
        db_session.commit()

        # db is not empty
        assert db_session.query(UserStatus).count() == 1

        response = client.patch(
            f"/user/{user_telegram_id}/login", headers=headers, json=user_login_body
        )

        assert response.status_code == 404
        assert response.json() == {
            "detail": "User doesn't exist in user_settings table"
        }

        # db still has only one row with authenticated=False
        assert db_session.query(UserStatus).count() == 1
        assert db_session.query(UserStatus).first().authenticated is False

        # mongo is empty
        assert mongo_collection.count_documents({}) == 0

    def test_login_user_status_not_found(self, db_session: Session):
        # db is empty
        for table in AbstractBaseModel.metadata.tables.values():
            assert db_session.query(table).count() == 0

        user_telegram_id = 1
        headers = {LOGOUT_SERVICE_HEADER_NAME: LOGOUT_SERVICE_TOKEN}
        user_login_body = {"cookies": {"example_cookie": "example_value"}}

        # insert user_settings
        user_settings = UserNotifySettings(user_telegram_id=user_telegram_id)
        db_session.add(user_settings)
        db_session.commit()

        # db is not empty
        assert db_session.query(UserNotifySettings).count() == 1

        response = client.patch(
            f"/user/{user_telegram_id}/login", headers=headers, json=user_login_body
        )

        assert response.status_code == 404
        assert response.json() == {"detail": "User doesn't exist in user_status table"}

        # db still has only one row with authenticated=False
        assert db_session.query(UserNotifySettings).count() == 1
        assert (
            db_session.query(UserNotifySettings).first().user_telegram_id
            == user_telegram_id
        )

        # mongo is empty
        assert mongo_collection.count_documents({}) == 0

    @patch("app.routers.make_user_authorized", make_user_authorized_mocked)
    def test_login_user(self, db_session: Session):
        user_telegram_id = 1
        headers = {LOGOUT_SERVICE_HEADER_NAME: LOGOUT_SERVICE_TOKEN}
        user_login_body = {"cookies": {"example_cookie": "example_value"}}

        user_status = UserStatus(user_telegram_id=user_telegram_id, authenticated=False)
        user_settings = UserNotifySettings(user_telegram_id=user_telegram_id)
        db_session.add(user_status)
        db_session.add(user_settings)

        db_session.commit()

        # db is not empty
        assert db_session.query(UserStatus).count() == 1
        assert db_session.query(UserNotifySettings).count() == 1

        response = client.patch(
            f"/user/{user_telegram_id}/login", headers=headers, json=user_login_body
        )

        assert response.status_code == 200
        assert response.json() == {
            "user_telegram_id": user_telegram_id,
            "authenticated": True,
        }

        # db still has only one row with authenticated=True
        assert db_session.query(UserStatus).count() == 1
        assert db_session.query(UserStatus).first().authenticated is True

        # mongo has one row with cookies
        assert mongo_collection.count_documents({}) == 1
        assert mongo_collection.find_one({})["cookies"] == {
            "example_cookie": "example_value"
        }
        assert mongo_collection.find_one({})["user_telegram_id"] == user_telegram_id
        assert mongo_collection.find_one({})["_id"] is not None

    @patch("app.routers.make_user_authorized", make_user_authorized_mocked)
    def test_login_user_without_header(self, db_session: Session):
        user_telegram_id = 1
        headers = {}
        user_login_body = {"cookies": {"example_cookie": "example_value"}}

        user_status = UserStatus(user_telegram_id=user_telegram_id, authenticated=False)
        user_settings = UserNotifySettings(user_telegram_id=user_telegram_id)
        db_session.add(user_status)
        db_session.add(user_settings)

        db_session.commit()

        # db is not empty
        assert db_session.query(UserStatus).count() == 1
        assert db_session.query(UserNotifySettings).count() == 1

        response = client.patch(
            f"/user/{user_telegram_id}/login", headers=headers, json=user_login_body
        )

        assert response.status_code == 401
        assert response.json() == {"detail": "Unauthorized"}

        # db still has only one row with authenticated=False
        assert db_session.query(UserStatus).count() == 1
        assert db_session.query(UserStatus).first().authenticated is False

        # mongo is empty
        assert mongo_collection.count_documents({}) == 0

    @patch("app.routers.make_user_authorized", make_user_authorized_mocked)
    def test_login_user_with_wrong_header(self, db_session: Session):
        user_telegram_id = 1
        headers = {"wrong_header": "wrong_token"}
        user_login_body = {"cookies": {"example_cookie": "example_value"}}

        user_status = UserStatus(user_telegram_id=user_telegram_id, authenticated=False)
        user_settings = UserNotifySettings(user_telegram_id=user_telegram_id)
        db_session.add(user_status)
        db_session.add(user_settings)

        db_session.commit()

        # db is not empty
        assert db_session.query(UserStatus).count() == 1
        assert db_session.query(UserNotifySettings).count() == 1

        response = client.patch(
            f"/user/{user_telegram_id}/login", headers=headers, json=user_login_body
        )

        assert response.status_code == 401
        assert response.json() == {"detail": "Unauthorized"}

        # db still has only one row with authenticated=False
        assert db_session.query(UserStatus).count() == 1
        assert db_session.query(UserStatus).first().authenticated is False

        # mongo is empty
        assert mongo_collection.count_documents({}) == 0

    @patch("app.routers.make_user_authorized", make_user_authorized_mocked)
    def test_login_user_with_wrong_token(self, db_session: Session):
        user_telegram_id = 1
        headers = {LOGOUT_SERVICE_HEADER_NAME: "wrong_token"}
        user_login_body = {"cookies": {"example_cookie": "example_value"}}

        user_status = UserStatus(user_telegram_id=user_telegram_id, authenticated=False)
        user_settings = UserNotifySettings(user_telegram_id=user_telegram_id)
        db_session.add(user_status)
        db_session.add(user_settings)

        db_session.commit()

        # db is not empty
        assert db_session.query(UserStatus).count() == 1
        assert db_session.query(UserNotifySettings).count() == 1

        response = client.patch(
            f"/user/{user_telegram_id}/login", headers=headers, json=user_login_body
        )

        assert response.status_code == 403
        assert response.json() == {"detail": "Forbidden"}

        # db still has only one row with authenticated=False
        assert db_session.query(UserStatus).count() == 1
        assert db_session.query(UserStatus).first().authenticated is False

        # mongo is empty
        assert mongo_collection.count_documents({}) == 0

    @patch("app.routers.make_user_authorized", make_user_authorized_mocked)
    def test_login_user_with_wrong_user_id(self, db_session: Session):
        user_telegram_id = 1
        headers = {LOGOUT_SERVICE_HEADER_NAME: LOGOUT_SERVICE_TOKEN}
        user_login_body = {"cookies": {"example_cookie": "example_value"}}

        user_status = UserStatus(user_telegram_id=user_telegram_id, authenticated=False)
        user_settings = UserNotifySettings(user_telegram_id=user_telegram_id)
        db_session.add(user_status)
        db_session.add(user_settings)

        db_session.commit()

        # db is not empty
        assert db_session.query(UserStatus).count() == 1
        assert db_session.query(UserNotifySettings).count() == 1

        response = client.patch(
            f"/user/{user_telegram_id + 1}/login", headers=headers, json=user_login_body
        )

        assert response.status_code == 404
        assert response.json() == {"detail": "User doesn't exist in user_status table"}

        # db still has only one row with authenticated=False
        assert db_session.query(UserStatus).count() == 1
        assert db_session.query(UserStatus).first().authenticated is False

        # mongo is empty
        assert mongo_collection.count_documents({}) == 0

    @patch("app.routers.make_user_authorized", make_user_authorized_mocked)
    def test_login_user_with_wrong_body(self, db_session: Session):
        user_telegram_id = 1
        headers = {LOGOUT_SERVICE_HEADER_NAME: LOGOUT_SERVICE_TOKEN}
        user_login_body = {"wrong_body": "wrong_value"}

        user_status = UserStatus(user_telegram_id=user_telegram_id, authenticated=False)
        user_settings = UserNotifySettings(user_telegram_id=user_telegram_id)
        db_session.add(user_status)
        db_session.add(user_settings)

        db_session.commit()

        # db is not empty
        assert db_session.query(UserStatus).count() == 1
        assert db_session.query(UserNotifySettings).count() == 1

        response = client.patch(
            f"/user/{user_telegram_id}/login", headers=headers, json=user_login_body
        )

        assert response.status_code == 422
        assert response.json()["detail"][0]["type"] == "missing"
        assert response.json()["detail"][0]["loc"] == ["body", "cookies"]
        assert response.json()["detail"][0]["msg"] == "Field required"
        assert response.json()["detail"][0]["input"] == {"wrong_body": "wrong_value"}

        # db still has only one row with authenticated=False
        assert db_session.query(UserStatus).count() == 1
        assert db_session.query(UserStatus).first().authenticated is False

        # mongo is empty
        assert mongo_collection.count_documents({}) == 0

    @patch("app.routers.make_user_authorized", make_user_authorized_mocked)
    def test_login_user_with_wrong_cookies(self, db_session: Session):
        user_telegram_id = 1
        headers = {LOGOUT_SERVICE_HEADER_NAME: LOGOUT_SERVICE_TOKEN}
        user_login_body = {"cookies": "wrong_value"}

        user_status = UserStatus(user_telegram_id=user_telegram_id, authenticated=False)
        user_settings = UserNotifySettings(user_telegram_id=user_telegram_id)
        db_session.add(user_status)
        db_session.add(user_settings)

        db_session.commit()

        # db is not empty
        assert db_session.query(UserStatus).count() == 1
        assert db_session.query(UserNotifySettings).count() == 1

        response = client.patch(
            f"/user/{user_telegram_id}/login", headers=headers, json=user_login_body
        )

        assert response.status_code == 422
        assert response.json()["detail"][0]["type"] == "dict_type"
        assert response.json()["detail"][0]["loc"] == ["body", "cookies"]
        assert (
            response.json()["detail"][0]["msg"] == "Input should be a valid dictionary"
        )
        assert response.json()["detail"][0]["input"] == "wrong_value"

        # db still has only one row with authenticated=False
        assert db_session.query(UserStatus).count() == 1
        assert db_session.query(UserStatus).first().authenticated is False

        # mongo is empty
        assert mongo_collection.count_documents({}) == 0

    @patch("app.routers.make_user_authorized", make_user_authorized_mocked)
    def test_login_user_with_empty_cookies(self, db_session: Session):
        user_telegram_id = 1
        headers = {LOGOUT_SERVICE_HEADER_NAME: LOGOUT_SERVICE_TOKEN}
        user_login_body = {"cookies": {}}

        user_status = UserStatus(user_telegram_id=user_telegram_id, authenticated=False)
        user_settings = UserNotifySettings(user_telegram_id=user_telegram_id)
        db_session.add(user_status)
        db_session.add(user_settings)

        db_session.commit()

        # db is not empty
        assert db_session.query(UserStatus).count() == 1
        assert db_session.query(UserNotifySettings).count() == 1

        response = client.patch(
            f"/user/{user_telegram_id}/login", headers=headers, json=user_login_body
        )

        assert response.status_code == 400
        assert response.json() == {"detail": "Cookies is empty"}

        # db still has only one row with authenticated=False
        assert db_session.query(UserStatus).count() == 1
        assert db_session.query(UserStatus).first().authenticated is False

        # mongo is empty
        assert mongo_collection.count_documents({}) == 0

    @patch("app.routers.make_user_authorized", make_user_authorized_mocked)
    def test_login_user_twice(self, db_session: Session):
        user_telegram_id = 1
        headers = {LOGOUT_SERVICE_HEADER_NAME: LOGOUT_SERVICE_TOKEN}
        user_login_body = {"cookies": {"example_cookie": "example_value"}}

        user_status = UserStatus(user_telegram_id=user_telegram_id, authenticated=False)
        user_settings = UserNotifySettings(user_telegram_id=user_telegram_id)
        db_session.add(user_status)
        db_session.add(user_settings)

        db_session.commit()

        # db is not empty
        assert db_session.query(UserStatus).count() == 1
        assert db_session.query(UserNotifySettings).count() == 1

        # first login
        response = client.patch(
            f"/user/{user_telegram_id}/login", headers=headers, json=user_login_body
        )

        assert response.status_code == 200
        assert response.json() == {
            "user_telegram_id": user_telegram_id,
            "authenticated": True,
        }

        # db still has only one row with authenticated=True
        assert db_session.query(UserStatus).count() == 1
        assert db_session.query(UserStatus).first().authenticated is True

        # mongo has one row with cookies
        assert mongo_collection.count_documents({}) == 1
        assert mongo_collection.find_one({})["cookies"] == {
            "example_cookie": "example_value"
        }
        assert mongo_collection.find_one({})["user_telegram_id"] == user_telegram_id
        assert mongo_collection.find_one({})["_id"] is not None

        # second login
        response = client.patch(
            f"/user/{user_telegram_id}/login", headers=headers, json=user_login_body
        )

        assert response.status_code == 400
        assert response.json() == {"detail": "User already logged in"}

        # db still has only one row with authenticated=True
        assert db_session.query(UserStatus).count() == 1
        assert db_session.query(UserStatus).first().authenticated is True

        # mongo has one row with cookies
        assert mongo_collection.count_documents({}) == 1
        assert mongo_collection.find_one({})["cookies"] == {
            "example_cookie": "example_value"
        }
        assert mongo_collection.find_one({})["user_telegram_id"] == user_telegram_id
        assert mongo_collection.find_one({})["_id"] is not None

    @patch("app.routers.make_user_authorized", make_user_authorized_mocked)
    def test_login_user_twice_with_different_cookies(self, db_session: Session):
        user_telegram_id = 1
        headers = {LOGOUT_SERVICE_HEADER_NAME: LOGOUT_SERVICE_TOKEN}
        user_login_body_1 = {"cookies": {"example_cookie": "example_value_1"}}
        user_login_body_2 = {"cookies": {"example_cookie": "example_value_2"}}

        user_status = UserStatus(user_telegram_id=user_telegram_id, authenticated=False)
        user_settings = UserNotifySettings(user_telegram_id=user_telegram_id)
        db_session.add(user_status)
        db_session.add(user_settings)

        db_session.commit()

        # db is not empty
        assert db_session.query(UserStatus).count() == 1
        assert db_session.query(UserNotifySettings).count() == 1

        # first login
        response = client.patch(
            f"/user/{user_telegram_id}/login", headers=headers, json=user_login_body_1
        )

        assert response.status_code == 200
        assert response.json() == {
            "user_telegram_id": user_telegram_id,
            "authenticated": True,
        }

        # db still has only one row with authenticated=True
        assert db_session.query(UserStatus).count() == 1
        assert db_session.query(UserStatus).first().authenticated is True

        # mongo has one row with cookies
        assert mongo_collection.count_documents({}) == 1
        assert mongo_collection.find_one({})["cookies"] == {
            "example_cookie": "example_value_1"
        }
        assert mongo_collection.find_one({})["user_telegram_id"] == user_telegram_id
        assert mongo_collection.find_one({})["_id"] is not None

        # second login
        response = client.patch(
            f"/user/{user_telegram_id}/login", headers=headers, json=user_login_body_2
        )

        assert response.status_code == 400
        assert response.json() == {"detail": "User already logged in"}

        # db still has only one row with authenticated=True
        assert db_session.query(UserStatus).count() == 1
        assert db_session.query(UserStatus).first().authenticated is True

        # mongo has one row with cookies
        assert mongo_collection.count_documents({}) == 1
        assert mongo_collection.find_one({})["cookies"] == {
            "example_cookie": "example_value_1"
        }
        assert mongo_collection.find_one({})["user_telegram_id"] == user_telegram_id
        assert mongo_collection.find_one({})["_id"] is not None

    @patch("app.routers.make_user_authorized", make_user_authorized_mocked)
    def test_login_user_multiple_users(self, db_session: Session):
        user_count = 100
        headers = {LOGOUT_SERVICE_HEADER_NAME: LOGOUT_SERVICE_TOKEN}

        map_user_telegram_id_to_cookies: dict[int, dict[str, str]] = {}
        for _ in range(user_count):
            user_telegram_id = randint(1, 1000000)
            user_login_body = {
                "cookies": {
                    f"example_cookie_{user_telegram_id}": f"example_value_{user_telegram_id}"
                }
            }
            map_user_telegram_id_to_cookies[user_telegram_id] = user_login_body[
                "cookies"
            ]
            user_status = UserStatus(
                user_telegram_id=user_telegram_id, authenticated=False
            )
            user_settings = UserNotifySettings(user_telegram_id=user_telegram_id)
            db_session.add(user_status)
            db_session.add(user_settings)
        db_session.commit()

        # db is not empty
        assert db_session.query(UserStatus).count() == user_count
        assert db_session.query(UserNotifySettings).count() == user_count

        for user_telegram_id, cookies in map_user_telegram_id_to_cookies.items():
            response = client.patch(
                f"/user/{user_telegram_id}/login",
                headers=headers,
                json={"cookies": cookies},
            )
            assert response.status_code == 200
            assert response.json() == {
                "user_telegram_id": user_telegram_id,
                "authenticated": True,
            }

        # all users are logged in
        assert db_session.query(UserStatus).count() == user_count
        assert (
            db_session.query(UserStatus)
            .filter(UserStatus.authenticated == True)
            .count()
            == user_count
        )

        # mongo has one row with cookies
        assert mongo_collection.count_documents({}) == user_count
        for user_telegram_id, cookies in map_user_telegram_id_to_cookies.items():
            assert (
                mongo_collection.find_one({"user_telegram_id": user_telegram_id})[
                    "cookies"
                ]
                == cookies
            )
            assert (
                mongo_collection.find_one({"user_telegram_id": user_telegram_id})[
                    "user_telegram_id"
                ]
                == user_telegram_id
            )
            assert (
                mongo_collection.find_one({"user_telegram_id": user_telegram_id})["_id"]
                is not None
            )

    @patch("app.routers.make_user_authorized", make_user_authorized_mocked)
    def test_login_user_one_by_one(self, db_session: Session):
        user_count = 100
        headers = {LOGOUT_SERVICE_HEADER_NAME: LOGOUT_SERVICE_TOKEN}

        assert mongo_collection.count_documents({}) == 0
        assert db_session.query(UserStatus).count() == 0

        # 100 unique users
        user_telegram_ids = set()
        while len(user_telegram_ids) < user_count:
            user_telegram_ids.add(randint(1, 1000))

        for i, user_telegram_id in enumerate(user_telegram_ids):
            user_login_body = {
                "cookies": {
                    f"example_cookie_{user_telegram_id}": f"example_value_{user_telegram_id}"
                }
            }
            user_status = UserStatus(
                user_telegram_id=user_telegram_id, authenticated=False
            )
            user_settings = UserNotifySettings(user_telegram_id=user_telegram_id)
            db_session.add(user_status)
            db_session.add(user_settings)
            db_session.commit()

            # db is not empty
            assert db_session.query(UserStatus).count() == i + 1
            assert db_session.query(UserNotifySettings).count() == i + 1

            # get user_status from endpoint
            response = client.get(f"/user/{user_telegram_id}", headers=headers)
            assert response.status_code == 200
            assert response.json() == {
                'agreement_accepted': False,
                'authenticated': False,
                'failed_request_count': 0,
                'login_attempt_count': 0,
                'user_telegram_id': user_telegram_id,
            }

            response = client.patch(
                f"/user/{user_telegram_id}/login", headers=headers, json=user_login_body
            )
            assert response.status_code == 200
            assert response.json() == {
                "user_telegram_id": user_telegram_id,
                "authenticated": True,
            }

            # get user_status from endpoint
            response = client.get(f"/user/{user_telegram_id}", headers=headers)
            assert response.status_code == 200
            assert response.json() == {
                'agreement_accepted': False,
                'authenticated': True,
                'failed_request_count': 0,
                'login_attempt_count': 0,
                'user_telegram_id': user_telegram_id,
            }

            # db still has only one row with authenticated=True
            assert db_session.query(UserStatus).count() == i + 1
            assert (
                db_session.query(UserStatus)
                .filter(UserStatus.authenticated == True)
                .count()
                == i + 1
            )

            # mongo has one row with cookies
            assert mongo_collection.count_documents({}) == i + 1
            assert (
                mongo_collection.find_one({"user_telegram_id": user_telegram_id})[
                    "cookies"
                ]
                == user_login_body["cookies"]
            )
            assert (
                mongo_collection.find_one({"user_telegram_id": user_telegram_id})[
                    "user_telegram_id"
                ]
                == user_telegram_id
            )
            assert (
                mongo_collection.find_one({"user_telegram_id": user_telegram_id})["_id"]
                is not None
            )

        # mongo has rows with cookies
        assert mongo_collection.count_documents({}) == user_count

        # sql has rows with authenticated=True
        assert db_session.query(UserStatus).count() == user_count
