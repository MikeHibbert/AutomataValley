from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


_VISION_SESSION: dict[str, Any] = {
    "active": False,
    "session_id": None,
    "requested_by": None,
    "reason": "",
    "mode": "snapshot",
    "camera_id": "front_cam",
    "started_at": None,
    "last_snapshot_at": None,
    "snapshot_count": 0,
    "available_cameras": ["front_cam", "left_cam", "right_cam", "rear_cam"],
    "pending_request": None,
    "latest_snapshot": None,
}


def build_mcp_tool_catalog() -> list[dict[str, Any]]:
    return [
        {
            "name": "vision_status",
            "description": "Check whether the dojo vision feed is available and whether an on-demand session is active.",
            "input_schema": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        },
        {
            "name": "vision_start",
            "description": "Start an on-demand dojo vision session so the robot can inspect the environment when needed.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "requested_by": {"type": "string"},
                    "reason": {"type": "string"},
                    "mode": {"type": "string", "enum": ["snapshot", "burst"]},
                    "camera_id": {"type": "string"},
                },
                "additionalProperties": False,
            },
        },
        {
            "name": "vision_snapshot",
            "description": "Capture a single on-demand dojo vision snapshot while a vision session is active.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "note": {"type": "string"},
                    "camera_id": {"type": "string"},
                },
                "additionalProperties": False,
            },
        },
        {
            "name": "vision_stop",
            "description": "Stop the current on-demand dojo vision session when the model no longer needs camera access.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                },
                "additionalProperties": False,
            },
        },
    ]


def get_vision_status() -> dict[str, Any]:
    session = deepcopy(_VISION_SESSION)
    return {
        "available": True,
        "active": bool(session["active"]),
        "session": session,
        "camera_id": session["camera_id"],
        "available_cameras": session["available_cameras"],
        "pending_request": session["pending_request"],
        "latest_snapshot": session["latest_snapshot"],
        "transport": "bridge_tool_surface",
        "source": "dojo_on_demand_vision",
        "mode": "mcp_on_demand",
        "notes": "Vision is activated on demand and can capture snapshots from onboard robot cameras without streaming continuously.",
    }


def start_vision_session(
    *,
    requested_by: str = "zeitgeist",
    reason: str = "",
    mode: str = "snapshot",
    camera_id: str = "front_cam",
) -> dict[str, Any]:
    if _VISION_SESSION["active"]:
        _VISION_SESSION["camera_id"] = camera_id or _VISION_SESSION["camera_id"]
        return {
            "ok": True,
            "message": "Vision session already active.",
            "status": get_vision_status(),
        }

    _VISION_SESSION.update(
        {
            "active": True,
            "session_id": str(uuid4()),
            "requested_by": requested_by,
            "reason": reason,
            "mode": mode,
            "camera_id": camera_id or "front_cam",
            "started_at": utc_now_iso(),
            "last_snapshot_at": None,
            "snapshot_count": 0,
            "pending_request": None,
        }
    )
    return {
        "ok": True,
        "message": "Vision session started.",
        "status": get_vision_status(),
    }


def stop_vision_session(session_id: str | None = None) -> dict[str, Any]:
    if not _VISION_SESSION["active"]:
        return {
            "ok": True,
            "message": "No active vision session to stop.",
            "status": get_vision_status(),
        }

    if session_id and session_id != _VISION_SESSION["session_id"]:
        return {
            "ok": False,
            "message": "The provided vision session id does not match the active session.",
            "status": get_vision_status(),
        }

    _VISION_SESSION.update(
        {
            "active": False,
            "session_id": None,
            "requested_by": None,
            "reason": "",
            "mode": "snapshot",
            "camera_id": "front_cam",
            "started_at": None,
            "last_snapshot_at": None,
            "snapshot_count": 0,
            "pending_request": None,
        }
    )
    return {
        "ok": True,
        "message": "Vision session stopped.",
        "status": get_vision_status(),
    }


def request_snapshot(*, note: str = "", camera_id: str | None = None) -> dict[str, Any]:
    if not _VISION_SESSION["active"]:
        return {
            "ok": False,
            "message": "Vision session is not active.",
            "status": get_vision_status(),
        }

    effective_camera_id = camera_id or _VISION_SESSION["camera_id"]
    _VISION_SESSION["camera_id"] = effective_camera_id
    pending_request = {
        "job_id": str(uuid4()),
        "session_id": _VISION_SESSION["session_id"],
        "camera_id": effective_camera_id,
        "note": note.strip(),
        "requested_at": utc_now_iso(),
        "status": "pending_capture",
    }
    _VISION_SESSION["pending_request"] = pending_request
    return {
        "ok": True,
        "message": "Vision snapshot requested from %s." % effective_camera_id,
        "requested_snapshot": pending_request,
        "status": get_vision_status(),
    }


