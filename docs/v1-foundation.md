# AutomataValley V1 Foundation

## Purpose

This document locks the initial implementation target for `AutomataValley`.

V1 is a robot-first Dojo experience:

- The user speaks a navigation command in the Dojo.
- The Dojo uses local NVIDIA Parakeet speech-to-text.
- The transcribed text is sent to the Dockerized Valley backend.
- The Valley interprets the command as a robot navigation task.
- The Dojo visualizes the robot moving in response.

The Valley remains the backend intelligence layer. The Dojo should not present Campfire/Valley internals as the main visual subject.

## V1 Scope

### In Scope

- Local speech-to-text using NVIDIA Parakeet
- Push-to-talk voice capture
- Text command submission from Dojo to Valley
- Movement and navigation commands only
- Robot-first 3D Dojo scene
- Minimal operator overlay
- Dockerized Valley backend development loop
- Published `campfirevalley` PyPI package as the starting dependency

### Out Of Scope

- Visualizing Campfire/Valley topology as the main UI
- Manipulation and grasping tasks
- Rich backend diagnostics panels
- Multi-robot support
- Always-listening voice mode
- Direct low-level hardware control from the Dojo

## Initial System Topology

- `dojo`
  - Godot application
  - room rendering
  - robot visualization
  - push-to-talk UI
  - local Parakeet speech-to-text
- `bridge`
  - thin adapter between Dojo and Valley
  - forwards command payloads
  - normalizes events for Dojo consumption
- `valley`
  - Python backend using published `campfirevalley`
  - runs in Docker
  - interprets commands into navigation tasks
  - publishes robot-centric events
- `redis`
  - runs in Docker
  - supports Valley messaging/pub-sub as needed

## V1 Command Grammar

The first command grammar should be intentionally constrained and deterministic.

### Supported Command Families

- Directional movement
- Named waypoint navigation
- Basic halt/cancel control

### Directional Movement

Accepted examples:

- `move north`
- `move south`
- `move east`
- `move west`
- `go north`
- `go south`
- `go east`
- `go west`

Normalized intent:

```json
{
  "intent": "move_direction",
  "direction": "north"
}
```

### Named Waypoint Navigation

Accepted examples:

- `go to door`
- `go to table`
- `go to center`
- `go to charging station`
- `move to door`
- `move to table`

Normalized intent:

```json
{
  "intent": "navigate_to",
  "target": "door"
}
```

### Stop And Cancel

Accepted examples:

- `stop`
- `wait`
- `cancel current task`
- `halt`

Normalized intent:

```json
{
  "intent": "stop_motion"
}
```

## Initial Room Model

The first Dojo scene should use a simple waypoint-based room model rather than full navigation complexity.

### Required Waypoints

- `center`
- `door`
- `table`
- `charging_station`
- `north_zone`
- `south_zone`
- `east_zone`
- `west_zone`

### Notes

- Directional commands may map either to short relative movement or to named directional zones in the room.
- For V1, mapping directions to fixed zones is acceptable if it simplifies deterministic behavior.
- The room should be visually obvious enough that waypoint movement is easy to understand.

## Command Payload

The Dojo should submit a stable command payload to the backend.

```json
{
  "command_id": "uuid",
  "timestamp": "2026-05-25T12:00:00Z",
  "session_id": "uuid",
  "robot_id": "dojo-bot-01",
  "source": "dojo_voice",
  "transcript": "move north",
  "command_text": "move north",
  "command_type": "navigation",
  "metadata": {
    "stt_engine": "parakeet",
    "confidence": 0.94
  }
}
```

## Event Schema

The backend or bridge should send robot-centric events back to the Dojo.

```json
{
  "event_id": "uuid",
  "timestamp": "2026-05-25T12:00:02Z",
  "session_id": "uuid",
  "task_id": "uuid",
  "command_id": "uuid",
  "robot_id": "dojo-bot-01",
  "event_type": "robot_moving",
  "status": "active",
  "data": {
    "position": { "x": 2, "y": 0, "z": 1 },
    "target": "north_zone",
    "facing": "north",
    "speed": 1.0
  }
}
```

### V1 Event Types

- `voice_received`
- `transcript_ready`
- `command_submitted`
- `command_parsed`
- `task_started`
- `robot_turning`
- `robot_moving`
- `robot_arrived`
- `task_cancelled`
- `task_failed`
- `backend_disconnected`
- `backend_reconnected`

## Minimal Overlay

The Dojo overlay should remain small and operator-focused.

### Display Fields

- microphone state
- transcript text
- submitted command
- robot state
- current target
- connection state

### Non-Goals

- no Campfire graph
- no Valley topology view
- no verbose backend event stream in the main scene

## Docker Development Loop

The Valley backend runs in Docker during development.

Expected loop:

1. Edit backend code.
2. Rebuild the Valley container.
3. Restart the Valley service.
4. Allow the Dojo to reconnect automatically.
5. Re-run the navigation command scenario.

This means reconnect handling is a required V1 behavior, not an enhancement.

## First Milestone

The first milestone is complete when the following scenario works reliably:

1. The user presses push-to-talk in the Dojo.
2. The user says `move north`.
3. Parakeet transcribes the command locally.
4. The Dojo submits the command payload to the Valley.
5. The Valley parses it into a navigation intent.
6. The Valley emits robot-centric events.
7. The Dojo animates the robot moving north.
8. The overlay updates with transcript, command, and robot state.
9. Restarting the backend does not require restarting the Dojo manually.

## Immediate Next Development Step

After approving this foundation, the next implementation step should be:

1. scaffold the Python backend and bridge layout
2. create the Docker Compose topology for `valley` and `redis`
3. define a minimal command intake endpoint or channel
4. create a mock navigation loop that emits test events

The initial backend should use the published `campfirevalley` package rather than a local clone of the upstream repository.
