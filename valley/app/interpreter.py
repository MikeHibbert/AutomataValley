from __future__ import annotations

import difflib
import json
import os
from typing import Any

import httpx

from .navigation import (
    CommandParseError,
    STOP_COMMANDS,
    TARGET_ALIASES,
    canonicalize_target,
    normalize_text,
    parse_navigation_command,
)

DEFAULT_COMMAND_SUGGESTIONS = [
    "move north",
    "move south",
    "move east",
    "move west",
    "go to table",
    "go to door",
    "go to center",
    "go to charging station",
    "stop",
]

LLM_URL = os.getenv("AUTOMATAVALLEY_LLM_URL", "").strip()
LLM_API_KEY = os.getenv("AUTOMATAVALLEY_LLM_API_KEY", "").strip()
LLM_MODEL = os.getenv("AUTOMATAVALLEY_LLM_MODEL", "gpt-4o-mini").strip()


def interpret_command(command_text: str) -> dict[str, Any]:
    normalized = normalize_text(command_text)

    try:
        intent = parse_navigation_command(normalized)
        return _execute_response(normalized, intent)
    except CommandParseError:
        pass

    llm_result = _interpret_with_llm(normalized)
    if llm_result is not None:
        return llm_result

    return _interpret_with_heuristics(normalized)


