from __future__ import annotations

from .models import RobotProfile


def build_smoke_test_plan(profile: RobotProfile) -> list[dict[str, object]]:
    plan: list[dict[str, object]] = []
    for interface_name in profile.testing.smoke_suite:
        interface = profile.get_interface(interface_name)
        plan.append(
            {
                "interface_name": interface_name,
                "capability": interface.normalized_capability,
                "entity_type": interface.entity_type,
                "entity_name": interface.entity_name,
                "message_type": interface.message_type,
                "writeable": interface.writeable,
                "required_mode": interface.required_mode,
            }
        )
    return plan
