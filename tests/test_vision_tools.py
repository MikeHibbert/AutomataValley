import unittest

from bridge.app.vision_tools import (
    build_mcp_tool_catalog,
    capture_snapshot,
    invoke_tool,
    report_snapshot,
    request_snapshot,
    start_vision_session,
    stop_vision_session,
)
from valley.app.world_model import build_world_state


class VisionToolTests(unittest.TestCase):
    def setUp(self) -> None:
        stop_vision_session()

    def tearDown(self) -> None:
        stop_vision_session()

    def test_tool_catalog_contains_expected_tools(self) -> None:
        tool_names = [tool["name"] for tool in build_mcp_tool_catalog()]
        self.assertEqual(
            tool_names,
            ["vision_status", "vision_start", "vision_snapshot", "vision_stop"],
        )

    def test_snapshot_requires_active_session(self) -> None:
        result = request_snapshot(note="check door")
        self.assertFalse(result["ok"])
        self.assertIn("not active", result["message"])

    def test_start_request_report_stop_flow(self) -> None:
        started = start_vision_session(requested_by="test_suite", reason="unit test")
        self.assertTrue(started["ok"])
        self.assertTrue(started["status"]["active"])

        requested = request_snapshot(note="check mug", camera_id="left_cam")
        self.assertTrue(requested["ok"])
        self.assertEqual(requested["requested_snapshot"]["camera_id"], "left_cam")

        reported = report_snapshot(
            session_id=started["status"]["session"]["session_id"],
            job_id=requested["requested_snapshot"]["job_id"],
            camera_id="left_cam",
            image_base64="ZmFrZS1wbmc=",
            media_type="image/png",
            width=512,
            height=512,
            frame_summary="left camera sees mug",
            observations=[{"label": "Red Mug"}],
        )
        self.assertTrue(reported["ok"])
        self.assertEqual(reported["snapshot"]["camera_id"], "left_cam")
        self.assertEqual(reported["snapshot"]["transport"], "image_base64")

        stopped = stop_vision_session(started["status"]["session"]["session_id"])
        self.assertTrue(stopped["ok"])
        self.assertFalse(stopped["status"]["active"])

    def test_invoke_tool_dispatches_snapshot(self) -> None:
        invoke_tool("vision_start", {"requested_by": "test_suite"}, world=None)
        result = invoke_tool("vision_snapshot", {"note": "check tool flow", "camera_id": "rear_cam"}, world=build_world_state())
        self.assertTrue(result["ok"])
        self.assertEqual(result["tool_name"], "vision_snapshot")
        self.assertEqual(result["result"]["requested_snapshot"]["camera_id"], "rear_cam")

    def test_legacy_capture_helper_still_generates_summary_snapshot(self) -> None:
        start_vision_session(requested_by="test_suite", reason="legacy path")
        result = capture_snapshot(world=build_world_state(), note="summary path", camera_id="front_cam")
        self.assertTrue(result["ok"])
        self.assertEqual(result["snapshot"]["media_type"], "application/json")


if __name__ == "__main__":
    unittest.main()
