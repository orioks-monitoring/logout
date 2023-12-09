from abc import abstractmethod
from typing import Optional, final

from sqlalchemy import Column, DateTime, Integer, func
from sqlalchemy.orm import Session

from app.models.sql_database import DeclarativeModelBase


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
    def delete(cls, db_session: Session, **query) -> None:
        db_session.query(cls).filter_by(**query).delete()
        db_session.commit()

    @abstractmethod
    def fill(self, *args, **kwargs) -> None:
        pass

    # @classmethod
    # @final
    # def create(cls, db_session: Session, with_commit: bool = True, *args, **kwargs) -> "AbstractBaseModel":
    #     instance = cls(*args, **kwargs)
    #     db_session.add(instance)
    #     if with_commit:
    #         db_session.commit()
    #     return instance

    @final
    def as_dict(self) -> dict:
        return {
            column.key: getattr(self, attr)
            for attr, column in self.__mapper__.c.items()
        }
