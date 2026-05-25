from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any


class ParakeetBackendError(RuntimeError):
    """Raised when the Parakeet backend cannot be loaded or run."""


@dataclass
class ParakeetResult:
    transcript: str
    confidence: float | None = None
    raw: Any = None


class TransformersParakeetBackend:
    def __init__(self, *, model_id: str) -> None:
        self.model_id = model_id
        self._pipeline = None

    def _load_pipeline(self):
        if self._pipeline is not None:
            return self._pipeline

        try:
            from transformers import pipeline
        except Exception as exc:  # pragma: no cover - exercised via runtime env
            raise ParakeetBackendError(
                "Transformers-based Parakeet backend is unavailable. "
                "Install optional STT runtime dependencies first."
            ) from exc

        try:
            self._pipeline = pipeline(
                "automatic-speech-recognition",
                model=self.model_id,
            )
        except Exception as exc:  # pragma: no cover - exercised via runtime env
            raise ParakeetBackendError(
                f"Unable to load Parakeet model '{self.model_id}'."
            ) from exc

        return self._pipeline

    def transcribe_bytes(self, *, audio_bytes: bytes, filename: str) -> ParakeetResult:
        suffix = Path(filename).suffix or ".wav"
        with NamedTemporaryFile(delete=True, suffix=suffix) as temp_audio:
            temp_audio.write(audio_bytes)
            temp_audio.flush()
            pipe = self._load_pipeline()
            try:
                result = pipe(temp_audio.name)
            except Exception as exc:  # pragma: no cover - exercised via runtime env
                raise ParakeetBackendError("Parakeet transcription failed.") from exc

        transcript = str(result.get("text", "")).strip() if isinstance(result, dict) else str(result).strip()
        confidence = None
        if isinstance(result, dict):
            confidence = result.get("confidence")
            if confidence is None:
                chunks = result.get("chunks")
                if isinstance(chunks, list) and chunks:
                    scores = [chunk.get("score") for chunk in chunks if isinstance(chunk, dict) and chunk.get("score") is not None]
                    if scores:
                        confidence = float(sum(scores) / len(scores))

        return ParakeetResult(transcript=transcript, confidence=confidence, raw=result)
