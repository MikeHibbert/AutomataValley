from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ..models import InterfaceConfig, ResolvedCommand, RobotProfile, RuntimeStatus, TransportConfig


class RobotAdapterError(RuntimeError):
    pass


class RobotAdapter(ABC):
    transport_name = "unknown"

    def __init__(self, profile: RobotProfile, transport: TransportConfig) -> None:
        self.profile = profile
        self.transport = transport
        self.connected = False

    @property
    def adapter_name(self) -> str:
        return self.__class__.__name__

    def resolve_interfaces(self, capability: str) -> dict[str, InterfaceConfig]:
        if not self.profile.supports_capability(capability):
            raise RobotAdapterError(
                "Profile %s does not advertise capability %s" % (self.profile.profile_id, capability)
            )
        interfaces = self.profile.get_interfaces_for_capability(capability)
        if not interfaces:
            raise RobotAdapterError(
                "Capability %s is enabled for profile %s but has no mapped interfaces"
                % (capability, self.profile.profile_id)
            )
        return interfaces

    def resolve_command(self, command_name: str, capability: str, payload: dict[str, Any] | None = None) -> ResolvedCommand:
        return ResolvedCommand(
            command_name=command_name,
            capability=capability,
            interfaces=self.resolve_interfaces(capability),
            payload=payload or {},
        )

    @abstractmethod
    def connect(self) -> RuntimeStatus:
        raise NotImplementedError

    @abstractmethod
    def disconnect(self) -> RuntimeStatus:
        raise NotImplementedError

    @abstractmethod
    def get_status(self) -> RuntimeStatus:
        raise NotImplementedError

    @abstractmethod
    def execute_command(self, command_name: str, capability: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def capture_observation(
        self,
        command_name: str,
        capability: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        raise NotImplementedError
