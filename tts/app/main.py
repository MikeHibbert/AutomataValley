from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel, Field

VOICE = os.getenv("TTS_VOICE", "en")
RATE = int(os.getenv("TTS_RATE", "165"))

app = FastAPI(title="AutomataValley TTS Service", version="0.1.0")


class SpeechRequest(BaseModel):
    text: str = Field(min_length=1, max_length=400)
    voice: str | None = None
    rate: int | None = None


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "tts",
        "engine": "espeak-ng",
    }


@app.post("/synthesize", response_class=Response)
def synthesize(request: SpeechRequest) -> Response:
    text = request.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text is required for synthesis.")

    wav_bytes = synthesize_wav_bytes(
        text=text,
        voice=request.voice or VOICE,
        rate=request.rate or RATE,
    )
    return Response(content=wav_bytes, media_type="audio/wav")


def synthesize_wav_bytes(*, text: str, voice: str, rate: int) -> bytes:
    with tempfile.TemporaryDirectory() as temp_dir:
        output_path = Path(temp_dir) / "speech.wav"
        command = [
            "espeak-ng",
            "-v",
            voice,
            "-s",
            str(rate),
            "-w",
            str(output_path),
            text,
        ]
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
        if completed.returncode != 0:
            detail = completed.stderr.strip() or completed.stdout.strip() or "Unknown espeak-ng failure."
            raise HTTPException(status_code=500, detail=f"TTS synthesis failed: {detail}")

        if not output_path.exists():
            raise HTTPException(status_code=500, detail="TTS synthesis did not produce audio output.")

        return output_path.read_bytes()
