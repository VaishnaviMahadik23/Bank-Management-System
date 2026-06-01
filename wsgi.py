import os

from config import DATABASE_PATH, DATABASE_URL
from database.db import init_db

if not (DATABASE_URL and DATABASE_URL.strip()):
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)

init_db()

from app import app  # noqa: E402
