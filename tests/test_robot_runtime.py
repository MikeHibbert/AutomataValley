import unittest

from valley.app.robot_runtime import (
    build_smoke_test_plan,
    create_adapter_for_profile_id,
    load_all_robot_profiles,
    load_robot_profile_by_id,
)


class RobotRuntimeTests(unittest.TestCase):
    def test_load_all_profiles_includes_walker(self) -> None:
        profiles = load_all_robot_profiles()
        self.assertIn("walker_tienkung_v2_0_5_1", profiles)
        self.assertIn("walker_tienkung_sim", profiles)

    def test_walker_profile_exposes_expected_interfaces(self) -> None:
        profile = load_robot_profile_by_id("walker_tienkung_v2_0_5_1")
        self.assertTrue(profile.supports_capability("robot.motion.set_velocity"))
        self.assertEqual(profile.get_interface("cmd_vel").entity_name, "/hric/robot/cmd_vel")
        self.assertEqual(profile.get_interface("color_image").message_type, "sensor_msgs/msg/Image")

    def test_runtime_selects_supported_secondary_transport(self) -> None:
        adapter = create_adapter_for_profile_id("walker_tienkung_v2_0_5_1")
        self.assertEqual(adapter.transport.name, "rosbridge_websocket")
        self.assertEqual(adapter.adapter_name, "RosbridgeAdapter")

    def test_runtime_resolves_motion_command_to_rosbridge_scaffold(self) -> None:
        adapter = create_adapter_for_profile_id("walker_tienkung_v2_0_5_1")
        result = adapter.execute_command(
            command_name="move_base",
            capability="robot.motion.set_velocity",
            payload={"linear_x": 0.1, "angular_z": 0.0},
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["command"]["interfaces"]["cmd_vel"]["entity_name"], "/hric/robot/cmd_vel")
        self.assertEqual(result["command"]["payload"]["linear_x"], 0.1)

    def test_runtime_selects_simulated_adapter_for_sim_profile(self) -> None:
        adapter = create_adapter_for_profile_id("walker_tienkung_sim")
        self.assertEqual(adapter.transport.name, "simulated")
        self.assertEqual(adapter.adapter_name, "SimulatedRobotAdapter")

    def test_simulated_motion_command_updates_pose_and_mode(self) -> None:
        adapter = create_adapter_for_profile_id("walker_tienkung_sim")
        adapter.connect()
        adapter.execute_command(
            command_name="set_motion_mode",
            capability="robot.motion.set_mode",
            payload={"mode": "walk"},
        )
        result = adapter.execute_command(
            command_name="move_base",
            capability="robot.motion.set_velocity",
            payload={"linear_x": 0.2, "angular_z": 0.1},
        )

        self.assertTrue(result["ok"])
        self.assertEqual(result["mode"], "walk")
        self.assertEqual(result["state"]["pose"]["x"], 0.2)
        self.assertEqual(result["state"]["pose"]["theta"], 0.1)
        self.assertEqual(result["state"]["velocity"]["linear_x"], 0.2)

    def test_simulated_status_observation_returns_power_and_motion_state(self) -> None:
        adapter = create_adapter_for_profile_id("walker_tienkung_sim")
        adapter.connect()
        adapter.execute_command(
            command_name="move_base",
            capability="robot.motion.set_velocity",
            payload={"linear_x": 0.15, "linear_y": -0.05, "angular_z": 0.0},
        )

        status = adapter.get_status()
        power = adapter.capture_observation(
            command_name="get_power",
            capability="robot.power.get",
        )

        self.assertTrue(status.ok)
        self.assertEqual(status.mode, "walk")
        self.assertEqual(status.details["pose"]["x"], 0.15)
        self.assertEqual(power["observation"]["percent"], 87.0)
        self.assertFalse(power["observation"]["charging"])

    def test_simulated_vision_capture_returns_frame_metadata(self) -> None:
        adapter = create_adapter_for_profile_id("walker_tienkung_sim")
        adapter.connect()
        observation = adapter.capture_observation(
            command_name="capture_color",
            capability="robot.vision.capture_color",
            payload={"camera": "front_camera"},
        )

        self.assertTrue(observation["ok"])
        self.assertEqual(observation["observation"]["camera"], "front_camera")
        self.assertEqual(observation["observation"]["frame_id"], "sim-frame-001")
        self.assertEqual(observation["observation"]["width"], 640)
        self.assertEqual(observation["observation"]["encoding"], "simulated")

    def test_smoke_plan_uses_profile_testing_defaults(self) -> None:
        profile = load_robot_profile_by_id("walker_tienkung_v2_0_5_1")
        smoke_plan = build_smoke_test_plan(profile)
        self.assertEqual(smoke_plan[0]["interface_name"], "battery_status")
        self.assertEqual(smoke_plan[-1]["interface_name"], "color_image")
        self.assertFalse(smoke_plan[0]["writeable"])

    def test_real_profile_points_to_simulation_profile(self) -> None:
        profile = load_robot_profile_by_id("walker_tienkung_v2_0_5_1")
        self.assertEqual(profile.testing.simulation_profile, "walker_tienkung_sim")


if __name__ == "__main__":
    unittest.main()
