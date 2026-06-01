import os
import sqlite3
import uuid
from contextlib import contextmanager

from config import DATABASE_PATH


def init_db():
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    schema_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "database", "schema.sql"
    )
    with get_connection() as conn:
        with open(schema_path, encoding="utf-8") as f:
            conn.executescript(f.read())
        conn.commit()
        _seed_admin(conn)


def _seed_admin(conn):
    from werkzeug.security import generate_password_hash

    row = conn.execute("SELECT id FROM users WHERE username = ?", ("admin",)).fetchone()
    if row:
        return
    conn.execute(
        """INSERT INTO users (username, email, password_hash, full_name, role)
           VALUES (?, ?, ?, ?, ?)""",
        (
            "admin",
            "admin@bank.local",
            generate_password_hash("admin123"),
            "System Administrator",
            "admin",
        ),
    )
    conn.commit()


@contextmanager
def get_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
    finally:
        conn.close()


def generate_account_number():
    return f"ACC{uuid.uuid4().hex[:10].upper()}"


def generate_transaction_ref():
    return f"TXN{uuid.uuid4().hex[:12].upper()}"


def log_audit(conn, user_id, action, details=None, ip=None):
    conn.execute(
        "INSERT INTO audit_logs (user_id, action, details, ip_address) VALUES (?, ?, ?, ?)",
        (user_id, action, details, ip),
    )
