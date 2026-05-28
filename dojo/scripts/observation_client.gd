extends Node
class_name ObservationClient

signal observation_ready(payload)
signal observation_error(message)

@export var bridge_base_url: String = "http://127.0.0.1:8002"

var _active_request: HTTPRequest
var _request_in_progress: bool = false

func configure(base_url: String) -> void:
    if base_url != "":
        bridge_base_url = base_url

func observe_image(file_path: String, note: String = "") -> void:
    if _request_in_progress:
        observation_error.emit("Image observation already in progress")
        return

    var file := FileAccess.open(file_path, FileAccess.READ)
    if file == null:
        observation_error.emit("Unable to open image file")
        return

    var image_bytes := file.get_buffer(file.get_length())
    var boundary := "----AutomataValleyObservation%s" % Time.get_ticks_usec()
    var body := PackedByteArray()
    body.append_array(_append_form_field(boundary, "note", note))
    body.append_array(_append_file_field(boundary, "image", file_path.get_file(), _guess_mime_type(file_path), image_bytes))
    body.append_array(("--%s--\r\n" % boundary).to_utf8_buffer())

    var http := _create_request(60.0)
    var headers := PackedStringArray([
        "Content-Type: multipart/form-data; boundary=%s" % boundary
    ])
    _request_in_progress = true
    var err := http.request_raw(
        "%s/api/dojo/observe/image" % bridge_base_url,
        headers,
        HTTPClient.METHOD_POST,
        body
    )
    if err != OK:
        _dispose_request()
        observation_error.emit("Failed to upload image: %s" % err)

func cancel_request() -> void:
    if is_instance_valid(_active_request):
        _active_request.cancel_request()
    _dispose_request()

func _on_request_completed(result: int, response_code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
    _dispose_request()
    if result != HTTPRequest.RESULT_SUCCESS:
        observation_error.emit("Image observation request failed: %s" % result)
        return

    var text := body.get_string_from_utf8()
    if response_code >= 400:
        observation_error.emit(text if text.strip_edges() != "" else "Image observation returned HTTP %s" % response_code)
        return

    var parsed = JSON.parse_string(text)
    if parsed == null:
        observation_error.emit("Image observation returned invalid JSON")
        return

    observation_ready.emit(parsed)

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
    if is_instance_valid(_active_request):
        if _active_request.request_completed.is_connected(_on_request_completed):
            _active_request.request_completed.disconnect(_on_request_completed)
        _active_request.queue_free()
    _active_request = null

func _append_form_field(boundary: String, field_name: String, value: String) -> PackedByteArray:
    var chunk := "--%s\r\n" % boundary
    chunk += "Content-Disposition: form-data; name=\"%s\"\r\n\r\n" % field_name
    chunk += "%s\r\n" % value
    return chunk.to_utf8_buffer()

func _append_file_field(boundary: String, field_name: String, filename: String, content_type: String, bytes: PackedByteArray) -> PackedByteArray:
    var prefix := "--%s\r\n" % boundary
    prefix += "Content-Disposition: form-data; name=\"%s\"; filename=\"%s\"\r\n" % [field_name, filename]
    prefix += "Content-Type: %s\r\n\r\n" % content_type
    var body := prefix.to_utf8_buffer()
    body.append_array(bytes)
    body.append_array("\r\n".to_utf8_buffer())
    return body

func _guess_mime_type(file_path: String) -> String:
    var extension := file_path.get_extension().to_lower()
    match extension:
        "png":
            return "image/png"
        "jpg", "jpeg":
            return "image/jpeg"
        "webp":
            return "image/webp"
        _:
            return "application/octet-stream"
