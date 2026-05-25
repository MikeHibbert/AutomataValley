import unittest

from valley.app.interpreter import interpret_command


class InterpreterTests(unittest.TestCase):
    def test_exact_command_executes(self) -> None:
        result = interpret_command("move north")
        self.assertEqual(result["interpretation"]["disposition"], "execute")
        self.assertEqual(result["intent"]["intent"], "move_direction")

    def test_forward_prompts_for_clarification(self) -> None:
        result = interpret_command("move forward")
        self.assertEqual(result["interpretation"]["disposition"], "clarify")
        self.assertIn("move north", result["interpretation"]["suggestions"])

    def test_backwards_prompts_for_clarification(self) -> None:
        result = interpret_command("move backwards")
        self.assertEqual(result["interpretation"]["disposition"], "clarify")
        self.assertIn("move south", result["interpretation"]["suggestions"])

    def test_waypoint_phrase_executes(self) -> None:
        result = interpret_command("head to table")
        self.assertEqual(result["interpretation"]["disposition"], "execute")
        self.assertEqual(result["intent"]["target"], "table")

    def test_two_close_matches_do_not_crash(self) -> None:
        result = interpret_command("move nort")
        self.assertEqual(result["interpretation"]["disposition"], "clarify")
        self.assertTrue(result["interpretation"]["message"].startswith("Did you mean"))

    def test_unsupported_capability_rejects(self) -> None:
        result = interpret_command("pick up the mug")
        self.assertEqual(result["interpretation"]["disposition"], "reject")
        self.assertIn("move north", result["interpretation"]["suggestions"])


if __name__ == "__main__":
    unittest.main()
