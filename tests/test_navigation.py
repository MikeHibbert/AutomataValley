import unittest

from valley.app.navigation import CommandParseError, parse_navigation_command


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


if __name__ == "__main__":
    unittest.main()
