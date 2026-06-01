import os
import re
import sqlite3

from config import DATABASE_PATH, DATABASE_URL

USE_POSTGRES = bool(DATABASE_URL and DATABASE_URL.strip())


def _pg_url():
    url = DATABASE_URL.strip()
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


class DbCursor:
    """Wraps DB cursor so fetchone/fetchall and lastrowid work for SQLite and PostgreSQL."""

    def __init__(self, cursor, is_postgres):
        self._cursor = cursor
        self._is_postgres = is_postgres
        self._last_id = None

    @property
    def lastrowid(self):
        if self._is_postgres:
            return self._last_id
        return self._cursor.lastrowid

    def fetchone(self):
        row = self._cursor.fetchone()
        if row is None:
            return None
        if self._is_postgres and hasattr(row, "keys"):
            return row
        return row

    def fetchall(self):
        return self._cursor.fetchall()


class DbConnection:
    def __init__(self, conn, is_postgres=False):
        self._conn = conn
        self._is_postgres = is_postgres

    def execute(self, sql, params=()):
        if self._is_postgres:
            import psycopg2.extras

            sql = sql.replace("?", "%s")
            is_insert = sql.strip().upper().startswith("INSERT")
            if is_insert and "RETURNING" not in sql.upper():
                sql = sql.rstrip().rstrip(";") + " RETURNING id"

            cur = self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute(sql, params)
            wrapper = DbCursor(cur, True)
            if is_insert:
                row = cur.fetchone()
                wrapper._last_id = row["id"] if row else None
            return wrapper

        cur = self._conn.cursor()
        cur.execute(sql, params)
        return DbCursor(cur, False)

    def commit(self):
        self._conn.commit()

    def close(self):
        self._conn.close()

    def executescript(self, script):
        if self._is_postgres:
            raise RuntimeError("Use init_db() for PostgreSQL schema setup")
        self._conn.executescript(script)


def get_db():
    if USE_POSTGRES:
        import psycopg2

        raw = psycopg2.connect(_pg_url())
        return DbConnection(raw, is_postgres=True)

    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    raw = sqlite3.connect(DATABASE_PATH)
    raw.row_factory = sqlite3.Row
    raw.execute("PRAGMA foreign_keys = ON")
    return DbConnection(raw, is_postgres=False)


def _run_postgres_schema(conn):
    schema_path = os.path.join(os.path.dirname(__file__), "schema_postgres.sql")
    with open(schema_path, encoding="utf-8") as f:
        script = f.read()
    statements = [
        s.strip()
        for s in re.split(r";\s*\n", script)
        if s.strip() and not s.strip().startswith("--")
    ]
    for stmt in statements:
        if stmt:
            conn.execute(stmt)
    conn.commit()


def init_db():
    conn = get_db()

    if USE_POSTGRES:
        _run_postgres_schema(conn)
    else:
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
