"""Database access layer for interviews and users — PostgreSQL backend."""

import json
import uuid
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

import psycopg2
import psycopg2.extras

from app.config import DATABASE_URL


@contextmanager
def get_db():
    """Context manager that yields a psycopg2 connection and commits/rolls back."""
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """Create tables if they don't exist."""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id          TEXT PRIMARY KEY,
                    username    TEXT UNIQUE NOT NULL,
                    email       TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at  TIMESTAMPTZ DEFAULT NOW()
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS interviews (
                    id                   TEXT PRIMARY KEY,
                    user_id              TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    candidate_name       TEXT NOT NULL,
                    candidate_email      TEXT,
                    position             TEXT NOT NULL,
                    position_description TEXT,
                    language             TEXT NOT NULL,
                    duration_minutes     INTEGER NOT NULL,
                    started_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    finished_at          TIMESTAMPTZ,
                    feedback             TEXT,
                    messages             JSONB NOT NULL DEFAULT '[]'::jsonb,
                    created_at           TIMESTAMPTZ DEFAULT NOW()
                )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_interviews_user ON interviews(user_id)")


# ---------------------------------------------------------------------------
# UserDB
# ---------------------------------------------------------------------------

class UserDB:
    """User CRUD operations."""

    @staticmethod
    def create_user(username: str, email: str, password_hash: str) -> str:
        user_id = str(uuid.uuid4())
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO users (id, username, email, password_hash) VALUES (%s, %s, %s, %s)",
                    (user_id, username, email, password_hash),
                )
        return user_id

    @staticmethod
    def _row(cur, query: str, params: tuple) -> Optional[Dict[str, Any]]:
        cur.execute(query, params)
        row = cur.fetchone()
        if row is None:
            return None
        cols = [d.name for d in cur.description]
        return dict(zip(cols, row))

    @staticmethod
    def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
        with get_db() as conn:
            with conn.cursor() as cur:
                return UserDB._row(cur, "SELECT * FROM users WHERE username = %s", (username,))

    @staticmethod
    def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
        with get_db() as conn:
            with conn.cursor() as cur:
                return UserDB._row(cur, "SELECT * FROM users WHERE email = %s", (email,))

    @staticmethod
    def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
        with get_db() as conn:
            with conn.cursor() as cur:
                return UserDB._row(cur, "SELECT * FROM users WHERE id = %s", (user_id,))


# ---------------------------------------------------------------------------
# InterviewDB
# ---------------------------------------------------------------------------

class InterviewDB:
    """Interview CRUD operations."""

    @staticmethod
    def create_interview(
        user_id: str,
        candidate_name: str,
        candidate_email: str,
        position: str,
        language: str,
        duration_minutes: int,
        position_description: Optional[str] = None,
    ) -> str:
        interview_id = str(uuid.uuid4())
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO interviews
                        (id, user_id, candidate_name, candidate_email, position,
                         position_description, language, duration_minutes)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        interview_id, user_id, candidate_name, candidate_email,
                        position, position_description, language, duration_minutes,
                    ),
                )
        return interview_id

    @staticmethod
    def _row(cur, query: str, params: tuple) -> Optional[Dict[str, Any]]:
        cur.execute(query, params)
        row = cur.fetchone()
        if row is None:
            return None
        cols = [d.name for d in cur.description]
        d = dict(zip(cols, row))
        # psycopg2 returns JSONB as a Python object already; normalise to list
        if "messages" in d and isinstance(d["messages"], str):
            d["messages"] = json.loads(d["messages"])
        return d

    @staticmethod
    def get_interview(interview_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        with get_db() as conn:
            with conn.cursor() as cur:
                return InterviewDB._row(
                    cur,
                    "SELECT * FROM interviews WHERE id = %s AND user_id = %s",
                    (interview_id, user_id),
                )

    @staticmethod
    def list_interviews(user_id: str) -> List[Dict[str, Any]]:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, candidate_name, position, language, duration_minutes,
                           started_at, finished_at, feedback
                    FROM interviews
                    WHERE user_id = %s
                    ORDER BY started_at DESC
                    """,
                    (user_id,),
                )
                cols = [d.name for d in cur.description]
                return [dict(zip(cols, row)) for row in cur.fetchall()]

    @staticmethod
    def update_interview(
        interview_id: str,
        user_id: str,
        finished_at: Optional[str] = None,
        feedback: Optional[str] = None,
        messages: Optional[Any] = None,
    ) -> None:
        updates: List[str] = []
        params: List[Any] = []

        if finished_at is not None:
            updates.append("finished_at = %s")
            params.append(finished_at)
        if feedback is not None:
            updates.append("feedback = %s")
            params.append(feedback)
        if messages is not None:
            updates.append("messages = %s::jsonb")
            params.append(json.dumps(messages) if not isinstance(messages, str) else messages)

        if not updates:
            return

        params += [interview_id, user_id]
        sql = f"UPDATE interviews SET {', '.join(updates)} WHERE id = %s AND user_id = %s"
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)

    # Convenience aliases used by main.py
    finish_interview = update_interview

    @staticmethod
    def get_messages(interview_id: str, user_id: str) -> List[Dict[str, Any]]:
        interview = InterviewDB.get_interview(interview_id, user_id)
        if not interview:
            return []
        msgs = interview.get("messages", [])
        if isinstance(msgs, str):
            try:
                msgs = json.loads(msgs)
            except json.JSONDecodeError:
                msgs = []
        return msgs

    @staticmethod
    def add_message(interview_id: str, user_id: str, role: str, content: str) -> None:
        messages = InterviewDB.get_messages(interview_id, user_id)
        messages.append({"role": role, "content": content, "timestamp": datetime.utcnow().isoformat() + "Z"})
        InterviewDB.update_interview(interview_id, user_id, messages=messages)

