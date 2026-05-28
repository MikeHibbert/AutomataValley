from __future__ import annotations

from typing import Any

ROOM_SURFACES: dict[str, dict[str, Any]] = {
    "center": {
        "id": "center",
        "label": "Center",
        "kind": "zone",
        "position": {"x": 0.0, "y": 0.0, "z": 0.0},
    },
    "door": {
        "id": "door",
        "label": "Door",
        "kind": "landmark",
        "position": {"x": 0.0, "y": 0.0, "z": 5.0},
    },
    "table": {
        "id": "table",
        "label": "Table",
        "kind": "surface",
        "position": {"x": 3.0, "y": 0.0, "z": 1.5},
    },
    "charging_station": {
        "id": "charging_station",
        "label": "Charging Station",
        "kind": "station",
        "position": {"x": -3.0, "y": 0.0, "z": -3.0},
    },
    "north_zone": {
        "id": "north_zone",
        "label": "North Zone",
        "kind": "zone",
        "position": {"x": 0.0, "y": 0.0, "z": 4.0},
    },
    "south_zone": {
        "id": "south_zone",
        "label": "South Zone",
        "kind": "zone",
        "position": {"x": 0.0, "y": 0.0, "z": -4.0},
    },
    "east_zone": {
        "id": "east_zone",
        "label": "East Zone",
        "kind": "zone",
        "position": {"x": 4.0, "y": 0.0, "z": 0.0},
    },
    "west_zone": {
        "id": "west_zone",
        "label": "West Zone",
        "kind": "zone",
        "position": {"x": -4.0, "y": 0.0, "z": 0.0},
    },
    "left_shelf": {
        "id": "left_shelf",
        "label": "Left Shelf",
        "kind": "surface",
        "position": {"x": -4.5, "y": 1.2, "z": 1.5},
    },
}

WORLD_OBJECTS: dict[str, dict[str, Any]] = {
    "red_mug": {
        "id": "red_mug",
        "label": "Red Mug",
        "category": "drinkware",
        "pickupable": True,
        "position": {"x": 3.1, "y": 0.85, "z": 1.3},
        "located_on": "table",
        "aliases": ["red mug", "mug", "cup"],
        "color_hint": "red",
    },
    "parts_box": {
        "id": "parts_box",
        "label": "Parts Box",
        "category": "container",
        "pickupable": True,
        "position": {"x": 2.5, "y": 0.85, "z": 1.8},
        "located_on": "table",
        "aliases": ["parts box", "box", "storage box"],
        "color_hint": "orange",
    },
    "inspection_camera": {
        "id": "inspection_camera",
        "label": "Inspection Camera",
        "category": "sensor",
        "pickupable": False,
        "position": {"x": -1.5, "y": 1.2, "z": -2.8},
        "located_on": "charging_station",
        "aliases": ["camera", "inspection camera"],
        "color_hint": "blue",
    },
    "screwdriver": {
        "id": "screwdriver",
        "label": "Screwdriver",
        "category": "tool",
        "pickupable": True,
        "position": {"x": -4.3, "y": 1.35, "z": 1.5},
        "located_on": "left_shelf",
        "aliases": ["screwdriver", "driver", "tool"],
        "color_hint": "yellow",
    },
}

SURFACE_ALIASES: dict[str, str] = {
    "center": "center",
    "middle": "center",
    "door": "door",
    "table": "table",
    "desk": "table",
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

OBJECT_ALIASES: dict[str, str] = {}
for object_id, object_data in WORLD_OBJECTS.items():
    for alias in object_data["aliases"]:
        OBJECT_ALIASES[alias] = object_id

ROBOT_CAMERAS: list[dict[str, Any]] = [
    {
        "id": "front_cam",
        "label": "Front Camera",
        "mount": "forward",
        "default": True,
        "resolution": {"width": 512, "height": 512},
    },
    {
        "id": "left_cam",
        "label": "Left Camera",
        "mount": "left",
        "default": False,
        "resolution": {"width": 512, "height": 512},
    },
    {
        "id": "right_cam",
        "label": "Right Camera",
        "mount": "right",
        "default": False,
        "resolution": {"width": 512, "height": 512},
    },
    {
        "id": "rear_cam",
        "label": "Rear Camera",
        "mount": "rear",
        "default": False,
        "resolution": {"width": 512, "height": 512},
    },
]


def get_surface(surface_id: str) -> dict[str, Any]:
    return ROOM_SURFACES[surface_id]


def get_object(object_id: str) -> dict[str, Any]:
    return WORLD_OBJECTS[object_id]


def canonicalize_surface(name: str) -> str | None:
    cleaned = _clean_entity_name(name)
    return SURFACE_ALIASES.get(cleaned)


def canonicalize_object(name: str) -> str | None:
    cleaned = _clean_entity_name(name)
    return OBJECT_ALIASES.get(cleaned)


def build_world_state() -> dict[str, Any]:
    return {
        "room": {
            "id": "dojo-room-01",
            "label": "AutomataValley Dojo",
        },
        "surfaces": list(ROOM_SURFACES.values()),
        "objects": [
            {
                "id": data["id"],
                "label": data["label"],
                "category": data["category"],
                "pickupable": data["pickupable"],
                "position": data["position"],
                "located_on": data["located_on"],
                "color_hint": data["color_hint"],
            }
            for data in WORLD_OBJECTS.values()
        ],
        "robot_state": {
            "robot_id": "dojo-bot-01",
            "held_object": None,
            "camera_mode": "forward_observer",
            "cameras": list(ROBOT_CAMERAS),
        },
        "vision": {
            "image_upload": True,
            "live_feed": {
                "enabled": False,
                "mode": "mcp_on_demand_placeholder",
                "source": None,
                "camera_id": "front_cam",
                "available_cameras": [camera["id"] for camera in ROBOT_CAMERAS],
                "notes": "Still-image upload is active. On-demand MCP vision sessions can request snapshots from onboard robot cameras.",
            },
        },
        "capabilities": {
            "navigation": True,
            "object_navigation": True,
            "inspection": True,
            "image_observation": True,
            "live_feed_placeholder": True,
            "mcp_on_demand_vision": True,
            "manipulation_foundation": True,
            "pick_up": True,
            "place": True,
        },
    }


def infer_image_observations(filename: str, hint_text: str = "") -> list[dict[str, Any]]:
    haystack = _clean_entity_name("%s %s" % (filename, hint_text))
    observations: list[dict[str, Any]] = []
    for object_id, data in WORLD_OBJECTS.items():
        if any(alias in haystack for alias in data["aliases"]):
            observations.append(
                {
                    "object_id": object_id,
                    "label": data["label"],
                    "confidence": 0.74,
                    "located_on": data["located_on"],
                    "position": data["position"],
                }
            )
    if not observations:
        for surface_id, data in ROOM_SURFACES.items():
            if data["label"].lower() in haystack:
                observations.append(
                    {
                        "surface_id": surface_id,
                        "label": data["label"],
                        "confidence": 0.58,
                        "position": data["position"],
                    }
                )
    return observations


def _clean_entity_name(name: str) -> str:
    cleaned = " ".join(name.strip().lower().split())
    if cleaned.startswith("the "):
        cleaned = cleaned[4:]
    return cleaned
