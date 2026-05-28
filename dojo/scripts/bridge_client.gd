extends Node
class_name BridgeClient

signal bootstrap_loaded(payload)
signal command_completed(payload)
signal bridge_error(message)

@export var bridge_base_url: String = "http://127.0.0.1:8002"

var _http: HTTPRequest
var _request_in_progress: bool = false

func _ready() -> void:
    _http = HTTPRequest.new()
    _http.timeout = 30.0
    add_child(_http)
    _http.request_completed.connect(_on_request_completed)
    request_bootstrap()

func request_bootstrap() -> void:
    if _request_in_progress:
        bridge_error.emit("Bridge request already in progress")
        return
    _request_in_progress = true
    var err := _http.request("%s/api/bootstrap" % bridge_base_url)
    if err != OK:
        _request_in_progress = false
        bridge_error.emit("Failed to request bootstrap: %s" % err)

func send_command(command_text: String, transcript: String = "") -> void:
    if _request_in_progress:
        bridge_error.emit("Bridge request already in progress")
        return
    var payload := {
        "command_id": _make_id(),
        "timestamp": Time.get_datetime_string_from_system(true, true),
        "session_id": _make_id(),
        "robot_id": "dojo-bot-01",
        "source": "dojo_voice",
        "transcript": transcript if transcript != "" else command_text,
        "command_text": command_text,
        "command_type": "navigation",
        "metadata": {
            "stt_engine": "parakeet",
            "confidence": 1.0
        }
    }
    var headers := PackedStringArray(["Content-Type: application/json"])
    _request_in_progress = true
    var err := _http.request(
        "%s/api/dojo/commands" % bridge_base_url,
        headers,
        HTTPClient.METHOD_POST,
        JSON.stringify(payload)
    )
    if err != OK:
        _request_in_progress = false
        bridge_error.emit("Failed to send command: %s" % err)

func cancel_request() -> void:
    if is_instance_valid(_http):
        _http.cancel_request()
    _request_in_progress = false

func _make_id() -> String:
    return str(Time.get_ticks_usec())

func _on_request_completed(result: int, response_code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
    _request_in_progress = false
    if result != HTTPRequest.RESULT_SUCCESS:
        bridge_error.emit("Bridge request failed: %s" % result)
        return

    var text := body.get_string_from_utf8()
    var parsed = JSON.parse_string(text)
    if parsed == null and response_code < 400:
        bridge_error.emit("Bridge returned invalid JSON")
        return

    if response_code >= 400:
        var detail := "Bridge returned HTTP %s" % response_code
        if parsed is Dictionary and parsed.has("detail"):
            detail = str(parsed.get("detail"))
        elif text != "":
            detail = text
        bridge_error.emit(detail)
        return

    if parsed.has("waypoints"):
        bootstrap_loaded.emit(parsed)
        return

    command_completed.emit(parsed)
