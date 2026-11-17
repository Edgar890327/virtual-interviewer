from datetime import datetime
from pydantic import BaseModel, Field, EmailStr
from typing import Literal, Optional


# Auth Schemas
class UserRegister(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=6, max_length=100)


class UserLogin(BaseModel):
    username: str
    password: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str


class UserInfo(BaseModel):
    id: str
    username: str
    email: str
    created_at: datetime


# Interview Schemas
class StartInterviewRequest(BaseModel):
    candidate_name: str = Field(min_length=1, max_length=120)
    candidate_email: Optional[str] = None
    position: str = Field(min_length=1, max_length=120)
    position_description: Optional[str] = Field(None, max_length=2000)
    duration_minutes: int = Field(ge=5, le=90)
    language: Literal["es", "en"]


class InterviewTurnResponse(BaseModel):
    transcript: str
    next_question: str
    ended: bool
    seconds_left: int


class StartInterviewResponse(BaseModel):
    interview_id: str
    first_question: str
    seconds_left: int
    started_at: datetime


class FinishInterviewResponse(BaseModel):
    feedback: str
    finished_at: datetime


class SessionSummary(BaseModel):
    interview_id: str
    candidate_name: str
    position: str
    language: Literal["es", "en"]
    duration_minutes: int
    started_at: datetime
    finished_at: Optional[datetime] = None
    feedback: Optional[str] = None


# Models Management
class ModelInfo(BaseModel):
    name: str
    size: Optional[int] = None


class ModelsListResponse(BaseModel):
    models: list[ModelInfo]
    available: bool

