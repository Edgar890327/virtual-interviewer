from __future__ import annotations

from dataclasses import asdict
from io import BytesIO
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile

import httpx
from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.security import HTTPBearer
from fastapi.staticfiles import StaticFiles
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from .ai import LocalLLMClient, SpeechToText, seconds_left
from .config import STATIC_DIR
from .database import init_db, UserDB, InterviewDB
from .auth import (
    hash_password,
    verify_password,
    create_access_token,
    decode_token,
    register_user,
    authenticate_user,
)
from .models_manager import ModelsManager
from .schemas import (
    FinishInterviewResponse,
    InterviewTurnResponse,
    SessionSummary,
    StartInterviewRequest,
    StartInterviewResponse,
    UserRegister,
    UserLogin,
    AuthResponse,
)
from .storage import Message, SessionStore

app = FastAPI(title="Local Voice Interviewer")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

store = SessionStore()
llm = LocalLLMClient()
security = HTTPBearer()
models_manager = ModelsManager()

_stt = None


def get_stt() -> SpeechToText:
    global _stt
    print("Initializing SpeechToText model..."  )
    if _stt is None:
        _stt = SpeechToText()
    print("SpeechToText model initialized.")
    return _stt


@app.on_event("startup")
async def startup_event():
    """Initialize database and models on startup."""
    init_db()


async def get_current_user(credentials = Depends(security)) -> str:
    """Extract user_id from JWT token."""
    token = credentials.credentials
    user_id = decode_token(token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    return user_id


def get_session_or_404(interview_id: str):
    try:
        print(f"Retrieving session for interview_id={interview_id}")
        return store.load(interview_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def render_session_pdf(session) -> bytes:
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    x = 50
    y = height - 50
    line_height = 15

    def write_line(text: str, font: str = "Helvetica", size: int = 10) -> None:
        nonlocal y
        if y < 60:
            pdf.showPage()
            y = height - 50
        pdf.setFont(font, size)
        pdf.drawString(x, y, text[:130])
        y -= line_height

    def write_wrapped(text: str, prefix: str = "") -> None:
        words = text.split()
        current = prefix
        for word in words:
            candidate = f"{current} {word}".strip()
            if len(candidate) > 120:
                write_line(current)
                current = word
            else:
                current = candidate
        if current:
            write_line(current)

    write_line("Interview Session Report", "Helvetica-Bold", 14)
    write_line(f"Candidate: {session.candidate_name}")
    write_line(f"Position: {session.position}")
    write_line(f"Language: {session.language.upper()}")
    write_line(f"Duration: {session.duration_minutes} min")
    write_line(f"Started: {session.started_at}")
    write_line(f"Finished: {session.finished_at or 'N/A'}")
    write_line("")
    write_line("Conversation", "Helvetica-Bold", 12)

    for message in session.messages:
        speaker = "Interviewer" if message.role == "assistant" else "Candidate"
        write_wrapped(message.content, prefix=f"{speaker}:")

    write_line("")
    write_line("Feedback", "Helvetica-Bold", 12)
    write_wrapped(session.feedback or "No feedback generated.")

    pdf.save()
    return buffer.getvalue()


# ============================================================================
# PUBLIC ENDPOINTS (No auth required)
# ============================================================================

@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


# ============================================================================
# AUTH ENDPOINTS
# ============================================================================

@app.post("/api/auth/register", response_model=AuthResponse)
def register(payload: UserRegister) -> AuthResponse:
    """Register a new user."""
    user_id = register_user(payload.username, payload.email, payload.password)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already exists",
        )
    
    token = create_access_token(user_id)
    return AuthResponse(access_token=token, token_type="bearer", user_id=user_id)


@app.post("/api/auth/login", response_model=AuthResponse)
def login(payload: UserLogin) -> AuthResponse:
    """Login user and return JWT token."""
    result = authenticate_user(payload.username, payload.password)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    user_id, token = result
    return AuthResponse(access_token=token, token_type="bearer", user_id=user_id)


@app.get("/api/auth/me")
def get_current_user_info(user_id: str = Depends(get_current_user)) -> dict:
    """Get current user info."""
    user = UserDB.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "id": user["id"],
        "username": user["username"],
        "email": user["email"],
    }


# ============================================================================
# MODELS ENDPOINTS
# ============================================================================

@app.get("/api/models")
async def list_models(user_id: str = Depends(get_current_user)) -> dict:
    """List available models."""
    models = await models_manager.list_models()
    return {"models": models}


@app.post("/api/models/download")
async def download_model(
    model_name: str,
    user_id: str = Depends(get_current_user),
) -> dict:
    """Download/pull a model from Ollama registry."""
    success = await models_manager.pull_model(model_name)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to download model {model_name}",
        )
    return {"status": "success", "model": model_name}


@app.post("/api/models/select")
async def select_model(
    model_name: str,
    user_id: str = Depends(get_current_user),
) -> dict:
    """Select the model to use for interviews."""
    available = await models_manager.is_model_available(model_name)
    if not available:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Model {model_name} is not available. Download it first.",
        )
    # TODO: Store selected model in user preferences
    return {"status": "success", "model": model_name}


