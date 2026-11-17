from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal, Optional
from uuid import uuid4

from .config import SESSIONS_DIR


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Message:
    role: Literal["assistant", "user", "system"]
    content: str
    timestamp: str = field(default_factory=lambda: utc_now().isoformat())


@dataclass
class InterviewSession:
    interview_id: str
    candidate_name: str
    position: str
    language: Literal["es", "en"]
    duration_minutes: int
    started_at: str
    finished_at: Optional[str] = None
    feedback: Optional[str] = None
    messages: list[Message] = field(default_factory=list)

    @property
    def ends_at(self) -> datetime:
        started = datetime.fromisoformat(self.started_at)
        return started + timedelta(minutes=self.duration_minutes)


class SessionStore:
    def __init__(self, sessions_dir: Path = SESSIONS_DIR):
        self.sessions_dir = sessions_dir
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    def _session_path(self, interview_id: str) -> Path:
        return self.sessions_dir / f"{interview_id}.json"

    def create(
        self,
        candidate_name: str,
        position: str,
        language: Literal["es", "en"],
        duration_minutes: int,
    ) -> InterviewSession:
        session = InterviewSession(
            interview_id=str(uuid4()),
            candidate_name=candidate_name.strip(),
            position=position.strip(),
            language=language,
            duration_minutes=duration_minutes,
            started_at=utc_now().isoformat(),
        )
        self.save(session)
        return session

    def save(self, session: InterviewSession) -> None:
        payload = asdict(session)
        payload["messages"] = [asdict(m) for m in session.messages]
        self._session_path(session.interview_id).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def load(self, interview_id: str) -> InterviewSession:
        print(f"Loading session for interview_id={interview_id}")
        path = self._session_path(interview_id)
        if not path.exists():
            raise FileNotFoundError(f"Session not found: {interview_id}")
        
        print(f"Session file path: {path}")
        data = json.loads(path.read_text(encoding="utf-8"))
        
        print(f"Session data loaded: {data}")
        messages = [Message(**m) for m in data.get("messages", [])]
        
        print(f"Session messages loaded: {messages}")
        return InterviewSession(
            interview_id=data["interview_id"],
            candidate_name=data["candidate_name"],
            position=data["position"],
            language=data["language"],
            duration_minutes=data["duration_minutes"],
            started_at=data["started_at"],
            finished_at=data.get("finished_at"),
            feedback=data.get("feedback"),
            messages=messages,
        )

    def export_json_path(self, interview_id: str) -> Path:
        path = self._session_path(interview_id)
        if not path.exists():
            raise FileNotFoundError(f"Session not found: {interview_id}")
        return path

    def list_summaries(self) -> list[dict]:
        results: list[dict] = []
        for path in self.sessions_dir.glob("*.json"):
            data = json.loads(path.read_text(encoding="utf-8"))
            results.append(
                {
                    "interview_id": data["interview_id"],
                    "candidate_name": data["candidate_name"],
                    "position": data["position"],
                    "language": data["language"],
                    "duration_minutes": data["duration_minutes"],
                    "started_at": data["started_at"],
                    "finished_at": data.get("finished_at"),
                }
            )
        return sorted(results, key=lambda item: item["started_at"], reverse=True)
