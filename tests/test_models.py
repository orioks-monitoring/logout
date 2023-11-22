from typing import Generator

import pytest
from sqlalchemy import Column, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.testclient import TestClient

from app.config import TEST_DATABASE_URL
from app.main import app
from app.models.base import AbstractBaseModel
from app.models.database import get_db

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


class TestModels:
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
        from app.models.users.user_status import UserStatus

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

    def test_base_model_is_abstract(self):
        """Test that the AbstractBaseModel class is abstract."""
        abstract_model = AbstractBaseModel()
        assert abstract_model.__abstract__
        assert isinstance(abstract_model.id, Column)

    def test_user_status_create(self, db_session: Session):
        """Test that a UserStatus object can be created and saved to the database."""
        from app.models.users.user_status import UserStatus

        # Create a test UserStatus object
        test_user_status = UserStatus(user_telegram_id=111)

        # Save the UserStatus object
        db_session.add(test_user_status)
        db_session.commit()

        # Retrieve the UserStatus object from the database
        retrieved_user_status = UserStatus.find_one(db_session, user_telegram_id=111)

        assert retrieved_user_status is not None
        assert retrieved_user_status.user_telegram_id == 111

    def test_user_notify_settings_create(self, db_session: Session):
        """Test that a UserNotifySettings object can be created and saved to the database."""
        from app.models.users.user_notify_settings import UserNotifySettings

        # Create a test UserNotifySettings object
        test_user_notify_settings = UserNotifySettings(user_telegram_id=222)

        # Save the UserNotifySettings object
        db_session.add(test_user_notify_settings)
        db_session.commit()

        # Retrieve the UserNotifySettings object from the database
        retrieved_user_notify_settings = UserNotifySettings.find_one(
            db_session, user_telegram_id=222
        )

        assert retrieved_user_notify_settings is not None
        assert retrieved_user_notify_settings.user_telegram_id == 222

    def test_user_status_delete(self, db_session: Session):
        """Test that a UserStatus object can be deleted from the database."""
        from app.models.users.user_status import UserStatus

        # Create a test UserStatus object
        test_user_status = UserStatus(user_telegram_id=333)

        # Save the UserStatus object
        db_session.add(test_user_status)
        db_session.commit()

        # Delete the UserStatus object
        test_user_status.delete(db_session)

        # Retrieve the UserStatus object from the database
        retrieved_user_status = UserStatus.find_one(db_session, user_telegram_id=333)

        assert retrieved_user_status is None

    def test_user_notify_settings_delete(self, db_session: Session):
        """Test that a UserNotifySettings object can be deleted from the database."""
        from app.models.users.user_notify_settings import UserNotifySettings

        # Create a test UserNotifySettings object
        test_user_notify_settings = UserNotifySettings(user_telegram_id=444)

        # Save the UserNotifySettings object
        db_session.add(test_user_notify_settings)
        db_session.commit()

        # Delete the UserNotifySettings object
        test_user_notify_settings.delete(db_session)

        # Retrieve the UserNotifySettings object from the database
        retrieved_user_notify_settings = UserNotifySettings.find_one(
            db_session, user_telegram_id=444
        )

        assert retrieved_user_notify_settings is None

    def test_user_status_fill(self, db_session: Session):
        """Test that a UserStatus object can be reset."""
        from app.models.users.user_status import UserStatus

        # Create a test UserStatus object
        test_user_status = UserStatus(user_telegram_id=555)

        # Save the UserStatus object
        db_session.add(test_user_status)
        db_session.commit()

        # Reset the UserStatus object
        test_user_status.fill(user_telegram_id=555)
        db_session.add(test_user_status)
        db_session.commit()

        # Retrieve the UserStatus object from the database
        retrieved_user_status = UserStatus.find_one(db_session, user_telegram_id=555)

        assert retrieved_user_status is not None
        assert retrieved_user_status.user_telegram_id == 555
        assert retrieved_user_status.agreement_accepted is False
        assert retrieved_user_status.authenticated is False
        assert retrieved_user_status.login_attempt_count == 0
        assert retrieved_user_status.failed_request_count == 0

    def test_user_notify_settings_fill(self, db_session: Session):
        """Test that a UserNotifySettings object can be reset."""
        from app.models.users.user_notify_settings import UserNotifySettings

        # Create a test UserNotifySettings object
        test_user_notify_settings = UserNotifySettings(user_telegram_id=666)

        # Save the UserNotifySettings object
        db_session.add(test_user_notify_settings)
        db_session.commit()

        # Reset the UserNotifySettings object
        test_user_notify_settings.fill(user_telegram_id=666)
        db_session.add(test_user_notify_settings)
        db_session.commit()

        # Retrieve the UserNotifySettings object from the database
        retrieved_user_notify_settings = UserNotifySettings.find_one(
            db_session, user_telegram_id=666
        )

        assert retrieved_user_notify_settings is not None
        assert retrieved_user_notify_settings.user_telegram_id == 666
        assert retrieved_user_notify_settings.marks is True
        assert retrieved_user_notify_settings.news is False
        assert retrieved_user_notify_settings.homeworks is False
        assert retrieved_user_notify_settings.requests is False

    def test_transactional_reset_user(self, db_session: Session):
        """Test that a UserStatus object and a UserNotifySettings object can be reset transactional."""
        from app.managers import reset_user
        from app.models.users.user_notify_settings import UserNotifySettings
        from app.models.users.user_status import UserStatus

        # Create a test UserStatus object
        test_user_status = UserStatus(user_telegram_id=777)

        # Create a test UserNotifySettings object
        test_user_notify_settings = UserNotifySettings(user_telegram_id=777)

        # Save the UserStatus and UserNotifySettings objects
        db_session.add(test_user_status)
        db_session.add(test_user_notify_settings)
        db_session.commit()

        # Reset the UserStatus and UserNotifySettings objects transactional
        reset_user(
            db_session,
            test_user_status,
            test_user_notify_settings,
            user_telegram_id=777,
        )

        # Retrieve the UserStatus and UserNotifySettings objects from the database
        retrieved_user_status = UserStatus.find_one(db_session, user_telegram_id=777)
        retrieved_user_notify_settings = UserNotifySettings.find_one(
            db_session, user_telegram_id=777
        )

        assert retrieved_user_status is not None
        assert retrieved_user_status.user_telegram_id == 777
        assert retrieved_user_status.agreement_accepted is False
        assert retrieved_user_status.authenticated is False
        assert retrieved_user_status.login_attempt_count == 0
        assert retrieved_user_status.failed_request_count == 0

        assert retrieved_user_notify_settings is not None
        assert retrieved_user_notify_settings.user_telegram_id == 777
        assert retrieved_user_notify_settings.marks is True
        assert retrieved_user_notify_settings.news is False
        assert retrieved_user_notify_settings.homeworks is False
        assert retrieved_user_notify_settings.requests is False

    def test_transaction_failure_reset_user(self, db_session: Session):
        """Test that a UserStatus object and a UserNotifySettings object can be reset transactional.
        Test that the transaction is rolled back if an exception occurs.
        """
        from pydantic import PositiveInt

        from app.models.users.user_notify_settings import UserNotifySettings
        from app.models.users.user_status import UserStatus

        def reset_user_with_raise(
            db: Session,
            user: UserStatus,
            user_settings: UserNotifySettings,
            user_telegram_id: PositiveInt,
        ) -> None:
            """
            Transactional function for reset user status and user notify settings.
            """

            with db.begin():
                user.authenticated = False
                db.add(user)
                user_settings.fill(user_telegram_id=user_telegram_id)
                db.add(user_settings)
                raise Exception("Test exception")
                db.commit()

            db.refresh(user)
            db.refresh(user_settings)

        # Create a test UserStatus object
        test_user_status = UserStatus(
            user_telegram_id=888, failed_request_count=3, login_attempt_count=5
        )

        # Create a test UserNotifySettings object
        test_user_notify_settings = UserNotifySettings(user_telegram_id=888)

        # Save the UserStatus and UserNotifySettings objects
        db_session.add(test_user_status)
        db_session.add(test_user_notify_settings)
        db_session.commit()

        # Reset the UserStatus and UserNotifySettings objects transactional
        with pytest.raises(Exception):
            reset_user_with_raise(
                db_session,
                test_user_status,
                test_user_notify_settings,
                user_telegram_id=888,
            )

        # Retrieve the UserStatus and UserNotifySettings objects from the database
        retrieved_user_status = UserStatus.find_one(db_session, user_telegram_id=888)
        retrieved_user_notify_settings = UserNotifySettings.find_one(
            db_session, user_telegram_id=888
        )

        assert retrieved_user_status is not None
        assert retrieved_user_status.user_telegram_id == 888
        assert retrieved_user_status.agreement_accepted is False
        assert retrieved_user_status.authenticated is False
        assert retrieved_user_status.login_attempt_count == 5
        assert retrieved_user_status.failed_request_count == 3

        assert retrieved_user_notify_settings is not None
        assert retrieved_user_notify_settings.user_telegram_id == 888
        assert retrieved_user_notify_settings.marks is True
        assert retrieved_user_notify_settings.news is True
        assert retrieved_user_notify_settings.homeworks is True
        assert retrieved_user_notify_settings.requests is True

    @pytest.mark.parametrize(
        "user_status_data",
        [
            {
                "user_telegram_id": 1,
                "agreement_accepted": True,
                "authenticated": True,
                "login_attempt_count": 1,
                "failed_request_count": 1,
            },
            {
                "user_telegram_id": 2,
                "agreement_accepted": False,
                "authenticated": False,
                "login_attempt_count": 2,
                "failed_request_count": 2,
            },
            {
                "user_telegram_id": 3,
                "agreement_accepted": True,
                "authenticated": False,
                "login_attempt_count": 3,
                "failed_request_count": 3,
            },
            {
                "user_telegram_id": 4,
                "agreement_accepted": False,
                "authenticated": True,
                "login_attempt_count": 4,
                "failed_request_count": 4,
            },
            {
                "user_telegram_id": 5,
                "agreement_accepted": True,
                "authenticated": True,
                "login_attempt_count": 5,
                "failed_request_count": 5,
            },
        ],
    )
    def test_create_user_status_model_with_parametrize_data(
        self, db_session, user_status_data: dict
    ):
        """Test that a UserStatus object can be created with random data."""
        from app.models.users.user_status import UserStatus

        # Create a test UserStatus object
        test_user_status = UserStatus(**user_status_data)

        # Save the UserStatus object
        db_session.add(test_user_status)
        db_session.commit()

        # Retrieve the UserStatus object from the database
        retrieved_user_status = UserStatus.find_one(
            db_session, user_telegram_id=user_status_data["user_telegram_id"]
        )

        assert retrieved_user_status is not None
        assert (
            retrieved_user_status.user_telegram_id
            == user_status_data["user_telegram_id"]
        )
        assert (
            retrieved_user_status.agreement_accepted
            == user_status_data["agreement_accepted"]
        )
        assert retrieved_user_status.authenticated == user_status_data["authenticated"]
        assert (
            retrieved_user_status.login_attempt_count
            == user_status_data["login_attempt_count"]
        )
        assert (
            retrieved_user_status.failed_request_count
            == user_status_data["failed_request_count"]
        )

    @pytest.mark.parametrize(
        "user_notify_settings_data",
        [
            {
                "user_telegram_id": 1,
                "marks": True,
                "news": True,
                "homeworks": True,
                "requests": True,
            },
            {
                "user_telegram_id": 2,
                "marks": False,
                "news": False,
                "homeworks": False,
                "requests": False,
            },
            {
                "user_telegram_id": 3,
                "marks": True,
                "news": False,
                "homeworks": False,
                "requests": False,
            },
            {
                "user_telegram_id": 4,
                "marks": False,
                "news": True,
                "homeworks": False,
                "requests": False,
            },
            {
                "user_telegram_id": 5,
                "marks": True,
                "news": True,
                "homeworks": False,
                "requests": False,
            },
            {
                "user_telegram_id": 6,
                "marks": True,
                "news": True,
                "homeworks": True,
                "requests": True,
            },
        ],
    )
    def test_create_user_notify_settings_model_with_parametrize_data(
        self, db_session, user_notify_settings_data: dict
    ):
        """Test that a UserNotifySettings object can be created with random data."""
        from app.models.users.user_notify_settings import UserNotifySettings

        # Create a test UserNotifySettings object
        test_user_notify_settings = UserNotifySettings(**user_notify_settings_data)

        # Save the UserNotifySettings object
        db_session.add(test_user_notify_settings)
        db_session.commit()

        # Retrieve the UserNotifySettings object from the database
        retrieved_user_notify_settings = UserNotifySettings.find_one(
            db_session, user_telegram_id=user_notify_settings_data["user_telegram_id"]
        )

        assert retrieved_user_notify_settings is not None
        assert (
            retrieved_user_notify_settings.user_telegram_id
            == user_notify_settings_data["user_telegram_id"]
        )
        assert (
            retrieved_user_notify_settings.marks == user_notify_settings_data["marks"]
        )
        assert retrieved_user_notify_settings.news == user_notify_settings_data["news"]
        assert (
            retrieved_user_notify_settings.homeworks
            == user_notify_settings_data["homeworks"]
        )
        assert (
            retrieved_user_notify_settings.requests
            == user_notify_settings_data["requests"]
        )

    def test_user_status_repr(self, db_session: Session):
        """Test that the __repr__ method of the UserStatus model works correctly."""
        from app.models.users.user_status import UserStatus

        # Create a test UserStatus object
        test_user_status = UserStatus(user_telegram_id=999)

        # Save the UserStatus object
        db_session.add(test_user_status)
        db_session.commit()

        # Retrieve the UserStatus object from the database
        retrieved_user_status = UserStatus.find_one(db_session, user_telegram_id=999)

        assert (
            repr(retrieved_user_status)
            == f"<UserStatus(user_telegram_id={retrieved_user_status.user_telegram_id})>"
        )

    def test_user_notify_settings_repr(self, db_session: Session):
        """Test that the __repr__ method of the UserNotifySettings model works correctly."""
        from app.models.users.user_notify_settings import UserNotifySettings

        # Create a test UserNotifySettings object
        test_user_notify_settings = UserNotifySettings(user_telegram_id=1000)

        # Save the UserNotifySettings object
        db_session.add(test_user_notify_settings)
        db_session.commit()

        # Retrieve the UserNotifySettings object from the database
        retrieved_user_notify_settings = UserNotifySettings.find_one(
            db_session, user_telegram_id=1000
        )

        assert (
            repr(retrieved_user_notify_settings)
            == f"<UserNotifySettings(user_telegram_id={retrieved_user_notify_settings.user_telegram_id})>"
        )

    def test_user_status_constraints_unique(self, db_session: Session):
        """Test that the user_telegram_id column of the UserStatus model is unique."""
        from app.models.users.user_status import UserStatus

        # Create a test UserStatus object
        test_user_status = UserStatus(user_telegram_id=111)

        # Save the UserStatus object
        db_session.add(test_user_status)
        db_session.commit()

        # Create a test UserStatus object with the same user_telegram_id
        test_user_status = UserStatus(user_telegram_id=111)

        # Save the UserStatus object
        db_session.add(test_user_status)

        with pytest.raises(Exception):
            db_session.commit()

    def test_user_status_constraints_non_negative(self, db_session: Session):
        """Test that the login_attempt_count and failed_request_count columns of the UserStatus model are
        non-negative."""
        from sqlalchemy.exc import PendingRollbackError

        from app.models.users.user_status import UserStatus

        # Create a test UserStatus object with negative login_attempt_count
        test_user_status = UserStatus(user_telegram_id=222, login_attempt_count=-1)

        # Save the UserStatus object
        db_session.add(test_user_status)

        with pytest.raises(Exception):
            db_session.commit()

        # Create a test UserStatus object with negative failed_request_count
        test_user_status = UserStatus(user_telegram_id=333, failed_request_count=-1)

        # Save the UserStatus object
        db_session.add(test_user_status)

        with pytest.raises(PendingRollbackError):
            db_session.commit()
