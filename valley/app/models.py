from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class CommandMetadata(BaseModel):
    stt_engine: str = "parakeet"
    confidence: float | None = None


class CommandPayload(BaseModel):
    command_id: str
    timestamp: str
    session_id: str
    robot_id: str = "dojo-bot-01"
    source: str = "dojo_voice"
    transcript: str
    command_text: str
    command_type: Literal["navigation", "inspection", "manipulation", "multimodal"] = "navigation"
    metadata: CommandMetadata | None = None


class InterpretationResponse(BaseModel):
    disposition: Literal["execute", "clarify", "reject"]
    message: str
    spoken_response: str
    canonical_command: str | None = None
    suggestions: list[str] = Field(default_factory=list)


class ValleyCommandResponse(BaseModel):
    interpretation: InterpretationResponse
    task_id: str | None = None
    intent: dict[str, Any] | None = None
    events: list[dict[str, Any]] = Field(default_factory=list)


class ObservationRequestMetadata(BaseModel):
    source: Literal["image_upload", "live_feed_snapshot"] = "image_upload"
    note: str | None = None


class ImageObservationResponse(BaseModel):
    ok: bool = True
    message: str
    observations: list[dict[str, Any]] = Field(default_factory=list)
    world: dict[str, Any]


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str
    campfirevalley_version: str | None = Field(default=None)
