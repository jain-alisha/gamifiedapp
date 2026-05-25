import json
import os
import hashlib
import time
from typing import Optional, Dict

_DATABASE_URL = os.environ.get("DATABASE_URL")

def _get_conn():
    if _DATABASE_URL:
        import psycopg2
        return psycopg2.connect(_DATABASE_URL)
    import sqlite3
    db_path = os.path.join(os.path.dirname(__file__), "tutorquest.db")
    return sqlite3.connect(db_path, check_same_thread=False)

def _is_pg():
    return bool(_DATABASE_URL)

def init_db():
    conn = _get_conn()
    c = conn.cursor()
    if _is_pg():
        c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            state_json TEXT,
            created_at BIGINT,
            last_seen BIGINT
        )
        """)
    else:
        c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            state_json TEXT,
            created_at INTEGER,
            last_seen INTEGER
        )
        """)
    conn.commit()
    conn.close()

def _hash_password(password: str, salt: Optional[bytes] = None) -> str:
    if salt is None:
        salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return salt.hex() + "$" + dk.hex()

def _verify_password(stored: str, password: str) -> bool:
    try:
        salt_hex, dk_hex = stored.split("$")
        salt = bytes.fromhex(salt_hex)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
        return dk.hex() == dk_hex
    except Exception:
        return False

def _ph(n: int = 1) -> str:
    """Return the right placeholder for the current backend."""
    return "%s" if _is_pg() else "?"

def create_user(username: str, password: str) -> Optional[int]:
    conn = _get_conn()
    c = conn.cursor()
    p = _ph()
    try:
        pwd = _hash_password(password)
        now = int(time.time())
        if _is_pg():
            c.execute(
                f"INSERT INTO users (username, password_hash, created_at, last_seen) VALUES ({p},{p},{p},{p}) RETURNING id",
                (username, pwd, now, now)
            )
            user_id = c.fetchone()[0]
        else:
            c.execute(
                f"INSERT INTO users (username, password_hash, created_at, last_seen) VALUES ({p},{p},{p},{p})",
                (username, pwd, now, now)
            )
            user_id = c.lastrowid
        conn.commit()
        return user_id
    except Exception:
        return None
    finally:
        conn.close()

def authenticate_user(username: str, password: str) -> Optional[int]:
    conn = _get_conn()
    c = conn.cursor()
    p = _ph()
    try:
        c.execute(f"SELECT id, password_hash FROM users WHERE username = {p}", (username,))
        row = c.fetchone()
        if not row:
            return None
        user_id, stored = row
        if _verify_password(stored, password):
            c.execute(f"UPDATE users SET last_seen = {p} WHERE id = {p}", (int(time.time()), user_id))
            conn.commit()
            return user_id
        return None
    finally:
        conn.close()

def get_user_state(user_id: int) -> Optional[Dict]:
    conn = _get_conn()
    c = conn.cursor()
    p = _ph()
    try:
        c.execute(f"SELECT state_json FROM users WHERE id = {p}", (user_id,))
        row = c.fetchone()
        if not row or row[0] is None:
            return None
        return json.loads(row[0])
    except Exception:
        return None
    finally:
        conn.close()

def save_user_state(user_id: int, state: Dict) -> bool:
    conn = _get_conn()
    c = conn.cursor()
    p = _ph()
    try:
        payload = json.dumps(state)
        c.execute(f"UPDATE users SET state_json = {p}, last_seen = {p} WHERE id = {p}", (payload, int(time.time()), user_id))
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()
