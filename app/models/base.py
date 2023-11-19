from abc import abstractmethod
from typing import Optional, final

from sqlalchemy import Column, DateTime, Integer, func
from sqlalchemy.orm import Session

from app.models.database import DeclarativeModelBase


class AbstractBaseModel(DeclarativeModelBase):
    """
    Base model for all models in the project. Contains common fields and methods.
    """

    __abstract__ = True

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    @classmethod
    @final
    def find_one(cls, session: Session, **query) -> Optional["AbstractBaseModel"]:
        return session.query(cls).filter_by(**query).one_or_none()

    @classmethod
    @final
    def delete(cls, db: Session, **query) -> None:
        db.query(cls).filter_by(**query).delete()
        db.commit()

    @abstractmethod
    def fill(self, *args, **kwargs) -> None:
        pass

    @final
    def as_dict(self) -> dict:
        return {
            column.key: getattr(self, attr)
            for attr, column in self.__mapper__.c.items()
        }