def _interpret_with_llm(normalized: str) -> dict[str, Any] | None:
    if not LLM_URL:
        return None

    prompt = {
        "role": "system",
        "content": (
            "You interpret robot navigation requests. "
            "Only use the supported commands and never invent capabilities. "
            "Return compact JSON with keys disposition, canonical_command, message, spoken_response, suggestions. "
            "disposition must be one of execute, clarify, reject. "
            "Allowed commands are: "
            + ", ".join(DEFAULT_COMMAND_SUGGESTIONS)
            + ". "
            "Use clarify when the request is ambiguous, execute when it maps cleanly, reject when unsupported."
        ),
    }
    user_message = {"role": "user", "content": normalized}
    headers = {"Content-Type": "application/json"}
    if LLM_API_KEY:
        headers["Authorization"] = f"Bearer {LLM_API_KEY}"

    payload = {
        "model": LLM_MODEL,
        "response_format": {"type": "json_object"},
        "messages": [prompt, user_message],
    }

    try:
        response = httpx.post(LLM_URL, json=payload, headers=headers, timeout=20.0)
        response.raise_for_status()
        body = response.json()
        content = body["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        return _normalize_llm_result(normalized, parsed)
    except Exception:
        return None


def _normalize_llm_result(normalized: str, parsed: dict[str, Any]) -> dict[str, Any] | None:
    disposition = str(parsed.get("disposition", "")).strip().lower()
    canonical_command = str(parsed.get("canonical_command", "")).strip().lower() or None
    message = str(parsed.get("message", "")).strip()
    spoken_response = str(parsed.get("spoken_response", "")).strip() or message
    suggestions = _coerce_suggestions(parsed.get("suggestions", []))

    if disposition not in {"execute", "clarify", "reject"}:
        return None

    if disposition == "execute":
        if canonical_command is None:
            canonical_command = normalized
        try:
            intent = parse_navigation_command(canonical_command)
        except CommandParseError:
            return None
        return {
            "interpretation": {
                "disposition": "execute",
                "message": message or _build_execution_message(intent),
                "spoken_response": spoken_response or message or _build_execution_message(intent),
                "canonical_command": canonical_command,
                "suggestions": [],
            },
            "intent": intent,
        }

    return {
        "interpretation": {
            "disposition": disposition,
            "message": message or "I could not confidently interpret that command.",
            "spoken_response": spoken_response or message or "I could not confidently interpret that command.",
            "canonical_command": canonical_command,
            "suggestions": suggestions[:2],
        },
        "intent": None,
    }


def _interpret_with_heuristics(normalized: str) -> dict[str, Any]:
    direction_hint = _extract_direction_hint(normalized)
    if direction_hint is not None:
        message = "Did you mean %s?" % direction_hint
        return {
            "interpretation": {
                "disposition": "clarify",
                "message": message,
                "spoken_response": message,
                "canonical_command": None,
                "suggestions": [direction_hint],
            },
            "intent": None,
        }

    waypoint_command = _extract_waypoint_command(normalized)
    if waypoint_command is not None:
        intent = parse_navigation_command(waypoint_command)
        return {
            "interpretation": {
                "disposition": "execute",
                "message": _build_execution_message(intent),
                "spoken_response": _build_execution_message(intent),
                "canonical_command": waypoint_command,
                "suggestions": [],
            },
            "intent": intent,
        }

    if normalized in {"cancel", "cancel task", "stop now"}:
        intent = parse_navigation_command("stop")
        return {
            "interpretation": {
                "disposition": "execute",
                "message": "Okay, stopping the robot.",
                "spoken_response": "Okay, stopping the robot.",
                "canonical_command": "stop",
                "suggestions": [],
            },
            "intent": intent,
        }

    unsupported_keywords = {"pick", "grab", "lift", "open", "close", "wave", "dance"}
    if any(keyword in normalized.split(" ") for keyword in unsupported_keywords):
        message = "I can help with navigation right now. Try move north or go to table."
        return {
            "interpretation": {
                "disposition": "reject",
                "message": message,
                "spoken_response": message,
                "canonical_command": None,
                "suggestions": ["move north", "go to table"],
            },
            "intent": None,
        }

    close_matches = difflib.get_close_matches(normalized, DEFAULT_COMMAND_SUGGESTIONS, n=2, cutoff=0.45)
    if close_matches:
        if len(close_matches) == 1:
            message = "Did you mean %s?" % close_matches[0]
        else:
            message = "Did you mean %s or %s?" % (close_matches[0], close_matches[1])
        return {
            "interpretation": {
                "disposition": "clarify",
                "message": message,
                "spoken_response": message,
                "canonical_command": None,
                "suggestions": close_matches[:2],
            },
            "intent": None,
        }

    message = "I did not understand that yet. Try move north, go to table, or stop."
    return {
        "interpretation": {
            "disposition": "reject",
            "message": message,
            "spoken_response": message,
            "canonical_command": None,
            "suggestions": ["move north", "go to table"],
        },
        "intent": None,
    }


def _extract_direction_hint(normalized: str) -> str | None:
    forward_phrases = {"move forward", "go forward", "forward", "walk forward"}
    backward_phrases = {"move backward", "move backwards", "go backward", "go backwards", "backward", "backwards", "move back", "go back"}
    left_phrases = {"move left", "go left", "left"}
    right_phrases = {"move right", "go right", "right"}

    if normalized in forward_phrases:
        return "move north"
    if normalized in backward_phrases:
        return "move south"
    if normalized in left_phrases:
        return "move west"
    if normalized in right_phrases:
        return "move east"
    return None


def _extract_waypoint_command(normalized: str) -> str | None:
    prefixes = (
        "go to ",
        "move to ",
        "head to ",
        "walk to ",
        "navigate to ",
        "please go to ",
        "please move to ",
    )
    for prefix in prefixes:
        if normalized.startswith(prefix):
            raw_target = normalized[len(prefix) :]
            try:
                target = canonicalize_target(raw_target)
            except CommandParseError:
                continue
            return "go to %s" % target.replace("_", " ")

    words = normalized.split(" ")
    known_targets = sorted(set(TARGET_ALIASES.keys()), key=len, reverse=True)
    for target_alias in known_targets:
        if target_alias in normalized:
            canonical_target = TARGET_ALIASES[target_alias].replace("_", " ")
            if any(token in words for token in ("go", "move", "head", "walk", "navigate")):
                return "go to %s" % canonical_target
    return None


def _execute_response(canonical_command: str, intent: dict[str, Any]) -> dict[str, Any]:
    message = _build_execution_message(intent)
    return {
        "interpretation": {
            "disposition": "execute",
            "message": message,
            "spoken_response": message,
            "canonical_command": canonical_command,
            "suggestions": [],
        },
        "intent": intent,
    }


def _build_execution_message(intent: dict[str, Any]) -> str:
    if intent["intent"] == "stop_motion":
        return "Okay, stopping the robot."
    target = str(intent.get("target", "")).replace("_", " ")
    if intent["intent"] == "move_direction":
        return "Okay, moving %s." % intent.get("direction", target)
    return "Okay, heading to %s." % target


def _coerce_suggestions(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []
