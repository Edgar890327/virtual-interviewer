from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import time
from typing import Literal

import httpx
from faster_whisper import WhisperModel

from .config import (
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
    WHISPER_COMPUTE_TYPE,
    WHISPER_DEVICE,
    WHISPER_MODEL_SIZE,
    OLLAMA_API_KEY
)
from .storage import InterviewSession, Message


class LocalLLMClient:
    def __init__(self, base_url: str = OLLAMA_BASE_URL, model: str = OLLAMA_MODEL, ollama_api_key: str = OLLAMA_API_KEY):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.ollama_api_key = ollama_api_key
        self.client = httpx.Client(timeout=120.0, event_hooks={
                       "request": [self.log_request],
                    })

    def _language_name(self, language: Literal["es", "en"]) -> str:
        return "Spanish" if language == "es" else "English"

    def _system_prompt(self, session: InterviewSession, position_description: str = "", seconds_left: int = 0) -> str:
        language_name = self._language_name(session.language)
        prompt = (
            "You are an expert interview agent.\n"
            f"Interview language: {language_name}.\n"
            f"Candidate name: {session.candidate_name}.\n"
            f"Position: {session.position}.\n"
        )
        
        if position_description:
            prompt += f"Position requirements and description:\n{position_description}\n\n"
        
        if seconds_left > 0:
            prompt += f"Time remaining: {max(seconds_left, 0)} seconds.\n\n"
        
        prompt += (
            "Rules:\n"
            "1) Keep a natural, conversational flow.\n"
            "2) Ask exactly one interview question at a time.\n"
            "3) Questions must be targeted to the position and previous answers.\n"
            "4) Consider the position requirements when asking questions.\n"
            "5) Keep each question concise.\n"
            "6) Return ONLY the next interviewer question text.\n"
        )
        return prompt

    def log_request(self,request):
        print(f"\n--- REQUEST ---")
        print(f"{request.method} {request.url}")
        print(f"Headers: {dict(request.headers)}")
        print(f"Body: {request.content.decode('utf-8')}")

    def next_question(self, session: InterviewSession, seconds_left: int, position_description: str = "") -> str:
        messages = [{"role": "user", "content": self._system_prompt(session, position_description, seconds_left)}]
        for message in session.messages[-16:]:
            if message.role in {"assistant", "user"}:
                messages.append({"role": message.role, "content": message.content})
            
        request = {
                "model": "gpt-oss:20b",
                "messages": messages,
                "stream": False,
                #"options": {"temperature": 0.7},
                "keep_alive": "30m",
            }
        response = self.client.post(
            f"{self.base_url}/api/chat",
            json=request,
            headers={"Authorization": f"Bearer {self.ollama_api_key}"},
            timeout=httpx.Timeout(600.0, connect=10.0)
        )
        print(f"Request data: {request}")
        print(f"OLLAMA API Key: {self.ollama_api_key}")
        print(f"Request to {self.base_url}/api/chat returned status code {response.status_code}")
        response.raise_for_status()
        data = response.json()
        print(f"Response data: {data}")
        question = data["message"]["content"].strip()
        if not question:
            raise ValueError("The local model returned an empty question.")
        return question
        
    def warmUp(self)    -> None:
            messages = [{"role": "user", "content": "Hi"}]
            request = {
                    "model": "gpt-oss:20b",
                    "messages": messages,
                    "stream": False,
                    "keep_alive": "30m",
                }
            reason = "load"
            retry = 0
            while reason == "load":
                response = self.client.post(
                    f"{self.base_url}/api/chat",
                    json=request,
                    headers={"Authorization": f"Bearer {self.ollama_api_key}"},
                    timeout=httpx.Timeout(600.0, connect=10.0)
                )
                data = response.json()
                reason = data.get("done_reason")
                retry += 1
                print(f"Warm-up attempt {retry}: done_reason={reason}")
                print(f"Request data: {request}")
                print(f"OLLAMA API Key: {self.ollama_api_key}")
                print(f"Request to {self.base_url}/api/chat returned status code {response.status_code}")
                print(f"Response data: {data}")
                time.sleep(5)

    def feedback(self, session: InterviewSession, position_description: str = "") -> str:
        language_name = self._language_name(session.language)
        print(f"Generating feedback for interview_id={session.interview_id}, language={language_name}")
        transcript = "\n".join(
            f"{'Interviewer' if m.role == 'assistant' else 'Candidate'}: {m.content}"
            for m in session.messages
            if m.role in {"assistant", "user"}
        )
        
        print(f"Transcript for feedback generation:\n{transcript}")
        context = f"Position: {session.position}\n"
        if position_description:
            context += f"Position Requirements:\n{position_description}\n"
        
        print(f"Context for feedback generation:\n{context}")
        context += f"Candidate: {session.candidate_name}\n"
        
        print(f"Final context for feedback generation:\n{context}")
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a senior technical interviewer that writes final interview feedback.\n"
                    f"Write feedback in {language_name}.\n"
                    "IMPORTANT: Always provide structured feedback.\n"
                    "Use this exact structure:\n\n"
                    "## Strengths\n"
                    "- [List candidate strengths]\n\n"
                    "## Areas to Improve\n"
                    "- [List areas for improvement]\n\n"
                    "## Technical Assessment\n"
                    "Score: [0-10]/10\n"
                    "- [Brief assessment]\n\n"
                    "## Recommendation\n"
                    "[Hiring recommendation]\n\n"
                    "Be specific, actionable, and fair."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"{context}"
                    "Transcript:\n"
                    f"{transcript}\n\n"
                    "Please provide structured feedback for this interview. Provide specific resources to consider for improvement if possible."
                ),
            },
        ]
        
        print(f"Sending feedback request to LLM with messages: {messages}")
        try:
            response = self.client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": "gpt-oss:20b",
                    "messages": messages,
                    "stream": False,
                    "options": {"temperature": 0.3},
                },
                headers={"Authorization": f"Bearer {self.ollama_api_key}"},
            )
            response.raise_for_status()
            
            print(f"Feedback response received with status code {response.status_code}")
            feedback = response.json()["message"]["content"].strip()
            if not feedback:
                return self._fallback_feedback(session, language_name)
            
            print(f"Generated feedback:\n{feedback}")
            return feedback
        except Exception as e:
            print(f"Error generating feedback: {e}")
            return self._fallback_feedback(session, language_name)
    
    def _fallback_feedback(self, session: InterviewSession, language_name: str) -> str:
        """Generate fallback feedback if LLM fails."""
        question_count = sum(1 for m in session.messages if m.role == "assistant")
        if language_name == "Spanish":
            return (
                "## Fortalezas\n"
                "- El candidato participó en la entrevista\n\n"
                "## Áreas para Mejorar\n"
                f"- Se realizaron {question_count} preguntas durante la entrevista\n\n"
                "## Evaluación Técnica\n"
                "Puntuación: 5/10\n"
                "- Entrevista completada con respuestas básicas\n\n"
                "## Recomendación\n"
                "Revisar respuestas con el equipo de evaluación.\n"
            )
        else:
            return (
                "## Strengths\n"
                "- Candidate participated in the interview\n\n"
                "## Areas to Improve\n"
                f"- {question_count} questions were asked during the interview\n\n"
                "## Technical Assessment\n"
                "Score: 5/10\n"
                "- Interview completed with basic responses\n\n"
                "## Recommendation\n"
                "Review answers with the evaluation team.\n"
            )


class SpeechToText:
    def __init__(self):
        self.model = WhisperModel(
            WHISPER_MODEL_SIZE,
            device=WHISPER_DEVICE,
            compute_type=WHISPER_COMPUTE_TYPE,
        )
    print(f"Whisper model initialized with size={WHISPER_MODEL_SIZE}, device={WHISPER_DEVICE}, compute_type={WHISPER_COMPUTE_TYPE}")
    def transcribe(self, file_path: Path, language: Literal["es", "en"]) -> str:
        segments, _ = self.model.transcribe(
            str(file_path),
            language=language,
            vad_filter=True,
        )
        print(f"Transcription completed for file: {file_path}, language: {language}")
        text = " ".join(segment.text.strip() for segment in segments).strip()
        
        print(f"Transcribed text: {text}")
        if not text:
            raise ValueError("Could not transcribe audio, empty result.")
        
        print(f"Transcription result: {text}")
        return text


def seconds_left(session: InterviewSession) -> int:
    started = datetime.fromisoformat(session.started_at)
    elapsed = datetime.now(timezone.utc) - started
    total = session.duration_minutes * 60
    return max(total - int(elapsed.total_seconds()), 0)
