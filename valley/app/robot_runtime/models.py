from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


TransportRole = Literal["primary", "secondary", "fallback"]
ControlPlane = Literal["ros2", "rosbridge_websocket", "http_robot_api", "mcp_gateway"]
InterfaceEntityType = Literal["topic", "service", "action", "virtual"]


class RuntimeConfig(BaseModel):
    control_plane: ControlPlane
    simulation_mode_supported: bool
    shadow_mode_supported: bool = False
    recommended_host_os: str | None = None
    notes: list[str] = Field(default_factory=list)


class TransportConfig(BaseModel):
    name: str
    role: TransportRole
    endpoint_example: str | None = None
    protocol: str | None = None
    notes: str | None = None


class InterfaceConfig(BaseModel):
    normalized_capability: str
    entity_type: InterfaceEntityType
    entity_name: str | None = None
    message_type: str | None = None
    rate_hz: float | None = None
    required_mode: str | None = None
    writeable: bool | None = None
    notes: str | None = None


class SafetyConfig(BaseModel):
    requires_estop_monitor: bool = False
    requires_mode_gate: bool = False
    default_motion_mode: str | None = None
    forbidden_interfaces: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class TestingConfig(BaseModel):
    smoke_suite: list[str] = Field(default_factory=list)
    simulation_profile: str | None = None


class RobotProfile(BaseModel):
    profile_id: str
    display_name: str
    vendor: str
    model: str
    software_version: str | None = None
    runtime: RuntimeConfig
    capabilities: dict[str, bool] = Field(default_factory=dict)
    transports: list[TransportConfig] = Field(default_factory=list)
    interfaces: dict[str, InterfaceConfig] = Field(default_factory=dict)
    safety: SafetyConfig = Field(default_factory=SafetyConfig)
    testing: TestingConfig = Field(default_factory=TestingConfig)

    def supports_capability(self, capability: str) -> bool:
        return self.capabilities.get(capability, False)

    def get_interface(self, interface_name: str) -> InterfaceConfig:
        return self.interfaces[interface_name]

    def get_interfaces_for_capability(self, capability: str) -> dict[str, InterfaceConfig]:
        return {
            name: interface
            for name, interface in self.interfaces.items()
            if interface.normalized_capability == capability
        }

    def get_transport(self, transport_name: str) -> TransportConfig | None:
        for transport in self.transports:
            if transport.name == transport_name:
                return transport
        return None

    def choose_transport(self, supported_transport_names: set[str]) -> TransportConfig:
        ranked_transports = sorted(
            self.transports,
            key=lambda transport: {"primary": 0, "secondary": 1, "fallback": 2}.get(transport.role, 99),
        )
        for transport in ranked_transports:
            if transport.name in supported_transport_names:
                return transport
        raise ValueError(
            "No supported transport is available for profile %s. Supported transports: %s"
            % (self.profile_id, ", ".join(sorted(supported_transport_names)))
        )


class ResolvedCommand(BaseModel):
    command_name: str
    capability: str
    interfaces: dict[str, InterfaceConfig] = Field(default_factory=dict)
    payload: dict[str, Any] = Field(default_factory=dict)


class RuntimeStatus(BaseModel):
    ok: bool = True
    profile_id: str
    adapter: str
    transport: str
    connected: bool
    mode: str
    details: dict[str, Any] = Field(default_factory=dict)
