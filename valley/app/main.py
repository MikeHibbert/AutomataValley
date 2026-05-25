from __future__ import annotations

from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from uuid import uuid4

from fastapi import FastAPI

from .interpreter import interpret_command
from .models import CommandPayload, HealthResponse, ValleyCommandResponse
from .navigation import ROOM_WAYPOINTS, build_task_events

app = FastAPI(title="AutomataValley Valley Service", version="0.1.0")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_campfirevalley_version() -> str | None:
    try:
        return version("campfirevalley")
    except PackageNotFoundError:
        return None


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(service="valley", campfirevalley_version=get_campfirevalley_version())


@app.get("/waypoints")
def list_waypoints() -> dict[str, dict[str, float]]:
    return ROOM_WAYPOINTS


@app.post("/commands", response_model=ValleyCommandResponse)
def submit_command(payload: CommandPayload) -> ValleyCommandResponse:
    interpretation_result = interpret_command(payload.command_text)
    interpretation = interpretation_result["interpretation"]
    intent = interpretation_result.get("intent")

    if intent is None:
        return ValleyCommandResponse(interpretation=interpretation)

    task_id = str(uuid4())
    timestamp = utc_now_iso()
    events = build_task_events(
        command_id=payload.command_id,
        task_id=task_id,
        session_id=payload.session_id,
        robot_id=payload.robot_id,
        intent=intent,
        timestamp=timestamp,
    )
    return ValleyCommandResponse(
        interpretation=interpretation,
        task_id=task_id,
        intent=intent,
        events=events,
    )