# ============================================================================
# INTERVIEW ENDPOINTS
# ============================================================================

@app.post("/api/interviews/start", response_model=StartInterviewResponse)
def start_interview(
    payload: StartInterviewRequest,
    user_id: str = Depends(get_current_user),
) -> StartInterviewResponse:
    """Start a new interview."""
    # Create interview in database — returns generated id
    interview_id = InterviewDB.create_interview(
        user_id=user_id,
        candidate_name=payload.candidate_name,
        candidate_email=payload.candidate_email or "",
        position=payload.position,
        position_description=payload.position_description or "",
        language=payload.language,
        duration_minutes=payload.duration_minutes,
    )
    
    # Create session in memory
    session = store.create(
        candidate_name=payload.candidate_name,
        position=payload.position,
        language=payload.language,
        duration_minutes=payload.duration_minutes,
    )
    
    # Override interview_id to match database
    session.interview_id = interview_id
    
    try:
        # Generate first question with position description context
        first_question = llm.next_question(
            session,
            seconds_left(session),
            position_description=payload.position_description or "",
        )
    except (httpx.HTTPError, KeyError, ValueError) as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Local LLM error while generating first question: {exc}",
        ) from exc

    session.messages.append(Message(role="assistant", content=first_question))
    store.save(session)
    
    return StartInterviewResponse(
        interview_id=session.interview_id,
        first_question=first_question,
        seconds_left=seconds_left(session),
        started_at=datetime.fromisoformat(session.started_at),
    )


@app.post("/api/interviews/{interview_id}/turn", response_model=InterviewTurnResponse)
def interview_turn(
    interview_id: str,
    audio: UploadFile | None = File(default=None),
    transcript: str | None = Form(default=None),
    user_id: str = Depends(get_current_user),
) -> InterviewTurnResponse:
    """Process interview turn with candidate response."""
    # Verify ownership
    print(f"Verifying ownership for interview_id={interview_id}, user_id={user_id}")
    db_interview = InterviewDB.get_interview(interview_id, user_id)
    if not db_interview:
        raise HTTPException(status_code=404, detail="Interview not found")
    
    print(f"Ownership verified. Loading session for interview_id={interview_id}")
    session = get_session_or_404(interview_id)
    stt = get_stt()

    print(f"Checking if interview is already finished for interview_id={interview_id}")
    if session.finished_at:
        raise HTTPException(status_code=409, detail="Interview already finished.")

    print(f"Calculating seconds left for interview_id={interview_id}")
    current_seconds_left = seconds_left(session)
    if current_seconds_left <= 0:
        raise HTTPException(status_code=409, detail="Interview time is over. Finish interview.")

    print(f"Processing candidate response for interview_id={interview_id}")
    spoken_text = (transcript or "").strip()
    if not spoken_text and audio is not None:
        suffix = Path(audio.filename or "audio.webm").suffix or ".webm"
        with NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            temp_path = Path(tmp.name)
            tmp.write(audio.file.read())
        try:
            spoken_text = stt.transcribe(temp_path, session.language)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        finally:
            temp_path.unlink(missing_ok=True)

    if not spoken_text:
        raise HTTPException(status_code=400, detail="Provide transcript text or audio file.")

    session.messages.append(Message(role="user", content=spoken_text))

    print(f"Generating next question for interview_id={interview_id}, seconds_left={current_seconds_left}")
    current_seconds_left = seconds_left(session)
    ended = current_seconds_left <= 0
    if not ended:
        try:
            print(f"Calling llm.next_question with interview_id={interview_id}, seconds_left={current_seconds_left}")
            next_question = llm.next_question(session, current_seconds_left)
            print(f"Next question generated: {next_question}")
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Local LLM error while generating next question: {exc}",
            ) from exc
        session.messages.append(Message(role="assistant", content=next_question))
    else:
        next_question = (
            "Tiempo finalizado. Presiona finalizar para generar feedback."
            if session.language == "es"
            else "Time is over. Press finish to generate feedback."
        )
    print(f"Saving session for interview_id={interview_id}")
    store.save(session)
    
    # Store messages in database
    #InterviewDB.update_messages(interview_id, user_id, session.messages)
    InterviewDB.update_interview(interview_id, user_id, messages=[asdict(m) for m in session.messages])
    print(f"Session saved and database updated for interview_id={interview_id}")
    return InterviewTurnResponse(
        transcript=spoken_text,
        next_question=next_question,
        ended=ended,
        seconds_left=current_seconds_left,
    )


