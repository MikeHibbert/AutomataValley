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
- simple navigation commands such as `move north` and `go to table`

## Current Status

This repository is an early working prototype.

The current goal is to let you:

- start the backend stack with Docker
- open the Dojo in Godot
- submit text commands
- use push-to-talk voice input
- see the robot respond to navigation tasks

Core command and interpreter tests are in place, and the backend stack is wired together. Voice input is functional but still being actively hardened, so if you are evaluating the project for the first time, start with typed commands before moving on to push-to-talk.

## Architecture

The current local setup is:

- `dojo`
  - Godot 4 project
  - 3D room and robot view
  - operator UI
  - push-to-talk and transcript flow
- `bridge`
  - FastAPI adapter between Dojo and Valley
  - exposes bootstrap and Dojo-friendly command endpoints
- `valley`
  - FastAPI command service
  - strict parser plus interpretation layer
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

Useful files:

- `docker/compose.yml`
- `run_dojo.ps1`
- `docs/v1-foundation.md`

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

Stop the stack with:

```bash
docker compose -f docker/compose.yml down
```

## Running Tests

Run the current Python tests from the repository root:

```bash
python -m unittest tests.test_navigation tests.test_interpreter
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

## Next Steps

Likely next improvements for the project are:

- stabilize push-to-talk further
- improve the Gemma interpretation prompt for navigation
- add richer robot animation and room feedback
- add better reconnect and operator diagnostics
- continue shaping the project toward MCP-native robot integration