def report_snapshot(
    *,
    session_id: str,
    job_id: str,
    camera_id: str,
    image_base64: str,
    media_type: str,
    captured_at: str | None = None,
    width: int = 0,
    height: int = 0,
    frame_summary: str = "",
    observations: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if not _VISION_SESSION["active"]:
        return {
            "ok": False,
            "message": "Cannot report a snapshot because no vision session is active.",
            "status": get_vision_status(),
        }

    pending_request = _VISION_SESSION.get("pending_request")
    if pending_request is None:
        return {
            "ok": False,
            "message": "No pending vision snapshot request is waiting for a report.",
            "status": get_vision_status(),
        }

    if session_id != _VISION_SESSION["session_id"] or job_id != pending_request["job_id"]:
        return {
            "ok": False,
            "message": "The reported vision snapshot does not match the active session or pending request.",
            "status": get_vision_status(),
        }

    _VISION_SESSION["snapshot_count"] += 1
    _VISION_SESSION["last_snapshot_at"] = captured_at or utc_now_iso()
    latest_snapshot = {
        "snapshot_id": job_id,
        "session_id": session_id,
        "camera_id": camera_id,
        "captured_at": _VISION_SESSION["last_snapshot_at"],
        "source": "dojo_robot_camera",
        "transport": "image_base64",
        "media_type": media_type,
        "width": width,
        "height": height,
        "frame_summary": frame_summary,
        "image_base64": image_base64,
        "observations": observations or [],
    }
    _VISION_SESSION["latest_snapshot"] = latest_snapshot
    _VISION_SESSION["pending_request"] = None
    return {
        "ok": True,
        "message": "Vision snapshot received from %s." % camera_id,
        "snapshot": latest_snapshot,
        "status": get_vision_status(),
    }


def capture_snapshot(*, world: dict[str, Any], note: str = "", camera_id: str | None = None) -> dict[str, Any]:
    requested = request_snapshot(note=note, camera_id=camera_id)
    if not requested["ok"]:
        return requested

    effective_camera_id = requested["requested_snapshot"]["camera_id"]
    pending_request = requested["requested_snapshot"]
    visible_objects = [item["label"] for item in world.get("objects", [])]
    summary = (
        "Prototype snapshot request for %s sees %s known object(s): %s."
        % (
            effective_camera_id,
            len(visible_objects),
            ", ".join(visible_objects) if visible_objects else "none",
        )
    )
    if note.strip():
        summary += " Operator note: %s." % note.strip()
    return report_snapshot(
        session_id=str(_VISION_SESSION["session_id"]),
        job_id=str(pending_request["job_id"]),
        camera_id=effective_camera_id,
        image_base64="",
        media_type="application/json",
        width=0,
        height=0,
        frame_summary=summary,
        observations=[
            {
                "object_id": item["id"],
                "label": item["label"],
                "confidence": 0.72,
                "position": item["position"],
                "located_on": item.get("located_on"),
            }
            for item in world.get("objects", [])
        ],
    )


def invoke_tool(tool_name: str, arguments: dict[str, Any] | None, *, world: dict[str, Any] | None = None) -> dict[str, Any]:
    args = arguments or {}
    if tool_name == "vision_status":
        return {
            "ok": True,
            "tool_name": tool_name,
            "result": get_vision_status(),
        }
    if tool_name == "vision_start":
        return {
            "ok": True,
            "tool_name": tool_name,
            "result": start_vision_session(
                requested_by=str(args.get("requested_by", "zeitgeist")),
                reason=str(args.get("reason", "")),
                mode=str(args.get("mode", "snapshot")),
                camera_id=str(args.get("camera_id", "front_cam")),
            ),
        }
    if tool_name == "vision_snapshot":
        return {
            "ok": True,
            "tool_name": tool_name,
            "result": request_snapshot(
                note=str(args.get("note", "")),
                camera_id=str(args.get("camera_id", "")) or None,
            ),
        }
    if tool_name == "vision_stop":
        return {
            "ok": True,
            "tool_name": tool_name,
            "result": stop_vision_session(session_id=args.get("session_id")),
        }
    raise ValueError("Unsupported MCP tool: %s" % tool_name)
