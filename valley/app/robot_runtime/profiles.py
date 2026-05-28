from __future__ import annotations

import json
from pathlib import Path

from .models import RobotProfile


REPO_ROOT = Path(__file__).resolve().parents[3]
ROBOT_PROFILE_DIR = REPO_ROOT / "robot_profiles"


def get_robot_profile_dir() -> Path:
    return ROBOT_PROFILE_DIR


def iter_robot_profile_paths() -> list[Path]:
    return sorted(path for path in ROBOT_PROFILE_DIR.glob("*.json") if path.name != "interface_contract.schema.json")


def load_robot_profile(profile_path: str | Path) -> RobotProfile:
    path = Path(profile_path)
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return RobotProfile.model_validate(payload)


def load_robot_profile_by_id(profile_id: str) -> RobotProfile:
    target_path = ROBOT_PROFILE_DIR / ("%s.json" % profile_id)
    if not target_path.exists():
        raise FileNotFoundError("Robot profile %s was not found at %s" % (profile_id, target_path))
    return load_robot_profile(target_path)


def load_all_robot_profiles() -> dict[str, RobotProfile]:
    profiles: dict[str, RobotProfile] = {}
    for profile_path in iter_robot_profile_paths():
        profile = load_robot_profile(profile_path)
        profiles[profile.profile_id] = profile
    return profiles
