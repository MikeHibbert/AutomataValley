Specification: ROS 2 Walker Tienkung Integration via Zeitgeist in CampfireValley / AutomataValley
1. Project Overview
Objective:
Integrate the UBTECH Walker Tienkung humanoid robot (ROS 2-based) into the AutomataValley Dojo as a first-class embodied agent. All robot communication and high-level reasoning will route through the Zeitgeist Runtime layer of CampfireValley. This enables natural language commands from the Godot Dojo to control the physical robot intelligently, with feedback loops for visualization, memory, and multi-agent collaboration.
Scope:

Real-time command execution (navigation, poses, gestures, speech, vision).
Bi-directional data flow (commands → robot, robot state → Dojo/Z eitgeist).
Support for multiple ROS 2 robots in the future.
Maintain clean separation: Dojo for visualization/UI, Valley for orchestration, Zeitgeist for intelligent processing.

Key Benefits:

Zeitgeist handles rich context-aware actions (e.g., combine knowledge retrieval with robot motion).
Hybrid sim/real workflow.
Leverages existing service discovery and round-based architecture.

2. High-Level Architecture
textGodot Dojo (AutomataValley)
    ↓ (HTTP/WebSocket commands + voice)
Valley Interpreter / Command Router
    ↓
Zeitgeist Runtime (extended)
    ↓ (dynamic action routing)
ROS 2 Bridge Service (new microservice)
    ↓ (rclpy / rosbridge)
Walker Tienkung Robot
    ↑ (joint states, odometry, camera, IMU, speech feedback)
Back to Zeitgeist → Valley → Dojo (real-time sync)

Networking: All services on the same local network. Use ROS_DOMAIN_ID for ROS 2 communication. The ROS Bridge can run on an edge PC or the robot’s x86 controller.

3. Components to Develop / Modify
3.1 Zeitgeist Runtime (campfirevalley/zeitgeist_runtime.py)
Functionality:

Register and manage multiple robots.
Execute high-level robot actions with context (memory, web knowledge, LLM reasoning).
Handle command translation and feedback processing.

Requirements:

Add active_robots dict to track registered robots.
New method: register_robot(robot_config: dict).
Extend execute_action(action: dict, context: dict) to detect type == "robot_command".
Support async communication with ROS Bridge.
Log all robot interactions for snapshots/auditing.

3.2 ROS 2 Bridge Service (New: ros_bridge/ directory)
Functionality:

Acts as the translation layer between HTTP/gRPC/WebSocket and native ROS 2.
Exposes clean REST-like API that Zeitgeist can call.
Supports both high-level actions and low-level ROS topics/services.

Tech Stack:

Docker container based on ROS 2 Humble/Iron + Python.
FastAPI (preferred) + rclpy.
Optional: rosbridge_suite for WebSocket fallback.

Core Endpoints (examples):

POST /robot/{robot_id}/command — High-level commands.
GET /robot/{robot_id}/status — Pose, battery, mode.
GET /robot/{robot_id}/joints — Joint states.
POST /robot/{robot_id}/vision/describe — Trigger vision + description.

Supported Command Types:

navigate (target: "table", "center", direction: "north", etc.)
perform_pose / gesture (e.g., "teaching_pose", "karate_block")
speak (text → robot TTS)
velocity (cmd_vel fallback)
get_observation (camera + description)

3.3 Service Catalog & Discovery

Extend the existing service catalog to include embodied agents.
Add dynamic registration of Walker robots via Zeitgeist.

3.4 AutomataValley Dojo (Godot 4)
Enhancements:

Real-time synchronization of robot pose/joints to the 3D avatar.
Display camera feed from robot.
Visual feedback for executed commands.
Toggle between simulation mode and real robot mode.

3.5 Valley Layer (Minimal Changes)

Route robot-specific commands to Zeitgeist instead of direct Bridge.

4. Detailed API & Data Formats
Example Robot Command (sent to Zeitgeist → Bridge):
JSON{
  "type": "robot_command",
  "robot_id": "walker-01",
  "action": "navigate",
  "target": "table",
  "mode": "safe",
  "context": { "lesson_topic": "karate" }
}
Example Feedback from Bridge:
JSON{
  "status": "success",
  "current_pose": {"x": 1.2, "y": 0.5, "yaw": 45},
  "joints": {...},
  "observation": "I see a student raising their hand."
}
5. Implementation Priorities (Phased)
Phase 1 (Core):

ROS Bridge skeleton with navigation and status.
Zeitgeist registration + basic command routing.
Basic Dojo feedback.

Phase 2:

Gestures, speech, vision.
Full state synchronization.

Phase 3:

Multi-robot support, RL policy execution, safety layers.

6. Safety & Best Practices

Always respect robot’s built-in balance and safety modes.
Implement emergency stop command.
Rate limiting on velocity commands.
Extensive simulation testing first (using Walker URDF in Gazebo/Isaac Lab).
Error handling and timeouts in all async calls.

7. Dependencies to Add

rclpy, geometry_msgs, sensor_msgs, etc.
aiohttp (for clients).
ROS 2 base image in Docker.

8. Acceptance Criteria

Voice command in Dojo ("Walker, go to the center and perform a teaching gesture") successfully executes on physical robot.
Robot state (pose, camera) updates live in Godot avatar.
All interactions logged through Zeitgeist.
System works with simulation fallback.