from __future__ import annotations

import os
from typing import Any

import httpx
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from .vision_tools import (
    build_mcp_tool_catalog,
    get_vision_status,
    invoke_tool,
    report_snapshot,
    request_snapshot,
    start_vision_session,
    stop_vision_session,
)

VALLEY_URL = os.getenv("VALLEY_URL", "http://valley:8001")
DOJO_STT_URL = os.getenv("DOJO_STT_URL", "http://localhost:8003")
DOJO_TTS_URL = os.getenv("DOJO_TTS_URL", "http://localhost:8004")

app = FastAPI(title="AutomataValley Bridge Service", version="0.1.0")


class HealthResponse(BaseModel):
    status: str
    service: str
    valley_url: str


class VisionStartRequest(BaseModel):
    requested_by: str = "zeitgeist"
    reason: str = ""
    mode: str = "snapshot"
    camera_id: str = "front_cam"


class VisionSnapshotRequest(BaseModel):
    note: str = ""
    camera_id: str | None = None


class VisionStopRequest(BaseModel):
    session_id: str | None = None


class McpToolInvokeRequest(BaseModel):
    tool_name: str
    arguments: dict[str, Any] = {}


class VisionSnapshotReport(BaseModel):
    session_id: str
    job_id: str
    camera_id: str
    image_base64: str
    media_type: str = "image/png"
    captured_at: str | None = None
    width: int = 0
    height: int = 0
    frame_summary: str = ""
    observations: list[dict[str, Any]] = []


async def get_json(path: str, *, timeout: float = 5.0) -> Any:
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            response = await client.get(f"{VALLEY_URL}{path}")
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text or str(exc)
            raise HTTPException(status_code=exc.response.status_code, detail=detail) from exc
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=503, detail=f"Valley unavailable: {exc}") from exc
    return response.json()


async def post_json(path: str, payload: dict, *, timeout: float = 10.0) -> Any:
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            response = await client.post(f"{VALLEY_URL}{path}", json=payload)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text or str(exc)
            raise HTTPException(status_code=exc.response.status_code, detail=detail) from exc
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=503, detail=f"Valley unavailable: {exc}") from exc
    return response.json()


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    await get_json("/health")
    return HealthResponse(status="ok", service="bridge", valley_url=VALLEY_URL)


@app.get("/api/bootstrap")
async def bootstrap() -> dict[str, Any]:
    valley_health = await get_json("/health")
    waypoints = await get_json("/waypoints")
    world = await get_json("/world")
    world["vision"] = dict(world.get("vision", {}))
    world["vision"]["live_feed"] = get_vision_status()
    return {
        "status": "ok",
        "service": "bridge",
        "valley_url": VALLEY_URL,
        "robot": {"id": "dojo-bot-01"},
        "stt": {"url": DOJO_STT_URL, "engine": "parakeet"},
        "tts": {"url": DOJO_TTS_URL, "engine": "espeak-ng"},
        "waypoints": waypoints,
        "world": world,
        "vision": world.get("vision", {}),
        "capabilities": world.get("capabilities", {}),
        "mcp_tools": build_mcp_tool_catalog(),
        "valley": valley_health,
    }


@app.post("/api/commands")
async def forward_command(payload: dict) -> dict:
    return await post_json("/commands", payload)


@app.post("/api/dojo/commands")
async def dojo_command(payload: dict) -> dict[str, Any]:
    result = await post_json("/commands", payload)
    return {
        "ok": True,
        "submitted_command": {
            "command_id": payload.get("command_id"),
            "session_id": payload.get("session_id"),
            "robot_id": payload.get("robot_id"),
            "transcript": payload.get("transcript"),
            "command_text": payload.get("command_text"),
        },
        "interpretation": result.get("interpretation", {}),
        "task": {
            "task_id": result.get("task_id"),
            "intent": result.get("intent"),
        },
        "events": result.get("events", []),
    }


@app.post("/api/dojo/observe/image")
async def dojo_observe_image(
    image: UploadFile = File(...),
    note: str = Form(default=""),
) -> dict[str, Any]:
    image_bytes = await image.read()
    files = {
        "image": (
            image.filename or "dojo_upload.png",
            image_bytes,
            image.content_type or "application/octet-stream",
        )
    }
    data = {"note": note}
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(f"{VALLEY_URL}/observe/image", files=files, data=data)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text or str(exc)
            raise HTTPException(status_code=exc.response.status_code, detail=detail) from exc
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=503, detail=f"Valley unavailable: {exc}") from exc
    return response.json()


@app.get("/api/dojo/vision/status")
async def dojo_vision_status() -> dict[str, Any]:
    return {
        "ok": True,
        "action": "vision_status",
        "status": get_vision_status(),
        "tools": build_mcp_tool_catalog(),
    }


@app.post("/api/dojo/vision/start")
async def dojo_vision_start(payload: VisionStartRequest) -> dict[str, Any]:
    return {
        "ok": True,
        "action": "vision_start",
        **start_vision_session(
            requested_by=payload.requested_by,
            reason=payload.reason,
            mode=payload.mode,
            camera_id=payload.camera_id,
        ),
        "tools": build_mcp_tool_catalog(),
    }


@app.post("/api/dojo/vision/snapshot")
async def dojo_vision_snapshot(payload: VisionSnapshotRequest) -> dict[str, Any]:
    result = request_snapshot(note=payload.note, camera_id=payload.camera_id)
    return {
        "action": "vision_snapshot",
        "tools": build_mcp_tool_catalog(),
        **result,
    }


@app.post("/api/dojo/vision/report")
async def dojo_vision_report(payload: VisionSnapshotReport) -> dict[str, Any]:
    result = report_snapshot(
        session_id=payload.session_id,
        job_id=payload.job_id,
        camera_id=payload.camera_id,
        image_base64=payload.image_base64,
        media_type=payload.media_type,
        captured_at=payload.captured_at,
        width=payload.width,
        height=payload.height,
        frame_summary=payload.frame_summary,
        observations=payload.observations,
    )
    return {
        "action": "vision_report",
        "tools": build_mcp_tool_catalog(),
        **result,
    }


@app.post("/api/dojo/vision/stop")
async def dojo_vision_stop(payload: VisionStopRequest) -> dict[str, Any]:
    result = stop_vision_session(session_id=payload.session_id)
    return {
        "action": "vision_stop",
        "tools": build_mcp_tool_catalog(),
        **result,
    }


@app.get("/api/mcp/tools")
async def list_mcp_tools() -> dict[str, Any]:
    return {
        "ok": True,
        "tools": build_mcp_tool_catalog(),
        "status": get_vision_status(),
    }


@app.post("/api/mcp/tools/invoke")
async def invoke_mcp_tool(payload: McpToolInvokeRequest) -> dict[str, Any]:
    try:
        result = invoke_tool(payload.tool_name, payload.arguments, world=None)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        **result,
        "tools": build_mcp_tool_catalog(),
    }
