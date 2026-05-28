from __future__ import annotations

import re
from typing import Any

from .world_model import (
    ROOM_SURFACES,
    WORLD_OBJECTS,
    canonicalize_object,
    canonicalize_surface,
    get_object,
    get_surface,
)

ROOM_WAYPOINTS: dict[str, dict[str, float]] = {
    surface_id: surface["position"]
    for surface_id, surface in ROOM_SURFACES.items()
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
    "left shelf": "left_shelf",
    "shelf": "left_shelf",
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


def parse_dojo_command(text: str) -> dict[str, Any]:
    try:
        return parse_navigation_command(text)
    except CommandParseError:
        pass

    normalized = normalize_text(text)

    if normalized in {"look around", "scan the room", "inspect scene", "what can you see"}:
        return {"intent": "inspect_scene", "target": "room"}

    look_match = re.fullmatch(r"(?:look at|inspect) (.+)", normalized)
    if look_match:
        target_name = look_match.group(1)
        object_id = canonicalize_object(target_name)
        if object_id is not None:
            target_object = get_object(object_id)
            return {
                "intent": "inspect_object",
                "target_object": object_id,
                "target": object_id,
                "position": target_object["position"],
            }
        surface_id = canonicalize_surface(target_name)
        if surface_id is not None:
            target_surface = get_surface(surface_id)
            return {
                "intent": "inspect_surface",
                "target_surface": surface_id,
                "target": surface_id,
                "position": target_surface["position"],
            }

    navigate_match = re.fullmatch(r"(?:go|move|walk|navigate|head) to (.+)", normalized)
    if navigate_match:
        target_name = navigate_match.group(1)
        object_id = canonicalize_object(target_name)
        if object_id is not None:
            target_object = get_object(object_id)
            return {
                "intent": "navigate_to_object",
                "target_object": object_id,
                "target": object_id,
                "position": target_object["position"],
                "target_surface": target_object["located_on"],
            }

    pick_up_match = re.fullmatch(r"(?:pick up|grab|lift) (.+)", normalized)
    if pick_up_match:
        object_id = canonicalize_object(pick_up_match.group(1))
        if object_id is None:
            raise CommandParseError(f"Unsupported manipulation target: {text}")
        target_object = get_object(object_id)
        if not target_object["pickupable"]:
            raise CommandParseError(f"Object is not pickupable: {text}")
        return {
            "intent": "pick_up_object",
            "target_object": object_id,
            "target": object_id,
            "position": target_object["position"],
            "target_surface": target_object["located_on"],
        }

    place_match = re.fullmatch(r"(?:place|put) (.+) on (.+)", normalized)
    if place_match:
        object_id = canonicalize_object(place_match.group(1))
        surface_id = canonicalize_surface(place_match.group(2))
        if object_id is None or surface_id is None:
            raise CommandParseError(f"Unsupported placement target: {text}")
        target_surface = get_surface(surface_id)
        return {
            "intent": "place_object",
            "target_object": object_id,
            "target_surface": surface_id,
            "target": surface_id,
            "position": target_surface["position"],
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

    if event_type == "navigate_to_object":
        return _build_navigation_to_object_events(
            command_id=command_id,
            task_id=task_id,
            session_id=session_id,
            robot_id=robot_id,
            intent=intent,
            timestamp=timestamp,
        )

    if event_type in {"inspect_scene", "inspect_object", "inspect_surface"}:
        return _build_inspection_events(
            command_id=command_id,
            task_id=task_id,
            session_id=session_id,
            robot_id=robot_id,
            intent=intent,
            timestamp=timestamp,
        )

    if event_type in {"pick_up_object", "place_object"}:
        return _build_manipulation_events(
            command_id=command_id,
            task_id=task_id,
            session_id=session_id,
            robot_id=robot_id,
            intent=intent,
            timestamp=timestamp,
        )

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


def _build_navigation_to_object_events(
    *,
    command_id: str,
    task_id: str,
    session_id: str,
    robot_id: str,
    intent: dict[str, Any],
    timestamp: str,
) -> list[dict[str, Any]]:
    target_object = get_object(intent["target_object"])
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
            "data": {"intent": "navigate_to_object", "target": target_object["id"]},
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
                "position": target_object["position"],
                "target": target_object["id"],
                "focus_object": target_object["label"],
                "speed": 0.8,
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
                "position": target_object["position"],
                "target": target_object["id"],
                "focus_object": target_object["label"],
                "surface": target_object["located_on"],
            },
        },
    ]


def _build_inspection_events(
    *,
    command_id: str,
    task_id: str,
    session_id: str,
    robot_id: str,
    intent: dict[str, Any],
    timestamp: str,
) -> list[dict[str, Any]]:
    target = intent.get("target", "room")
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
            "data": {"intent": intent["intent"], "target": target},
        },
        {
            "event_id": f"{task_id}-observed",
            "timestamp": timestamp,
            "session_id": session_id,
            "task_id": task_id,
            "command_id": command_id,
            "robot_id": robot_id,
            "event_type": "scene_observed",
            "status": "completed",
            "data": {
                "target": target,
                "visible_objects": [data["id"] for data in WORLD_OBJECTS.values()],
            },
        },
    ]


def _build_manipulation_events(
    *,
    command_id: str,
    task_id: str,
    session_id: str,
    robot_id: str,
    intent: dict[str, Any],
    timestamp: str,
) -> list[dict[str, Any]]:
    target_object = get_object(intent["target_object"])
    if intent["intent"] == "pick_up_object":
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
                "data": {"intent": "pick_up_object", "target": target_object["id"]},
            },
            {
                "event_id": f"{task_id}-picked",
                "timestamp": timestamp,
                "session_id": session_id,
                "task_id": task_id,
                "command_id": command_id,
                "robot_id": robot_id,
                "event_type": "object_picked_up",
                "status": "completed",
                "data": {
                    "target": target_object["id"],
                    "held_object": target_object["id"],
                    "surface": target_object["located_on"],
                },
            },
        ]

    target_surface = get_surface(intent["target_surface"])
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
            "data": {"intent": "place_object", "target": target_surface["id"]},
        },
        {
            "event_id": f"{task_id}-placed",
            "timestamp": timestamp,
            "session_id": session_id,
            "task_id": task_id,
            "command_id": command_id,
            "robot_id": robot_id,
            "event_type": "object_placed",
            "status": "completed",
            "data": {
                "target": target_surface["id"],
                "held_object": None,
                "placed_object": target_object["id"],
                "surface": target_surface["id"],
                "position": target_surface["position"],
            },
        },
    ]
