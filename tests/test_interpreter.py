import unittest

from valley.app.interpreter import interpret_command


class InterpreterTests(unittest.TestCase):
    def test_exact_command_executes(self) -> None:
        result = interpret_command("move north")
        self.assertEqual(result["interpretation"]["disposition"], "execute")
        self.assertEqual(result["intent"]["intent"], "move_direction")

    def test_forward_executes_as_north(self) -> None:
        result = interpret_command("move forward")
        self.assertEqual(result["interpretation"]["disposition"], "execute")
        self.assertEqual(result["interpretation"]["canonical_command"], "move north")
        self.assertEqual(result["intent"]["direction"], "north")

    def test_backwards_prompts_for_clarification(self) -> None:
        result = interpret_command("move backwards")
        self.assertEqual(result["interpretation"]["disposition"], "execute")
        self.assertEqual(result["interpretation"]["canonical_command"], "move south")
        self.assertEqual(result["intent"]["direction"], "south")

    def test_step_right_executes_as_east(self) -> None:
        result = interpret_command("take a step to the right")
        self.assertEqual(result["interpretation"]["disposition"], "execute")
        self.assertEqual(result["interpretation"]["canonical_command"], "move east")
        self.assertEqual(result["intent"]["direction"], "east")

    def test_go_over_to_table_executes(self) -> None:
        result = interpret_command("go over to the table")
        self.assertEqual(result["interpretation"]["disposition"], "execute")
        self.assertEqual(result["interpretation"]["canonical_command"], "go to table")
        self.assertEqual(result["intent"]["target"], "table")

    def test_back_up_executes_as_south(self) -> None:
        result = interpret_command("back up")
        self.assertEqual(result["interpretation"]["disposition"], "execute")
        self.assertEqual(result["interpretation"]["canonical_command"], "move south")
        self.assertEqual(result["intent"]["direction"], "south")

    def test_waypoint_phrase_executes(self) -> None:
        result = interpret_command("head to table")
        self.assertEqual(result["interpretation"]["disposition"], "execute")
        self.assertEqual(result["intent"]["target"], "table")

    def test_object_navigation_executes(self) -> None:
        result = interpret_command("go to the mug")
        self.assertEqual(result["interpretation"]["disposition"], "execute")
        self.assertEqual(result["intent"]["intent"], "navigate_to_object")
        self.assertEqual(result["intent"]["target_object"], "red_mug")

    def test_scene_inspection_executes(self) -> None:
        result = interpret_command("what can you see")
        self.assertEqual(result["interpretation"]["disposition"], "execute")
        self.assertEqual(result["intent"]["intent"], "inspect_scene")

    def test_pick_up_object_executes(self) -> None:
        result = interpret_command("pick up the mug")
        self.assertEqual(result["interpretation"]["disposition"], "execute")
        self.assertEqual(result["intent"]["intent"], "pick_up_object")
        self.assertEqual(result["intent"]["target_object"], "red_mug")

    def test_place_object_executes(self) -> None:
        result = interpret_command("place the mug on the table")
        self.assertEqual(result["interpretation"]["disposition"], "execute")
        self.assertEqual(result["intent"]["intent"], "place_object")
        self.assertEqual(result["intent"]["target_surface"], "table")

    def test_two_close_matches_do_not_crash(self) -> None:
        result = interpret_command("move nort")
        self.assertEqual(result["interpretation"]["disposition"], "clarify")
        self.assertTrue(result["interpretation"]["message"].startswith("I heard something close"))

    def test_unsupported_capability_rejects(self) -> None:
        result = interpret_command("dance")
        self.assertEqual(result["interpretation"]["disposition"], "reject")
        self.assertIn("move north", result["interpretation"]["suggestions"])


if __name__ == "__main__":
    unittest.main()
