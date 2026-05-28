from __future__ import annotations

from typing import Any

from ..models import RuntimeStatus
from .base import RobotAdapter


class RosbridgeAdapter(RobotAdapter):
    transport_name = "rosbridge_websocket"

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
            mode="scaffold",
            details={
                "endpoint_example": self.transport.endpoint_example,
                "protocol": self.transport.protocol,
                "supported_capabilities": sorted(
                    capability for capability, enabled in self.profile.capabilities.items() if enabled
                ),
            },
        )

    def execute_command(self, command_name: str, capability: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        resolved = self.resolve_command(command_name, capability, payload)
        return {
            "ok": True,
            "adapter": self.adapter_name,
            "transport": self.transport.name,
            "connected": self.connected,
            "mode": "scaffold",
            "command": resolved.model_dump(mode="json"),
            "message": "Rosbridge adapter scaffold resolved the command but does not publish to ROS yet.",
        }

    def capture_observation(
        self,
        command_name: str,
        capability: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        resolved = self.resolve_command(command_name, capability, payload)
        return {
            "ok": True,
            "adapter": self.adapter_name,
            "transport": self.transport.name,
            "connected": self.connected,
            "mode": "scaffold",
            "observation_request": resolved.model_dump(mode="json"),
            "message": "Rosbridge adapter scaffold resolved the observation request but does not subscribe to ROS yet.",
        }
