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
    parse_dojo_command,
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
        intent = parse_dojo_command(normalized)
        return _execute_response(normalized, intent)
    except CommandParseError:
        pass

    pre_llm_result = _interpret_with_pre_llm_heuristics(normalized)
    if pre_llm_result is not None:
        return pre_llm_result

    llm_result = _interpret_with_llm(normalized)
    if llm_result is not None:
        return llm_result

    return _interpret_with_post_llm_heuristics(normalized)


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
            "Use execute only when you can map directly to one supported command. "
            "Use clarify when the request sounds like a supported navigation action but remains ambiguous. "
            "Use reject when the request is unsupported. "
            "For execute, canonical_command must be exactly one supported command. "
            "For clarify, canonical_command must be null and suggestions must contain 1 or 2 supported commands. "
            "For reject, canonical_command must be null. "
            "Examples: "
            "'move backwards' -> execute 'move south'. "
            "'back up' -> execute 'move south'. "
            "'take a step to the right' -> execute 'move east'. "
            "'go over to the table' -> execute 'go to table'. "
            "'pick up the mug' -> reject."
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
        "temperature": 0.1,
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
    suggestions = _coerce_supported_commands(parsed.get("suggestions", []))

    if disposition not in {"execute", "clarify", "reject"}:
        return None

    if disposition == "execute":
        if canonical_command is None:
            canonical_command = normalized
        try:
            intent = parse_dojo_command(canonical_command)
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

    if canonical_command is not None and _is_supported_command(canonical_command):
        if disposition == "clarify" and canonical_command not in suggestions:
            suggestions = [canonical_command] + suggestions
    canonical_command = None

    fallback_message = _build_non_execute_message(disposition, suggestions)
    return {
        "interpretation": {
            "disposition": disposition,
            "message": message or fallback_message,
            "spoken_response": spoken_response or message or fallback_message,
            "canonical_command": canonical_command,
            "suggestions": suggestions[:2],
        },
        "intent": None,
    }


def _interpret_with_pre_llm_heuristics(normalized: str) -> dict[str, Any] | None:
    direction_hint = _extract_direction_hint(normalized)
    if direction_hint is not None:
        intent = parse_navigation_command(direction_hint)
        return {
            "interpretation": {
                "disposition": "execute",
                "message": _build_execution_message(intent),
                "spoken_response": _build_execution_message(intent),
                "canonical_command": direction_hint,
                "suggestions": [],
            },
            "intent": intent,
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

    return None


def _interpret_with_post_llm_heuristics(normalized: str) -> dict[str, Any]:
    unsupported_keywords = {"pick", "grab", "lift", "open", "close", "wave", "dance"}
    if any(keyword in normalized.split(" ") for keyword in unsupported_keywords):
        message = "I can help with navigation right now. Try saying move north or go to table."
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
        message = _build_clarification_message(close_matches)
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

    message = "I did not catch a supported navigation command. Try move north, go to table, or stop."
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
    forward_phrases = {
        "move forward",
        "go forward",
        "forward",
        "walk forward",
        "step forward",
        "take a step forward",
        "go ahead",
        "walk ahead",
    }
    backward_phrases = {
        "move backward",
        "move backwards",
        "go backward",
        "go backwards",
        "backward",
        "backwards",
        "move back",
        "go back",
        "back up",
        "step back",
        "take a step back",
        "walk back",
    }
    left_phrases = {
        "move left",
        "go left",
        "left",
        "step left",
        "take a step left",
        "take a step to the left",
        "move to the left",
    }
    right_phrases = {
        "move right",
        "go right",
        "right",
        "step right",
        "take a step right",
        "take a step to the right",
        "move to the right",
    }

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
        "go over to ",
        "head over to ",
        "walk over to ",
        "please go to ",
        "please move to ",
        "please head to ",
        "please go over to ",
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
    if intent["intent"] == "move_direction":
        return "Okay, moving %s." % intent.get("direction", "there")
    if intent["intent"] == "navigate_to":
        return "Okay, heading to %s." % str(intent.get("target", "")).replace("_", " ")
    if intent["intent"] == "navigate_to_object":
        return "Okay, moving to the %s." % str(intent.get("target_object", "")).replace("_", " ")
    if intent["intent"] == "inspect_scene":
        return "Okay, taking a look around the dojo."
    if intent["intent"] == "inspect_object":
        return "Okay, inspecting the %s." % str(intent.get("target_object", "")).replace("_", " ")
    if intent["intent"] == "inspect_surface":
        return "Okay, inspecting the %s." % str(intent.get("target_surface", "")).replace("_", " ")
    if intent["intent"] == "pick_up_object":
        return "Okay, picking up the %s." % str(intent.get("target_object", "")).replace("_", " ")
    if intent["intent"] == "place_object":
        return "Okay, placing the %s on the %s." % (
            str(intent.get("target_object", "")).replace("_", " "),
            str(intent.get("target_surface", "")).replace("_", " "),
        )
    return "Okay, handling that task."


def _build_non_execute_message(disposition: str, suggestions: list[str]) -> str:
    if disposition == "clarify":
        return _build_clarification_message(suggestions)
    return "I can help with navigation commands like move north, go to table, or stop."


def _build_clarification_message(suggestions: list[str]) -> str:
    if len(suggestions) == 1:
        return "I heard something close to that. Did you mean %s?" % suggestions[0]
    if len(suggestions) >= 2:
        return "I heard something close to that. Did you mean %s or %s?" % (suggestions[0], suggestions[1])
    return "I think that was close to a navigation command, but I need a little more detail."


def _coerce_supported_commands(value: Any) -> list[str]:
    if isinstance(value, list):
        suggestions: list[str] = []
        for item in value:
            command = str(item).strip().lower()
            if command and _is_supported_command(command) and command not in suggestions:
                suggestions.append(command)
        return suggestions
    return []


def _is_supported_command(command: str) -> bool:
    try:
        parse_dojo_command(command)
    except CommandParseError:
        return False
    return True
