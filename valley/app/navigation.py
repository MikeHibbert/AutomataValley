from __future__ import annotations

import re
from typing import Any

ROOM_WAYPOINTS: dict[str, dict[str, float]] = {
    "center": {"x": 0.0, "y": 0.0, "z": 0.0},
    "door": {"x": 0.0, "y": 0.0, "z": 5.0},
    "table": {"x": 3.0, "y": 0.0, "z": 1.5},
    "charging_station": {"x": -3.0, "y": 0.0, "z": -3.0},
    "north_zone": {"x": 0.0, "y": 0.0, "z": 4.0},
    "south_zone": {"x": 0.0, "y": 0.0, "z": -4.0},
    "east_zone": {"x": 4.0, "y": 0.0, "z": 0.0},
    "west_zone": {"x": -4.0, "y": 0.0, "z": 0.0},
}

DIRECTION_TARGETS = {
    "north": "north_zone",
    "south": "south_zone",
    "east": "east_zone",
    "west": "west_zone",
}

STOP_COMMANDS = {
    "stop",
    "wait",
    "halt",
    "cancel current task",
}

TARGET_ALIASES = {
    "center": "center",
    "middle": "center",
    "door": "door",
    "table": "table",
    "charging station": "charging_station",
    "charger": "charging_station",
    "north": "north_zone",
    "south": "south_zone",
    "east": "east_zone",
    "west": "west_zone",
    "north zone": "north_zone",
    "south zone": "south_zone",
    "east zone": "east_zone",
    "west zone": "west_zone",
}


class CommandParseError(ValueError):
    """Raised when a transcript does not match the supported command grammar."""


def normalize_text(text: str) -> str:
    normalized = re.sub(r"\s+", " ", text.strip().lower())
    return normalized


def canonicalize_target(target: str) -> str:
    cleaned = normalize_text(target)
    if cleaned.startswith("the "):
        cleaned = cleaned[4:]
    if cleaned not in TARGET_ALIASES:
        raise CommandParseError(f"Unsupported target: {target}")
    return TARGET_ALIASES[cleaned]


def parse_navigation_command(text: str) -> dict[str, str]:
    normalized = normalize_text(text)

    if normalized in STOP_COMMANDS:
        return {"intent": "stop_motion"}

    direction_match = re.fullmatch(r"(?:move|go) (north|south|east|west)", normalized)
    if direction_match:
        direction = direction_match.group(1)
        return {
            "intent": "move_direction",
            "direction": direction,
            "target": DIRECTION_TARGETS[direction],
        }

    target_match = re.fullmatch(r"(?:go|move) to (.+)", normalized)
    if target_match:
        target = canonicalize_target(target_match.group(1))
        return {
            "intent": "navigate_to",
            "target": target,
        }

    raise CommandParseError(f"Unsupported command: {text}")


def build_task_events(
    *,
    command_id: str,
    task_id: str,
    session_id: str,
    robot_id: str,
    intent: dict[str, str],
    timestamp: str,
) -> list[dict[str, Any]]:
    event_type = intent["intent"]
    if event_type == "stop_motion":
        return [
            {
                "event_id": f"{task_id}-cancelled",
                "timestamp": timestamp,
                "session_id": session_id,
                "task_id": task_id,
                "command_id": command_id,
                "robot_id": robot_id,
                "event_type": "task_cancelled",
                "status": "completed",
                "data": {"reason": "operator_stop"},
            }
        ]

    target = intent["target"]
    position = ROOM_WAYPOINTS[target]
    facing = intent.get("direction") or target.removesuffix("_zone")

    return [
        {
            "event_id": f"{task_id}-started",
            "timestamp": timestamp,
            "session_id": session_id,
            "task_id": task_id,
            "command_id": command_id,
            "robot_id": robot_id,
            "event_type": "task_started",
            "status": "active",
            "data": {"intent": event_type, "target": target},
        },
        {
            "event_id": f"{task_id}-moving",
            "timestamp": timestamp,
            "session_id": session_id,
            "task_id": task_id,
            "command_id": command_id,
            "robot_id": robot_id,
            "event_type": "robot_moving",
            "status": "active",
            "data": {
                "position": position,
                "target": target,
                "facing": facing,
                "speed": 1.0,
            },
        },
        {
            "event_id": f"{task_id}-arrived",
            "timestamp": timestamp,
            "session_id": session_id,
            "task_id": task_id,
            "command_id": command_id,
            "robot_id": robot_id,
            "event_type": "robot_arrived",
            "status": "completed",
            "data": {
                "position": position,
                "target": target,
                "facing": facing,
            },
        },
    ]
