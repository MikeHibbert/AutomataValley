1. Project Overview
Project Name: AutomataValley
Purpose: A real-time 3D visualization and debugging tool for a robot powered by pyCampfires + pyCampfireValley. It shows the robot’s modular “mind” — multiple specialized Campfires working together — in an engaging, dojo-style training environment.
The Dojo acts as a first-class participant in the MCP (Model Context Protocol) ecosystem, receiving and (optionally) sending events without using WebSockets as the primary channel.
2. Core Architecture

pyCampfireValley runs the robot brain (Executive + Ability Campfires).
Dojo runs as a separate Visualizer Campfire (or dedicated MCP client) that subscribes to visualization-relevant MCP topics.
Communication is handled natively via MCP (Redis-backed pub/sub).
A lightweight Python bridge may be used if direct MCP integration in Godot is complex.

Key Data Flows

Valley → Dojo: Real-time events (Campfire status, Torch passing, Hardware commands, Party Box updates).
Dojo → Valley (optional): Control commands (pause/resume, inject scenario, change task).

3. Godot Frontend Requirements (AutomataValley)
3.1 Visual Style

Futuristic yet warm “Dojo” aesthetic.
Dark background with glowing neon accents (oranges, cyans, purples, golds).
Multiple glowing campfires as visual metaphors for active cognitive modules.
Clean, modern sci-fi UI.

3.2 Main Scene Layout
Viewport (70% of screen)

3D robot avatar (simple humanoid or mobile manipulator — use placeholder model initially).
Multiple glowing Campfire Nodes positioned around or on the robot.
Animated Torch flows (glowing particle beams or energy arcs) when torches are passed between Campfires.
Camera: Orbit + Follow mode with smooth controls.

Right Sidebar — Status Dashboard

List of all active Campfires with:
Name
Current status (Idle / Thinking / Acting)
Confidence meter
Last activity timestamp


Bottom Panel — Live Log / Torch Feed

Scrollable list of recent Torches with:
Source Campfire → Target Campfire
Claim summary
Confidence score (colored)
Timestamp


Top Bar

Current robot task
Overall system status
Playback controls (Play / Pause / Step / Speed)

Left Sidebar (optional)

Available scenarios / test cases
World model summary (Party Box highlights)

3.3 Key Visual Elements

Campfire Nodes — 3D objects that glow brighter when active.
Torch Visualization — Glowing orb + trail moving from source to target Campfire.
Robot Animation — Simple idle, thinking, and action animations (e.g., head turning, arm movement) triggered by hardware commands.
Particle Systems — For energy, data flow, and activity indicators.

3.4 Godot Technical Requirements

Godot 4.3+
Use GDScript
Support real-time JSON event ingestion via MCP bridge
Record session history for replay
Responsive UI that works in windowed and fullscreen

4. Backend / Valley Integration
4.1 New Component: Visualizer Campfire
Create a new Campfire type called VisualizerCampfire with the following Campers:

Event Listener — Subscribes to MCP topics:
campfire.status.*
torch.passed
hardware.command
partybox.update
executive.task

Renderer — Formats events into clean JSON payloads for the Dojo.
Controller — (Optional) Sends commands back to the Executive.

4.2 MCP Event Schema (Required)
All visualization events must follow this structure:
JSON{
  "type": "visualization_event",
  "event": "torch_passed" | "campfire_status" | "hardware_command" | "task_update" | "partybox_update",
  "timestamp": "ISO datetime",
  "source": "Perception",
  "target": "Manipulation",
  "data": {
    "claim": "...",
    "confidence": 0.87,
    "metadata": { ... },
    "hardware_action": "move_arm_to(0.45, 0.3, 0.8)"
  }
}
4.3 Bridge (if needed)
A minimal Python script dojo_bridge.py that:

Subscribes to relevant Redis/MCP channels.
Forwards formatted events to Godot (via TCP socket or HTTP SSE as fallback).

5. Functional Requirements

Real-time updates (≤ 200ms latency target)
Pause / Resume visualization
Session recording + replay
Clickable Campfires to show detailed internal state
Support for multiple simultaneous Campfires
Graceful handling of disconnected Valley

6. Deliverables Expected from AI IDE

Complete Godot project folder with:
Main scene (dojo.tscn)
All necessary scripts
Placeholder robot model + campfire assets

Python-side components:
VisualizerCampfire class
Example integration into a robot valley
dojo_bridge.py (if used)

Sample test scenario (e.g., “Fetch Red Mug” task) that triggers rich visualization.