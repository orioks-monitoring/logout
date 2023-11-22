from typing import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.testclient import TestClient

from app.config import LOGOUT_SERVICE_TOKEN, TEST_DATABASE_URL
from app.main import app
from app.models.base import AbstractBaseModel
from app.models.database import get_db
from app.models.users.user_notify_settings import UserNotifySettings
from app.models.users.user_status import UserStatus

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False}
    if TEST_DATABASE_URL.startswith("sqlite")
    else {},
    poolclass=StaticPool if TEST_DATABASE_URL.endswith(":memory:") else None,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

client = TestClient(app)


def override_get_db():
    """Override get_db function for testing purposes."""
    database = TestingSessionLocal()
    try:
        yield database
    finally:
        database.close()


app.dependency_overrides[get_db] = override_get_db


class TestAPI:
    @pytest.fixture(scope="function")
    def db_session(self) -> Generator[Session, None, None]:
        """Create a clean database session for testing purposes."""
        # Create the database tables
        AbstractBaseModel.metadata.create_all(bind=engine)

        # Run the tests
        yield TestingSessionLocal()

        # Drop the database tables
        AbstractBaseModel.metadata.drop_all(bind=engine)

    def test_tables_are_created(self, db_session: Session):
        """Test that all tables are created after the database is created."""
        tables = AbstractBaseModel.metadata.tables.values()
        assert len(tables) > 0

    def test_user_status_table_is_created(self, db_session: Session):
        """Test that the user_status table is created after the database is created."""
        assert UserStatus.__tablename__ in AbstractBaseModel.metadata.tables

    def test_user_notify_settings_table_is_created(self, db_session: Session):
        """Test that the user_notify_settings table is created after the database is created."""
        from app.models.users.user_notify_settings import UserNotifySettings

        assert UserNotifySettings.__tablename__ in AbstractBaseModel.metadata.tables

    def test_tables_are_empty(self, db_session: Session):
        """Test that all tables are empty after the database is created."""
        for table in AbstractBaseModel.metadata.tables.values():
            print(table.name)
            assert db_session.query(table).count() == 0

    @pytest.mark.parametrize(
        "url",
        ["/user/{user_telegram_id}", "/user/{user_telegram_id}/logout", "/wrong-url"],
    )
    @pytest.mark.parametrize(
        "user_telegram_id",
        ["0", "1", "abc", "11.1"],
    )
    @pytest.mark.parametrize(
        "method",
        ["post", "get", "put", "delete", "options", "patch"],
    )
    def test_middleware_invalid_token(
        self, url: str, user_telegram_id: int, method: str
    ):
        headers = {"X-Auth-Token": "InvalidToken"}
        response = getattr(client, method)(
            url.format(user_telegram_id=user_telegram_id), headers=headers
        )
        assert response.status_code == 403
        assert response.json() == {"detail": "Forbidden"}

    @pytest.mark.parametrize(
        "url",
        ["/user/{user_telegram_id}", "/user/{user_telegram_id}/logout", "/wrong-url"],
    )
    @pytest.mark.parametrize(
        "user_telegram_id",
        ["0", "1", "abc", "11.1"],
    )
    @pytest.mark.parametrize(
        "method",
        ["post", "get", "put", "delete", "options", "patch"],
    )
    def test_middleware_no_token_wrong_url(
        self, url: str, user_telegram_id: int, method: str
    ):
        response = getattr(client, method)(
            url.format(user_telegram_id=user_telegram_id)
        )
        assert response.status_code == 401
        assert response.json() == {"detail": "Unauthorized"}

    def test_docs(self):
        response = client.get("/docs")
        assert response.status_code == 200

    def test_openapi(self):
        response = client.get("/openapi.json")
        assert response.status_code == 200

    def test_get_user_status(self, db_session: Session):
        # Create a test UserStatus object
        test_user_status = UserStatus(
            user_telegram_id=123,
            agreement_accepted=True,
            authenticated=True,
            login_attempt_count=2,
            failed_request_count=1,
        )
        db_session.add(test_user_status)
        db_session.commit()

        headers = {"X-Auth-Token": LOGOUT_SERVICE_TOKEN}
        response = client.get(
            f"/user/{test_user_status.user_telegram_id}", headers=headers
        )

        assert response.status_code == 200
        assert response.json() == {
            "user_telegram_id": 123,
            "agreement_accepted": True,
            "authenticated": True,
            "login_attempt_count": 2,
            "failed_request_count": 1,
        }

    def test_get_user_status_not_found(self, db_session: Session):
        print(db_session.query(AbstractBaseModel.metadata.tables["user_status"]).all())
        headers = {"X-Auth-Token": LOGOUT_SERVICE_TOKEN}
        response = client.get("/user/123", headers=headers)

        print(response.json())
        assert response.status_code == 404
        assert response.json() == {"detail": "User not found"}

    def test_get_user_status_invalid_id(self, db_session: Session):
        headers = {"X-Auth-Token": LOGOUT_SERVICE_TOKEN}
        response = client.get("/user/abc", headers=headers)

        assert response.status_code == 422
        assert len(response.json()["detail"]) == 1
        assert response.json()["detail"][0]["type"] == "int_parsing"
        assert response.json()["detail"][0]["loc"] == ["path", "user_telegram_id"]
        assert response.json()["detail"][0]["input"] == "abc"

    def test_logout_user(self, db_session: Session):
        # Create a test UserStatus and UserNotifySettings objects
        test_user_status = UserStatus(
            user_telegram_id=321,
            agreement_accepted=True,
            authenticated=True,
            login_attempt_count=5,
            failed_request_count=0,
        )
        test_user_notify_settings = UserNotifySettings(
            user_telegram_id=321,
            marks=True,
            news=False,
            homeworks=True,
            requests=False,
        )
        db_session.add(test_user_status)
        db_session.add(test_user_notify_settings)
        db_session.commit()

        headers = {"X-Auth-Token": LOGOUT_SERVICE_TOKEN}

        response = client.get(
            f"/user/{test_user_status.user_telegram_id}", headers=headers
        )
        assert response.status_code == 200
        assert response.json() == {
            "user_telegram_id": 321,
            "agreement_accepted": True,
            "authenticated": True,
            "login_attempt_count": 5,
            "failed_request_count": 0,
        }

        response = client.post(
            f"/user/{test_user_status.user_telegram_id}/logout", headers=headers
        )

        assert response.status_code == 204
        assert response.content == b""
        assert db_session.query(UserStatus).count() == 1
        assert db_session.query(UserNotifySettings).count() == 1

        response = client.get(
            f"/user/{test_user_status.user_telegram_id}", headers=headers
        )
        assert response.status_code == 200
        assert response.json() == {
            "user_telegram_id": 321,
            "agreement_accepted": True,
            "authenticated": False,
            "login_attempt_count": 5,
            "failed_request_count": 0,
        }

        db_session.refresh(test_user_status)
        db_session.refresh(test_user_notify_settings)
        # Check that the user_notify_settings object filled with default values
        test_user_notify_settings_after = UserNotifySettings.find_one(
            db_session, user_telegram_id=test_user_status.user_telegram_id
        )
        assert test_user_notify_settings_after.marks is True
        assert test_user_notify_settings_after.news is False
        assert test_user_notify_settings_after.homeworks is False
        assert test_user_notify_settings_after.requests is False

        # Check that the user_status object authenticated field is False, but other fields are not changed
        test_user_status_after = UserStatus.find_one(
            db_session, user_telegram_id=test_user_status.user_telegram_id
        )
        print(test_user_status_after.as_dict())
        assert test_user_status_after.authenticated is False
        assert test_user_status_after.agreement_accepted is True
        assert test_user_status_after.login_attempt_count == 5
        assert test_user_status_after.failed_request_count == 0

    def test_user_double_logout(self, db_session: Session):
        # Create a test UserStatus and UserNotifySettings objects
        test_user_status = UserStatus(
            user_telegram_id=1234,
            agreement_accepted=True,
            authenticated=True,
            login_attempt_count=7,
            failed_request_count=0,
        )
        test_user_notify_settings = UserNotifySettings(
            user_telegram_id=1234,
            marks=True,
            news=False,
            homeworks=True,
            requests=True,
        )
        db_session.add(test_user_status)
        db_session.add(test_user_notify_settings)
        db_session.commit()

        headers = {"X-Auth-Token": LOGOUT_SERVICE_TOKEN}

        response = client.post(
            f"/user/{test_user_status.user_telegram_id}/logout", headers=headers
        )

        assert response.status_code == 204
        assert response.content == b""
        assert db_session.query(UserStatus).count() == 1
        assert db_session.query(UserNotifySettings).count() == 1

        response = client.post(
            f"/user/{test_user_status.user_telegram_id}/logout", headers=headers
        )

        assert response.status_code == 204
        assert response.content == b""
        assert db_session.query(UserStatus).count() == 1
        assert db_session.query(UserNotifySettings).count() == 1

        db_session.refresh(test_user_status)
        db_session.refresh(test_user_notify_settings)
        # Check that the user_notify_settings object filled with default values
        test_user_notify_settings_after = UserNotifySettings.find_one(
            db_session, user_telegram_id=test_user_status.user_telegram_id
        )
        assert test_user_notify_settings_after.marks is True
        assert test_user_notify_settings_after.news is False
        assert test_user_notify_settings_after.homeworks is False
        assert test_user_notify_settings_after.requests is False

        # Check that the user_status object authenticated field is False, but other fields are not changed
        test_user_status_after = UserStatus.find_one(
            db_session, user_telegram_id=test_user_status.user_telegram_id
        )
        assert test_user_status_after.authenticated is False
        assert test_user_status_after.agreement_accepted is True
        assert test_user_status_after.login_attempt_count == 7
        assert test_user_status_after.failed_request_count == 0

    @pytest.mark.parametrize(
        "method",
        ["post", "put", "delete", "options", "patch"],
    )
    def test_wrong_method_on_user_get(self, db_session: Session, method: str):
        headers = {"X-Auth-Token": LOGOUT_SERVICE_TOKEN}
        response = getattr(client, method)("/user/123", headers=headers)
        assert response.status_code == 405
        assert response.json() == {"detail": "Method Not Allowed"}

    @pytest.mark.parametrize(
        "method",
        ["get", "put", "delete", "options", "patch"],
    )
    def test_wrong_method_on_user_logout(self, db_session: Session, method: str):
        headers = {"X-Auth-Token": LOGOUT_SERVICE_TOKEN}
        response = client.get("/user/123/logout", headers=headers)
        assert response.status_code == 405
        assert response.json() == {"detail": "Method Not Allowed"}

    def test_logout_user_and_notify_settings_not_found(self, db_session: Session):
        headers = {"X-Auth-Token": LOGOUT_SERVICE_TOKEN}
        response = client.post("/user/123/logout", headers=headers)

        assert response.status_code == 404
        assert response.json() == {"detail": "User not found"}

    def test_logout_user_not_found_but_notify_settings_exists(
        self, db_session: Session
    ):
        # Create a test UserNotifySettings object
        test_user_notify_settings = UserNotifySettings(
            user_telegram_id=123,
            marks=True,
            news=False,
            homeworks=True,
            requests=True,
        )
        db_session.add(test_user_notify_settings)
        db_session.commit()

        headers = {"X-Auth-Token": LOGOUT_SERVICE_TOKEN}
        response = client.post("/user/123/logout", headers=headers)

        assert response.status_code == 404
        assert response.json() == {"detail": "User not found"}

    def test_logout_user_exists_but_notify_settings_not_found(
        self, db_session: Session
    ):
        # Create a test UserStatus object
        test_user_status = UserStatus(
            user_telegram_id=123,
            agreement_accepted=True,
            authenticated=True,
            login_attempt_count=2,
            failed_request_count=1,
        )
        db_session.add(test_user_status)
        db_session.commit()

        headers = {"X-Auth-Token": LOGOUT_SERVICE_TOKEN}
        response = client.post("/user/123/logout", headers=headers)

        assert response.status_code == 404
        assert response.json() == {"detail": "User settings not found"}
