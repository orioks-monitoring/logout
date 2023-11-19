from sqlalchemy import Boolean, Column, Integer

from app.models.base import AbstractBaseModel


class UserNotifySettings(AbstractBaseModel):
    __tablename__ = "user_notify_settings"

    user_telegram_id = Column(Integer, nullable=False, unique=True)
    marks = Column(Boolean, nullable=False, default=True)
    news = Column(Boolean, nullable=False, default=True)
    homeworks = Column(Boolean, nullable=False, default=True)
    requests = Column(Boolean, nullable=False, default=True)

    def fill(self, user_telegram_id: int) -> None:
        self.user_telegram_id = user_telegram_id
        self.marks = True
        self.news = False
        self.homeworks = False
        self.requests = False

    def __repr__(self) -> str:
        return f"<UserNotifySettings(user_telegram_id={self.user_telegram_id})>"