@app.post("/api/interviews/{interview_id}/finish", response_model=FinishInterviewResponse)
def finish_interview(
    interview_id: str,
    user_id: str = Depends(get_current_user),
) -> FinishInterviewResponse:
    """Finish interview and generate feedback."""
    # Verify ownership
    db_interview = InterviewDB.get_interview(interview_id, user_id)
    if not db_interview:
        raise HTTPException(status_code=404, detail="Interview not found")
    
    session = get_session_or_404(interview_id)

    if session.finished_at and session.feedback:
        return FinishInterviewResponse(
            feedback=session.feedback,
            finished_at=datetime.fromisoformat(session.finished_at),
        )

    try:
        # Use position_description for better feedback context
        position_description = db_interview.get("position_description", "")
        feedback = llm.feedback(session, position_description=position_description)
    except (httpx.HTTPError, KeyError, ValueError) as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Local LLM error while generating feedback: {exc}",
        ) from exc

    finished_at = datetime.now(timezone.utc)
    session.feedback = feedback
    session.finished_at = finished_at.isoformat()
    store.save(session)
    
    # Update in database
    InterviewDB.update_interview(
        interview_id=interview_id,
        user_id=user_id,
        feedback=feedback,
        finished_at=finished_at.isoformat(),
    )

    return FinishInterviewResponse(feedback=feedback, finished_at=finished_at)


@app.get("/api/interviews")
def list_interviews(user_id: str = Depends(get_current_user)) -> dict:
    """List all interviews for current user."""
    interviews = InterviewDB.list_interviews(user_id)
    return {
        "interviews": [
            {
                "interview_id": i["id"],
                "candidate_name": i["candidate_name"],
                "position": i["position"],
                "language": i["language"],
                "duration_minutes": i["duration_minutes"],
                "started_at": i["started_at"],
                "finished_at": i["finished_at"],
                "feedback": i["feedback"],
            }
            for i in interviews
        ]
    }


@app.get("/api/interviews/{interview_id}")
def get_interview(
    interview_id: str,
    user_id: str = Depends(get_current_user),
) -> dict:
    """Get interview details."""
    # Verify ownership
    db_interview = InterviewDB.get_interview(interview_id, user_id)
    if not db_interview:
        raise HTTPException(status_code=404, detail="Interview not found")
    
    session = get_session_or_404(interview_id)
    return {
        "interview_id": session.interview_id,
        "candidate_name": session.candidate_name,
        "position": session.position,
        "language": session.language,
        "duration_minutes": session.duration_minutes,
        "started_at": session.started_at,
        "finished_at": session.finished_at,
        "feedback": session.feedback,
        "messages": [message.__dict__ for message in session.messages],
    }


@app.get("/api/interviews/{interview_id}/feedback")
def get_feedback(
    interview_id: str,
    user_id: str = Depends(get_current_user),
) -> dict:
    """Get interview feedback."""
    # Verify ownership
    db_interview = InterviewDB.get_interview(interview_id, user_id)
    if not db_interview:
        raise HTTPException(status_code=404, detail="Interview not found")
    
    session = get_session_or_404(interview_id)
    return {"feedback": session.feedback or "No feedback available"}


@app.get("/api/sessions", response_model=list[SessionSummary])
def list_sessions(user_id: str = Depends(get_current_user)) -> list[SessionSummary]:
    """List all sessions for current user (backward compatibility)."""
    # Get from database
    interviews = InterviewDB.list_interviews(user_id)
    return [
        SessionSummary(
            interview_id=i["id"],
            candidate_name=i["candidate_name"],
            position=i["position"],
            language=i["language"],
            duration_minutes=i["duration_minutes"],
            started_at=i["started_at"],
            finished_at=i["finished_at"],
            feedback=i["feedback"],
        )
        for i in interviews
    ]


@app.get("/api/sessions/{interview_id}")
def get_session(
    interview_id: str,
    user_id: str = Depends(get_current_user),
) -> dict:
    """Get session details (backward compatibility)."""
    # Verify ownership
    db_interview = InterviewDB.get_interview(interview_id, user_id)
    if not db_interview:
        raise HTTPException(status_code=404, detail="Interview not found")
    
    session = get_session_or_404(interview_id)
    return {
        "interview_id": session.interview_id,
        "candidate_name": session.candidate_name,
        "position": session.position,
        "language": session.language,
        "duration_minutes": session.duration_minutes,
        "started_at": session.started_at,
        "finished_at": session.finished_at,
        "feedback": session.feedback,
        "messages": [message.__dict__ for message in session.messages],
    }


@app.get("/api/sessions/{interview_id}/export/json")
def export_session_json(
    interview_id: str,
    user_id: str = Depends(get_current_user),
) -> FileResponse:
    """Export session as JSON."""
    # Verify ownership
    db_interview = InterviewDB.get_interview(interview_id, user_id)
    if not db_interview:
        raise HTTPException(status_code=404, detail="Interview not found")
    
    try:
        path = store.export_json_path(interview_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return FileResponse(
        path,
        media_type="application/json",
        filename=f"session-{interview_id}.json",
    )


@app.get("/api/sessions/{interview_id}/export/pdf")
def export_session_pdf(
    interview_id: str,
    user_id: str = Depends(get_current_user),
) -> StreamingResponse:
    """Export session as PDF."""
    # Verify ownership
    db_interview = InterviewDB.get_interview(interview_id, user_id)
    if not db_interview:
        raise HTTPException(status_code=404, detail="Interview not found")
    
    session = get_session_or_404(interview_id)
    pdf_bytes = render_session_pdf(session)
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="session-{interview_id}.pdf"'},
    )
