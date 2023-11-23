from sqlalchemy import Boolean, CheckConstraint, Column, Integer

from app.models.base import AbstractBaseModel


class UserStatus(AbstractBaseModel):
    __tablename__ = "user_status"

    user_telegram_id = Column(Integer, nullable=False, unique=True, index=True)
    agreement_accepted = Column(Boolean, nullable=False, default=False)
    authenticated = Column(Boolean, nullable=False, default=False)
    login_attempt_count = Column(Integer, nullable=False, default=0)
    failed_request_count = Column(Integer, nullable=False, default=0)

    __table_args__ = (
        CheckConstraint(
            login_attempt_count >= 0, name="check_login_attempt_count_non_negative"
        ),
        CheckConstraint(
            failed_request_count >= 0, name="check_failed_request_count_non_negative"
        ),
        {},
    )

    def fill(self, user_telegram_id: int) -> None:
        self.user_telegram_id = user_telegram_id
        self.agreement_accepted = False
        self.authenticated = False
        self.login_attempt_count = 0
        self.failed_request_count = 0

    def __repr__(self) -> str:
        return f"<UserStatus(user_telegram_id={self.user_telegram_id})>"
