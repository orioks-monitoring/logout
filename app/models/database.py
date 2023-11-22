from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.config import DATABASE_URL

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
    if DATABASE_URL.startswith("sqlite")
    else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

DeclarativeModelBase = declarative_base()


def get_db() -> SessionLocal:
    """Get database session. Use this function in FastAPI path operation functions. Injections are used."""
    database = SessionLocal()
    try:
        yield database
    finally:
        database.close()
