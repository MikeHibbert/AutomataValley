# AutomataValley

AutomataValley is a robot-first prototype that pairs a Godot Dojo visualizer with a Dockerized Python backend.

Today the project supports:

- a 3D Dojo scene in Godot
- a bridge service between the Dojo and Valley
- a Dockerized Valley backend
- Redis for backend support
- local speech-to-text via an NVIDIA Parakeet service in Docker
- command interpretation using local Ollama with `gemma3:latest`
- spoken clarification and status responses through Godot's native text-to-speech
- object-aware world bootstrap for the Dojo
- simple scene observation from uploaded images
- navigation, inspection, and early manipulation scaffolding
- on-demand MCP-style vision sessions with start, snapshot, and stop actions
- onboard robot camera selection for front, left, right, and rear snapshots
- a generic robot runtime with profile-driven transport selection
- an in-process simulation profile for Walker-style motion, status, and vision testing

## Current Status

This repository is an early working prototype.

The current goal is to let you:

- start the backend stack with Docker
- open the Dojo in Godot
- submit text commands
- use push-to-talk voice input
- see the robot respond to navigation tasks
- inspect the current mock dojo world model
- upload a scene image to seed object observations
- start and stop on-demand vision sessions instead of keeping vision always on
- request a picture from a specific robot-mounted camera
- exercise the robot runtime without hardware by using the internal Walker simulation profile

Core command and interpreter tests are in place, and the backend stack is wired together. Voice input is functional but still being actively hardened, so if you are evaluating the project for the first time, start with typed commands before moving on to push-to-talk.

## Architecture

The current local setup is:

- `dojo`
  - Godot 4 project
  - 3D room and robot view
  - operator UI
  - push-to-talk and transcript flow
  - world/object panel with image observation entry point
- `bridge`
  - FastAPI adapter between Dojo and Valley
  - exposes bootstrap, command, image-observation, and on-demand vision endpoints
- `valley`
  - FastAPI command service
  - world model plus strict parser and interpretation layer
  - optional local LLM interpretation through Ollama
- `stt`
  - FastAPI speech-to-text service
  - configured for NVIDIA Parakeet
- `tts`
  - FastAPI text-to-speech service using `espeak-ng`
  - currently kept for backend parity, while the Dojo itself uses Godot native TTS
- `redis`
  - support service for Valley

## Prerequisites

To run this project on your own machine, you currently need:

