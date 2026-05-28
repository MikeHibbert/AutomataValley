from __future__ import annotations

from typing import Type

from .adapters import RobotAdapter, RosbridgeAdapter, SimulatedRobotAdapter
from .models import RobotProfile
from .profiles import load_robot_profile_by_id


ADAPTER_REGISTRY: dict[str, Type[RobotAdapter]] = {
    RosbridgeAdapter.transport_name: RosbridgeAdapter,
    SimulatedRobotAdapter.transport_name: SimulatedRobotAdapter,
}


def get_supported_transport_names() -> set[str]:
    return set(ADAPTER_REGISTRY)


def create_adapter_for_profile(
    profile: RobotProfile,
    preferred_transports: list[str] | None = None,
) -> RobotAdapter:
    supported_transports = get_supported_transport_names()
    if preferred_transports:
        for transport_name in preferred_transports:
            transport = profile.get_transport(transport_name)
            if transport is not None and transport_name in supported_transports:
                return ADAPTER_REGISTRY[transport_name](profile=profile, transport=transport)

    transport = profile.choose_transport(supported_transports)
    return ADAPTER_REGISTRY[transport.name](profile=profile, transport=transport)


def create_adapter_for_profile_id(
    profile_id: str,
    preferred_transports: list[str] | None = None,
) -> RobotAdapter:
    profile = load_robot_profile_by_id(profile_id)
    return create_adapter_for_profile(profile, preferred_transports=preferred_transports)
