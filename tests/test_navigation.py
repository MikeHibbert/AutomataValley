import unittest

from valley.app.navigation import CommandParseError, parse_dojo_command, parse_navigation_command


class NavigationParsingTests(unittest.TestCase):
    def test_parses_direction_command(self) -> None:
        result = parse_navigation_command("move north")
        self.assertEqual(result["intent"], "move_direction")
        self.assertEqual(result["direction"], "north")
        self.assertEqual(result["target"], "north_zone")

    def test_parses_waypoint_command_with_article(self) -> None:
        result = parse_navigation_command("go to the table")
        self.assertEqual(result["intent"], "navigate_to")
        self.assertEqual(result["target"], "table")

    def test_parses_stop_command(self) -> None:
        result = parse_navigation_command("stop")
        self.assertEqual(result["intent"], "stop_motion")

    def test_rejects_unsupported_command(self) -> None:
        with self.assertRaises(CommandParseError):
            parse_navigation_command("pick up the mug")

    def test_parses_object_navigation(self) -> None:
        result = parse_dojo_command("go to the mug")
        self.assertEqual(result["intent"], "navigate_to_object")
        self.assertEqual(result["target_object"], "red_mug")

    def test_parses_scene_inspection(self) -> None:
        result = parse_dojo_command("what can you see")
        self.assertEqual(result["intent"], "inspect_scene")

    def test_parses_pick_up_object(self) -> None:
        result = parse_dojo_command("pick up the screwdriver")
        self.assertEqual(result["intent"], "pick_up_object")
        self.assertEqual(result["target_object"], "screwdriver")

    def test_parses_place_object(self) -> None:
        result = parse_dojo_command("place the mug on the table")
        self.assertEqual(result["intent"], "place_object")
        self.assertEqual(result["target_object"], "red_mug")
        self.assertEqual(result["target_surface"], "table")


if __name__ == "__main__":
    unittest.main()
