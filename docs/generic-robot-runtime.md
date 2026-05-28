# Generic Robot Runtime

## Purpose

This document defines the first generic robot runtime contract for `AutomataValley`.

The goal is to keep the core package robot-agnostic:

- `Dojo` stays focused on operator UX and visualization
- `Valley` stays focused on orchestration and interpretation
- `Zeitgeist` stays focused on intelligent tool use and context-aware action routing
- robot-specific details live in configuration profiles and transport adapters

This is explicitly designed to reduce per-robot code changes in the core package.

## Design Goal

`AutomataValley` should not need a custom code path for every robot.

Instead, it should load:

- a generic adapter interface
- one robot profile
- one transport choice
- one capability map

The first target profile is `UBTech Walker Tienkung`, using the published ROS 2 interface families as the initial canonical reference.

## Runtime Layers

### 1. Zeitgeist Tool Layer

`Zeitgeist` sees only normalized tool capabilities such as:

- `robot.status.get`
- `robot.power.get`
- `robot.imu.get`
- `robot.vision.capture_color`
- `robot.vision.capture_depth`
- `robot.motion.set_mode`
- `robot.motion.set_velocity`
- `robot.motion.stop`
- `robot.posture.set_base`
- `robot.head.move`
- `robot.waist.move`
- `robot.arm.move_pose`
- `robot.hand.set_open_ratio`

### 2. Generic Adapter Layer

Each adapter implements the same internal interface:

- `connect(profile)`
- `get_status()`
- `get_capabilities()`
- `execute_command(command_payload)`
- `capture_observation(observation_payload)`
- `disconnect()`

The first transport targets should be:

- `rosbridge_websocket`
- `http_robot_api`
- `mcp_robot_gateway`
- `native_ros2` as an optional advanced transport

### 3. Robot Profile Layer

A profile provides:

- robot identity
- transport selection
- capabilities
- topic/service/action mappings
- safety rules
- startup assumptions
- test defaults

## Ideal Testing Strategy

The runtime should support three progressive modes:

1. `simulation`
2. `shadow`
3. `active`

### Simulation

No physical robot required.

The same normalized commands are answered by a mock backend or simulator.

This is now implemented as an in-process simulation transport with a `walker_tienkung_sim` profile.

### Shadow

Observe real robot telemetry and sensors, but do not send motion commands.

### Active

Allow controlled actuation with explicit safety gating.

## Walker Tienkung Guidance

The published UBTech docs indicate these important constraints:

- the SDK is ROS 2-based
- Ubuntu 22.04 is the recommended robot-side environment
- startup is managed through `proc_manager`
- locomotion, body, sensors, and perception are split across service families
- some direct joint control paths are only valid when the locomotion controller is not owning those joints

Useful published references:

- SDK overview: <https://docs.ubtrobot.com/walker-tienkung/en/docs/sdk/7/>
- startup flow: <https://docs.ubtrobot.com/walker-tienkung/en/docs/sdk/8/2/>
- IMU: <https://docs.ubtrobot.com/walker-tienkung/en/docs/sdk/8/3/>
- head joints: <https://docs.ubtrobot.com/walker-tienkung/en/docs/sdk/8/5/>
- waist joint: <https://docs.ubtrobot.com/walker-tienkung/en/docs/sdk/8/6/>
- arm joints: <https://docs.ubtrobot.com/walker-tienkung/en/docs/sdk/8/7/>
- leg joints: <https://docs.ubtrobot.com/walker-tienkung/en/docs/sdk/8/8/>
- depth camera: <https://docs.ubtrobot.com/walker-tienkung/en/docs/sdk/8/10/>
- hand joints: <https://docs.ubtrobot.com/walker-tienkung/en/docs/sdk/8/11/>
- battery and power: <https://docs.ubtrobot.com/walker-tienkung/en/docs/sdk/8/13/>
- LiDAR: <https://docs.ubtrobot.com/walker-tienkung/en/docs/sdk/8/17/>
- RL motion control: <https://docs.ubtrobot.com/walker-tienkung/en/docs/sdk/8/18/>

## Normalized Capability Model

### Core State

- `status`
- `battery`
- `estop`
- `imu`
- `joint_state`

### Vision

- `capture_color`
- `capture_depth`
- `capture_pointcloud`

### Motion

- `set_motion_mode`
- `set_velocity`
- `stop_motion`
- `set_velocity_limit`
- `set_base_posture`

### Upper Body

- `move_head`
- `move_waist`
- `move_arm_joint_position`
- `move_arm_hybrid_control`

### Hands

- `set_hand_open_ratio`
- `set_hand_speed`
- `set_hand_force`

## Walker-Specific Recommendations

### Preferred First-Class Interfaces

Use these first because they are the cleanest high-value surfaces for initial integration:

- `/power/battery/status`
- `/power/board/key_status`
- `/imu`
- `/hric/motion/set_motion_mode`
- `/hric/robot/cmd_vel`
- `/hric/motion/status`
- `/camera/color/image_raw`
- `/camera/depth/image_raw`
- `/camera/depth/points`
- `/head/status`
- `/head/cmd_pos`
- `/waist/status`
- `/waist/cmd_pos`
- `/arm/status`
- `/arm/cmd_pos`

### Defer Until Later

Keep these out of the first active-control milestone:

- direct leg joint control
- zeroing operations
- force-rich hand control
- RL posture tuning at 400 Hz
- arbitrary raw topic publication

## Recommended First Milestone

The first real robot profile should support:

- health and availability checks
- battery and E-stop state
- IMU state
- color and depth capture
- motion mode switching
- low-speed `cmd_vel`
- head movement
- one safe arm position command

That is enough to validate:

- connectivity
- perception
- safety state handling
- limited actuation
- Dojo synchronization

## Proposed Repo Artifacts

- `robot_profiles/interface_contract.schema.json`
- `robot_profiles/walker_tienkung_v2_0_5_1.json`
- `robot_profiles/walker_tienkung_sim.json`
- `valley/app/robot_runtime/models.py`
- `valley/app/robot_runtime/profiles.py`
- `valley/app/robot_runtime/runtime.py`
- `valley/app/robot_runtime/adapters/rosbridge.py`
- `valley/app/robot_runtime/adapters/simulated.py`
- `tests/test_robot_runtime.py`

## Current Implementation Status

The runtime scaffold now exists in the repository and currently supports:

- profile loading and schema-backed JSON artifacts
- adapter selection by advertised transport
- a rosbridge scaffold for future Walker transport work
- a deterministic simulation adapter for motion, status, and vision
- regression tests for profile loading, adapter selection, motion, telemetry, and camera capture

Future implementation work can then extend:

- a rosbridge adapter
- Valley and Bridge endpoints for direct runtime control
- Dojo-side simulation synchronization
- shadow-mode telemetry against a real Walker deployment

without changing the high-level contract.
