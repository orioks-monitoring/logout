import logging
import os

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///database.sqlite3")


LOGOUT_SERVICE_TOKEN = os.getenv("LOGOUT_SERVICE_TOKEN", "SecretToken")
LOGOUT_SERVICE_HEADER_NAME = os.getenv("LOGOUT_SERVICE_HEADER_NAME", "X-Auth-Token")

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)-8s %(pathname)s:%(lineno)d - %(message)s",
    datefmt="%H:%M:%S %d.%m.%Y",
)

TEST_DATABASE_URL = "sqlite:///:memory:"
