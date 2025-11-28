import sqlite3
import json
import os
import hashlib
import time
from typing import Optional, Dict

DB_PATH = os.path.join(os.path.dirname(__file__), "tutorquest.db")

def _get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    conn = _get_conn()
    c = conn.cursor()
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

def create_user(username: str, password: str) -> Optional[int]:
    conn = _get_conn()
    c = conn.cursor()
    try:
        pwd = _hash_password(password)
        now = int(time.time())
        c.execute("INSERT INTO users (username, password_hash, created_at, last_seen) VALUES (?, ?, ?, ?)",
                  (username, pwd, now, now))
        conn.commit()
        user_id = c.lastrowid
        return user_id
    except Exception:
        return None
    finally:
        conn.close()

def authenticate_user(username: str, password: str) -> Optional[int]:
    conn = _get_conn()
    c = conn.cursor()
    try:
        c.execute("SELECT id, password_hash FROM users WHERE username = ?", (username,))
        row = c.fetchone()
        if not row:
            return None
        user_id, stored = row
        if _verify_password(stored, password):
            c.execute("UPDATE users SET last_seen = ? WHERE id = ?", (int(time.time()), user_id))
            conn.commit()
            return user_id
        return None
    finally:
        conn.close()

def get_user_state(user_id: int) -> Optional[Dict]:
    conn = _get_conn()
    c = conn.cursor()
    try:
        c.execute("SELECT state_json FROM users WHERE id = ?", (user_id,))
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
    try:
        payload = json.dumps(state)
        c.execute("UPDATE users SET state_json = ?, last_seen = ? WHERE id = ?", (payload, int(time.time()), user_id))
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()