- Windows with PowerShell
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- [Godot 4.2.2](https://godotengine.org/download/archive/4.2.2-stable/)
- Python 3.10+ if you want to run the tests locally
- [Ollama](https://ollama.com/) if you want the current LLM-backed interpretation flow

You should also have the `gemma3:latest` model available in Ollama:

```bash
ollama pull gemma3:latest
```

The Docker stack is currently configured to call Ollama at:

```text
http://host.docker.internal:11434/v1/chat/completions
```

That works well on Docker Desktop for Windows. If you are running on a different platform, you may need to adjust the Valley LLM URL in `docker/compose.yml`.

## Repository Layout

Key folders:

- `dojo/`
- `bridge/`
- `valley/`
- `stt/`
- `tts/`
- `docker/`
- `tests/`
- `docs/`
- `robot_profiles/`

Useful files:

- `docker/compose.yml`
- `check_stack.ps1`
- `run_dojo.ps1`
- `docs/v1-foundation.md`
- `docs/generic-robot-runtime.md`
- `robot_profiles/walker_tienkung_v2_0_5_1.json`
- `robot_profiles/walker_tienkung_sim.json`

## Getting Started

### 1. Clone The Repository

```bash
git clone https://github.com/MikeHibbert/AutomataValley.git
cd AutomataValley
```

### 2. Install And Start Ollama

Make sure Ollama is running locally and that `gemma3:latest` is installed:

```bash
ollama ls
ollama pull gemma3:latest
```

### 3. Build And Start The Docker Stack

From the repository root:

```bash
docker compose -f docker/compose.yml up --build -d
```

This starts:

- `redis` on `6379`
- `valley` on `8001`
- `bridge` on `8002`
- `stt` on `8003`
- `tts` on `8004`

Check the running containers:

```bash
docker compose -f docker/compose.yml ps
```

### 4. Confirm The Services Are Up

You can check the main health endpoints in a browser or with PowerShell:

```powershell
Invoke-RestMethod http://localhost:8001/health
Invoke-RestMethod http://localhost:8002/health
Invoke-RestMethod http://localhost:8003/health
Invoke-RestMethod http://localhost:8004/health
```

The Dojo bootstrap endpoint is:

```text
http://localhost:8002/api/bootstrap
```

You can also run the local health-check script:

```powershell
powershell -ExecutionPolicy Bypass -File .\check_stack.ps1
```

### 5. Set Your Godot Path

The launcher script currently expects Godot at:

```text
C:\Users\Mike\Documents\Applications\Godot_v4.2.2-stable_win64.exe\Godot_v4.2.2-stable_win64.exe
```

If your Godot executable is somewhere else, edit `run_dojo.ps1` and update the `$godotExe` value before launching.

### 6. Launch The Dojo

To open the project normally:

```powershell
powershell -ExecutionPolicy Bypass -File .\run_dojo.ps1
```

To validate that the Godot project loads without opening the full UI:

```powershell
powershell -ExecutionPolicy Bypass -File .\run_dojo.ps1 -Headless
```

## How To Use The Prototype

### Text Commands

Once the Dojo is connected to the bridge, start by typing commands such as:

- `move north`
- `move south`
- `move east`
- `move west`
- `go to table`
- `go to the mug`
- `look at the screwdriver`
- `what can you see`
- `pick up the mug`
- `place the mug on the table`
- `go to door`
- `go to center`
- `go to charging station`
- `stop`

The robot view and overlay should update when a command is accepted.

### Voice Input

The current voice flow is:

1. Press the push-to-talk button.
2. Speak a navigation request.
3. Stop recording.
4. Wait for the transcript to return from the STT service.
5. Review the transcript and submit or accept a suggestion.

There is also an upload flow for prerecorded audio files if you want a more repeatable test path.

### Natural Language Interpretation

The Valley service first tries exact supported commands and then falls back to interpretation logic.

Examples of phrases the prototype tries to handle include:

- `move forward`
- `move backwards`
- `head to table`
- `take a step to the right`

If Valley cannot confidently interpret the request, it can return:

- `execute`
- `clarify`
- `reject`

The Dojo can then surface suggestions such as `Did you mean move south?`

### Scene Observation

The Dojo now includes a world panel with a first-pass observation flow:

1. Click `Upload Image`.
2. Select a local scene image.
3. Click `Observe Image`.
4. Review the observation result and the currently known objects list.

This is a foundation step toward richer perception and future live-feed support. The current image observer is still a mock grounding layer, not a full visual recognition model.

### On-Demand Vision Tools

The Dojo world panel now also includes the first on-demand vision workflow:

1. Choose a robot camera such as `Front Camera`, `Left Camera`, `Right Camera`, or `Rear Camera`.
2. Click `Start Vision`.
3. When a session is active, click `Snapshot`.
4. The Dojo captures a picture from the selected onboard robot camera and reports it back through the bridge.
5. Review the returned scene summary in the observation panel.
6. Click `Stop Vision` when inspection is complete.

This now uses a robot camera rig inside the Dojo scene rather than only returning a generic world summary.

The current prototype camera path works like this:

- the bridge queues a pending snapshot request
- the Dojo polls for that request
- the selected robot camera captures a shot
- the Dojo reports the image and metadata back to the bridge
- MCP-style callers can then inspect the latest reported snapshot state

This means the contract is already aligned with tool-driven on-demand perception, even though the current implementation is still local and prototype-oriented.

The bridge-exposed MCP-oriented tool surface is:

- `vision_status`
- `vision_start`
- `vision_snapshot`
- `vision_stop`

The current design goal remains that vision is requested when needed and released when it is not, rather than streaming continuously.

### Robot Cameras

The prototype now includes these onboard robot cameras in the Dojo scene:

- `front_cam`
- `left_cam`
- `right_cam`
- `rear_cam`

Each camera can be selected for on-demand inspection snapshots.

### Generic Robot Runtime

The repository now includes an internal robot runtime layer that loads:

- a robot profile from `robot_profiles/`
- a supported transport adapter from `valley/app/robot_runtime/`
- normalized capabilities for motion, status, and observation

The current runtime path supports:

- a real Walker-oriented ROS 2 profile that currently resolves to the rosbridge scaffold
- a `walker_tienkung_sim` profile that runs entirely in process
- deterministic motion, status, power, IMU, joint, and camera behavior for tests

This means the backend can already validate robot-control flows before a physical robot or ROS deployment is available.

## Developer Workflow

### Rebuild The Backend After Changes

When you change backend code in `bridge/`, `valley/`, `stt/`, or `tts/`, rebuild the relevant containers:

```bash
docker compose -f docker/compose.yml up --build -d
```

Or rebuild a subset:

```bash
docker compose -f docker/compose.yml up --build -d valley bridge
```

View logs with:

```bash
docker logs automatavalley-valley-1 --tail 200
docker logs automatavalley-bridge-1 --tail 200
docker logs automatavalley-stt-1 --tail 200
docker logs automatavalley-tts-1 --tail 200
```

Run the quick health check with:

```powershell
powershell -ExecutionPolicy Bypass -File .\check_stack.ps1
```

Stop the stack with:

```bash
docker compose -f docker/compose.yml down
```

## Running Tests

Run the current Python tests from the repository root:

```bash
python -m unittest tests.test_navigation tests.test_interpreter tests.test_vision_tools tests.test_robot_runtime
```

Validate the Godot project headlessly:

```powershell
powershell -ExecutionPolicy Bypass -File .\run_dojo.ps1 -Headless
```

## API Endpoints

Current local endpoints:

- Valley health: `GET http://localhost:8001/health`
- Valley waypoints: `GET http://localhost:8001/waypoints`
- Valley commands: `POST http://localhost:8001/commands`
- Bridge health: `GET http://localhost:8002/health`
- Bridge bootstrap: `GET http://localhost:8002/api/bootstrap`
- Bridge Dojo commands: `POST http://localhost:8002/api/dojo/commands`
- Bridge vision status: `GET http://localhost:8002/api/dojo/vision/status`
- Bridge vision start: `POST http://localhost:8002/api/dojo/vision/start`
- Bridge vision snapshot: `POST http://localhost:8002/api/dojo/vision/snapshot`
- Bridge vision report: `POST http://localhost:8002/api/dojo/vision/report`
- Bridge vision stop: `POST http://localhost:8002/api/dojo/vision/stop`
- MCP tool catalog: `GET http://localhost:8002/api/mcp/tools`
- MCP tool invoke: `POST http://localhost:8002/api/mcp/tools/invoke`
- STT health: `GET http://localhost:8003/health`
- STT text transcription: `POST http://localhost:8003/transcribe/text`
- STT audio transcription: `POST http://localhost:8003/transcribe`
- TTS health: `GET http://localhost:8004/health`
- TTS synthesis: `POST http://localhost:8004/synthesize`

## Example Command Request

The Dojo currently posts a payload shaped like this:

```json
{
  "command_id": "123456789",
  "timestamp": "2026-05-25T12:00:00Z",
  "session_id": "123456790",
  "robot_id": "dojo-bot-01",
  "source": "dojo_voice",
  "transcript": "move north",
  "command_text": "move north",
  "command_type": "navigation",
  "metadata": {
    "stt_engine": "parakeet",
    "confidence": 1.0
  }
}
```

## Known Notes

- The current Docker configuration expects local Ollama on the host machine.
- The first real Parakeet startup can take time because the model and dependencies need to initialize.
- The Dojo currently uses Godot native text-to-speech rather than the Docker TTS service for in-app playback.
- Push-to-talk and the transcription handoff are functional but still being refined.
- The robot runtime currently exposes an internal simulation path and a rosbridge scaffold; it does not yet drive a live Walker robot.

## Next Steps

Likely next improvements for the project are:

- stabilize push-to-talk further
- improve the Gemma interpretation prompt for navigation
- add richer robot animation and room feedback
- add better reconnect and operator diagnostics
- continue shaping the project toward MCP-native robot integration
