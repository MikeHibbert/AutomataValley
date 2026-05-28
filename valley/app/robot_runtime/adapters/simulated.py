from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ..models import RuntimeStatus
from .base import RobotAdapter


class SimulatedRobotAdapter(RobotAdapter):
    transport_name = "simulated"

    def __init__(self, profile, transport) -> None:
        super().__init__(profile=profile, transport=transport)
        self.motion_mode = profile.safety.default_motion_mode or "simulation_idle"
        self.pose = {"x": 0.0, "y": 0.0, "theta": 0.0}
        self.velocity = {"linear_x": 0.0, "linear_y": 0.0, "angular_z": 0.0}
        self.velocity_limit = {"linear_x": 0.5, "angular_z": 0.8}
        self.head = {"yaw": 0.0, "pitch": 0.0}
        self.waist = {"yaw": 0.0, "pitch": 0.0, "roll": 0.0, "height": 0.0}
        self.arms = {
            "left": {"x": 0.35, "y": 0.2, "z": 1.0},
            "right": {"x": 0.35, "y": -0.2, "z": 1.0},
        }
        self.battery = {"percent": 87.0, "charging": False, "voltage": 52.1}
        self.estop = {"engaged": False}
        self.imu = {"roll": 0.0, "pitch": 0.0, "yaw": 0.0}
        self.capture_count = 0

    def connect(self) -> RuntimeStatus:
        self.connected = True
        return self.get_status()

    def disconnect(self) -> RuntimeStatus:
        self.connected = False
        return self.get_status()

    def get_status(self) -> RuntimeStatus:
        return RuntimeStatus(
            profile_id=self.profile.profile_id,
            adapter=self.adapter_name,
            transport=self.transport.name,
            connected=self.connected,
            mode=self.motion_mode,
            details=self._runtime_snapshot(),
        )

    def execute_command(self, command_name: str, capability: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        resolved = self.resolve_command(command_name, capability, payload)
        request = payload or {}

        if capability == "robot.motion.set_mode":
            self.motion_mode = str(request.get("mode", self.motion_mode))
        elif capability == "robot.motion.set_velocity":
            self._apply_velocity(request)
        elif capability == "robot.motion.stop":
            self.velocity = {"linear_x": 0.0, "linear_y": 0.0, "angular_z": 0.0}
        elif capability == "robot.head.move":
            self.head["yaw"] = float(request.get("yaw", self.head["yaw"]))
            self.head["pitch"] = float(request.get("pitch", self.head["pitch"]))
        elif capability == "robot.waist.move":
            self.waist["yaw"] = float(request.get("yaw", self.waist["yaw"]))
            self.waist["pitch"] = float(request.get("pitch", self.waist["pitch"]))
            self.waist["roll"] = float(request.get("roll", self.waist["roll"]))
            self.waist["height"] = float(request.get("height", self.waist["height"]))
        elif capability == "robot.arm.move_pose":
            arm_name = str(request.get("arm", "left"))
            if arm_name not in self.arms:
                arm_name = "left"
            self.arms[arm_name] = {
                "x": float(request.get("x", self.arms[arm_name]["x"])),
                "y": float(request.get("y", self.arms[arm_name]["y"])),
                "z": float(request.get("z", self.arms[arm_name]["z"])),
            }

        return {
            "ok": True,
            "adapter": self.adapter_name,
            "transport": self.transport.name,
            "connected": self.connected,
            "mode": self.motion_mode,
            "command": resolved.model_dump(mode="json"),
            "state": self._runtime_snapshot(),
            "message": "Simulated adapter applied the command in-process.",
        }

    def capture_observation(
        self,
        command_name: str,
        capability: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        resolved = self.resolve_command(command_name, capability, payload)
        observation = self._build_observation(capability, payload or {})
        return {
            "ok": True,
            "adapter": self.adapter_name,
            "transport": self.transport.name,
            "connected": self.connected,
            "mode": self.motion_mode,
            "observation_request": resolved.model_dump(mode="json"),
            "observation": observation,
            "message": "Simulated adapter produced a deterministic observation.",
        }

    def _apply_velocity(self, payload: dict[str, Any]) -> None:
        linear_x = self._clamp(float(payload.get("linear_x", 0.0)), -self.velocity_limit["linear_x"], self.velocity_limit["linear_x"])
        linear_y = self._clamp(float(payload.get("linear_y", 0.0)), -self.velocity_limit["linear_x"], self.velocity_limit["linear_x"])
        angular_z = self._clamp(
            float(payload.get("angular_z", 0.0)),
            -self.velocity_limit["angular_z"],
            self.velocity_limit["angular_z"],
        )

        self.velocity = {
            "linear_x": linear_x,
            "linear_y": linear_y,
            "angular_z": angular_z,
        }
        self.pose["x"] = round(self.pose["x"] + linear_x, 3)
        self.pose["y"] = round(self.pose["y"] + linear_y, 3)
        self.pose["theta"] = round(self.pose["theta"] + angular_z, 3)
        self.imu["yaw"] = self.pose["theta"]

        if any(abs(component) > 0.0 for component in self.velocity.values()):
            self.motion_mode = "walk"

    def _build_observation(self, capability: str, payload: dict[str, Any]) -> dict[str, Any]:
        if capability == "robot.status.get":
            return {
                "pose": dict(self.pose),
                "velocity": dict(self.velocity),
                "motion_mode": self.motion_mode,
                "estop": dict(self.estop),
            }
        if capability == "robot.power.get":
            return dict(self.battery)
        if capability == "robot.estop.get":
            return dict(self.estop)
        if capability == "robot.imu.get":
            return dict(self.imu)
        if capability == "robot.joints.get":
            return {
                "head": dict(self.head),
                "waist": dict(self.waist),
                "arms": {name: dict(values) for name, values in self.arms.items()},
            }
        if capability in {"robot.vision.capture_color", "robot.vision.capture_depth"}:
            self.capture_count += 1
            camera_name = str(payload.get("camera", "front_camera"))
            return {
                "frame_id": "sim-frame-%03d" % self.capture_count,
                "camera": camera_name,
                "capability": capability,
                "captured_at": self._utc_now(),
                "width": 640,
                "height": 480,
                "mime_type": "image/png" if capability == "robot.vision.capture_color" else "application/octet-stream",
                "encoding": "simulated",
                "content": "simulated-%s-%s" % (camera_name, capability.rsplit(".", 1)[-1]),
            }
        return self._runtime_snapshot()

    def _runtime_snapshot(self) -> dict[str, Any]:
        return {
            "motion_mode": self.motion_mode,
            "pose": dict(self.pose),
            "velocity": dict(self.velocity),
            "velocity_limit": dict(self.velocity_limit),
            "battery": dict(self.battery),
            "estop": dict(self.estop),
            "imu": dict(self.imu),
            "head": dict(self.head),
            "waist": dict(self.waist),
            "arms": {name: dict(values) for name, values in self.arms.items()},
            "capture_count": self.capture_count,
            "supported_capabilities": sorted(
                capability for capability, enabled in self.profile.capabilities.items() if enabled
            ),
        }

    @staticmethod
    def _clamp(value: float, lower: float, upper: float) -> float:
        return max(lower, min(upper, value))

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
