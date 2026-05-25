from __future__ import annotations

import os
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

VALLEY_URL = os.getenv("VALLEY_URL", "http://valley:8001")
DOJO_STT_URL = os.getenv("DOJO_STT_URL", "http://localhost:8003")
DOJO_TTS_URL = os.getenv("DOJO_TTS_URL", "http://localhost:8004")

app = FastAPI(title="AutomataValley Bridge Service", version="0.1.0")


class HealthResponse(BaseModel):
    status: str
    service: str
    valley_url: str


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
    return {
        "status": "ok",
        "service": "bridge",
        "valley_url": VALLEY_URL,
        "robot": {"id": "dojo-bot-01"},
        "stt": {"url": DOJO_STT_URL, "engine": "parakeet"},
        "tts": {"url": DOJO_TTS_URL, "engine": "espeak-ng"},
        "waypoints": waypoints,
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
