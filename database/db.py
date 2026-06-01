import os
import sqlite3

from config import DATABASE_PATH


def get_db():
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    with open(schema_path, encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.commit()

    admin = conn.execute(
        "SELECT id FROM users WHERE username = ?", ("admin",)
    ).fetchone()
    if not admin:
        from werkzeug.security import generate_password_hash

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
    conn.close()


def close_db(conn):
    conn.close()
