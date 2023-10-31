import logging
import os

from dotenv import load_dotenv
from sqlalchemy.orm.scoping import ScopedSession

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///database.sqlite3")


def initialize_database() -> ScopedSession:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import scoped_session, sessionmaker

    engine = create_engine(DATABASE_URL)
    return scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))


db_session = initialize_database()

SERVICE_TOKEN = os.getenv("SERVICE_TOKEN", "SecretToken")

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)-8s %(pathname)s:%(lineno)d - %(message)s",
    datefmt="%H:%M:%S %d.%m.%Y",
)
