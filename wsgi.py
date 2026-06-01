import os

from config import DATABASE_PATH
from database.db import init_db

os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
init_db()

from app import app  # noqa: E402
