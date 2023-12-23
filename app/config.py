import logging
import os

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///database.sqlite3")
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://admin:admin@localhost:27017")

LOGIN_LOGOUT_SERVICE_TOKEN = os.getenv("LOGIN_LOGOUT_SERVICE_TOKEN", "SecretToken")
LOGIN_LOGOUT_SERVICE_HEADER_NAME = "x-auth-token"

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)-8s %(pathname)s:%(lineno)d - %(message)s",
    datefmt="%H:%M:%S %d.%m.%Y",
)

TEST_DATABASE_URL = "sqlite:///:memory:"
