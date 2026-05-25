from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from .parakeet_backend import ParakeetBackendError, TransformersParakeetBackend

ENGINE_NAME = os.getenv("STT_ENGINE", "parakeet")
ENGINE_MODE = os.getenv("STT_MODE", "stub")
PARAKEET_BACKEND = os.getenv("PARAKEET_BACKEND", "transformers")
PARAKEET_MODEL_ID = os.getenv("PARAKEET_MODEL_ID", "nvidia/parakeet-ctc-0.6b")

app = FastAPI(title="AutomataValley STT Service", version="0.1.0")
_parakeet_backend: TransformersParakeetBackend | None = None


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "stt"
    engine: str = ENGINE_NAME
    mode: str = ENGINE_MODE


class TextTranscriptionRequest(BaseModel):
    text: str


class AudioMetadata(BaseModel):
    filename: str
    content_type: str | None = None
    byte_count: int


class TranscriptionResponse(BaseModel):
    ok: bool = True
    transcript: str
    confidence: float
    engine: str = ENGINE_NAME
    mode: str = ENGINE_MODE
    source: Literal["text_stub", "audio_stub", "audio_parakeet"] = "text_stub"
    audio: AudioMetadata | None = None


def normalize_transcript(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def transcript_from_filename(filename: str) -> str:
    stem = Path(filename).stem
    cleaned = stem.replace("_", " ").replace("-", " ")
    return normalize_transcript(cleaned)


def get_parakeet_backend() -> TransformersParakeetBackend:
    global _parakeet_backend
    if PARAKEET_BACKEND != "transformers":
        raise ParakeetBackendError(f"Unsupported Parakeet backend: {PARAKEET_BACKEND}")
    if _parakeet_backend is None:
        _parakeet_backend = TransformersParakeetBackend(model_id=PARAKEET_MODEL_ID)
    return _parakeet_backend


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse()


@app.post("/transcribe/text", response_model=TranscriptionResponse)
def transcribe_text(payload: TextTranscriptionRequest) -> TranscriptionResponse:
    transcript = normalize_transcript(payload.text)
    return TranscriptionResponse(
        transcript=transcript,
        confidence=1.0 if transcript else 0.0,
        source="text_stub",
    )


@app.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(
    audio: UploadFile = File(...),
    simulated_transcript: str = Form(default=""),
) -> TranscriptionResponse:
    # Read the body now so later we can swap the stub for real Parakeet inference
    # without changing the endpoint contract.
    audio_bytes = await audio.read()
    transcript = normalize_transcript(simulated_transcript)

    if ENGINE_MODE != "stub":
        try:
            backend = get_parakeet_backend()
            result = backend.transcribe_bytes(
                audio_bytes=audio_bytes,
                filename=audio.filename or "uploaded_audio.wav",
            )
        except ParakeetBackendError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

        return TranscriptionResponse(
            transcript=normalize_transcript(result.transcript),
            confidence=float(result.confidence or 0.0),
            source="audio_parakeet",
            audio=AudioMetadata(
                filename=audio.filename or "uploaded_audio",
                content_type=audio.content_type,
                byte_count=len(audio_bytes),
            ),
        )

    if not transcript:
        transcript = transcript_from_filename(audio.filename or "")

    return TranscriptionResponse(
        transcript=transcript,
        confidence=0.75 if transcript else 0.0,
        source="audio_stub",
        audio=AudioMetadata(
            filename=audio.filename or "uploaded_audio",
            content_type=audio.content_type,
            byte_count=len(audio_bytes),
        ),
    )
