extends Node
class_name VisionClient

signal vision_status_loaded(payload)
signal vision_action_completed(action, payload)
signal vision_error(message)

@export var bridge_base_url: String = "http://127.0.0.1:8002"

var _active_request: HTTPRequest
var _request_in_progress: bool = false
var _pending_action: String = ""

func configure(base_url: String) -> void:
    if base_url != "":
        bridge_base_url = base_url

func request_status() -> void:
    if _request_in_progress:
        vision_error.emit("Vision request already in progress")
        return
    var http := _create_request(20.0)
    _pending_action = "vision_status"
    _request_in_progress = true
    var err := http.request("%s/api/dojo/vision/status" % bridge_base_url)
    if err != OK:
        _dispose_request()
        vision_error.emit("Failed to load vision status: %s" % err)

func start_session(requested_by: String = "dojo_operator", reason: String = "manual inspection", mode: String = "snapshot", camera_id: String = "front_cam") -> void:
    _post_json(
        "/api/dojo/vision/start",
        {
            "requested_by": requested_by,
            "reason": reason,
            "mode": mode,
            "camera_id": camera_id,
        },
        "vision_start",
        "Failed to start vision session"
    )

func request_snapshot(note: String = "", camera_id: String = "") -> void:
    _post_json(
        "/api/dojo/vision/snapshot",
        {
            "note": note,
            "camera_id": camera_id if camera_id != "" else null,
        },
        "vision_snapshot",
        "Failed to capture vision snapshot"
    )

func stop_session(session_id: String = "") -> void:
    _post_json(
        "/api/dojo/vision/stop",
        {
            "session_id": session_id if session_id != "" else null,
        },
        "vision_stop",
        "Failed to stop vision session"
    )

func report_snapshot(
    session_id: String,
    job_id: String,
    camera_id: String,
    image_base64: String,
    media_type: String,
    width: int,
    height: int,
    frame_summary: String,
    observations: Array,
    captured_at: String = ""
) -> void:
    _post_json(
        "/api/dojo/vision/report",
        {
            "session_id": session_id,
            "job_id": job_id,
            "camera_id": camera_id,
            "image_base64": image_base64,
            "media_type": media_type,
            "captured_at": captured_at if captured_at != "" else null,
            "width": width,
            "height": height,
            "frame_summary": frame_summary,
            "observations": observations,
        },
        "vision_report",
        "Failed to report vision snapshot"
    )

func cancel_request() -> void:
    if is_instance_valid(_active_request):
        _active_request.cancel_request()
    _dispose_request()

func _post_json(path: String, payload: Dictionary, action: String, error_prefix: String) -> void:
    if _request_in_progress:
        vision_error.emit("Vision request already in progress")
        return
    var http := _create_request(30.0)
    var headers := PackedStringArray(["Content-Type: application/json"])
    _pending_action = action
    _request_in_progress = true
    var err := http.request(
        "%s%s" % [bridge_base_url, path],
        headers,
        HTTPClient.METHOD_POST,
        JSON.stringify(payload)
    )
    if err != OK:
        _dispose_request()
        vision_error.emit("%s: %s" % [error_prefix, err])

func _on_request_completed(result: int, response_code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
    var action := _pending_action
    _dispose_request()
    if result != HTTPRequest.RESULT_SUCCESS:
        vision_error.emit("Vision request failed: %s" % result)
        return

    var text := body.get_string_from_utf8()
    var parsed = JSON.parse_string(text)
    if parsed == null:
        vision_error.emit("Vision service returned invalid JSON")
        return

    if response_code >= 400:
        if parsed is Dictionary and parsed.has("detail"):
            vision_error.emit(str(parsed.get("detail")))
        else:
            vision_error.emit(text if text != "" else "Vision service returned HTTP %s" % response_code)
        return

    if action == "vision_status":
        vision_status_loaded.emit(parsed)
        return

    vision_action_completed.emit(action, parsed)

func _create_request(timeout_seconds: float) -> HTTPRequest:
    _dispose_request()
    _active_request = HTTPRequest.new()
    _active_request.use_threads = true
    _active_request.timeout = timeout_seconds
    add_child(_active_request)
    _active_request.request_completed.connect(_on_request_completed)
    return _active_request

func _dispose_request() -> void:
    _request_in_progress = false
    _pending_action = ""
    if is_instance_valid(_active_request):
        if _active_request.request_completed.is_connected(_on_request_completed):
            _active_request.request_completed.disconnect(_on_request_completed)
        _active_request.queue_free()
    _active_request = null
