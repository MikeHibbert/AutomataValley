extends Node
class_name SttClient

signal transcript_ready(payload)
signal stt_error(message)

@export var stt_base_url: String = "http://127.0.0.1:8003"

var _http: HTTPRequest
var _request_in_progress: bool = false

func _ready() -> void:
    _http = HTTPRequest.new()
    _http.timeout = 120.0
    add_child(_http)
    _http.request_completed.connect(_on_request_completed)

func configure(base_url: String) -> void:
    if base_url != "":
        stt_base_url = base_url

func transcribe_text(text: String) -> void:
    if _request_in_progress:
        stt_error.emit("STT request already in progress")
        return
    var payload := {
        "text": text
    }
    var headers := PackedStringArray(["Content-Type: application/json"])
    _request_in_progress = true
    var err := _http.request(
        "%s/transcribe/text" % stt_base_url,
        headers,
        HTTPClient.METHOD_POST,
        JSON.stringify(payload)
    )
    if err != OK:
        _request_in_progress = false
        stt_error.emit("Failed to request STT: %s" % err)

func transcribe_audio_file(file_path: String, simulated_transcript: String = "") -> void:
    if _request_in_progress:
        stt_error.emit("STT request already in progress")
        return
    var file := FileAccess.open(file_path, FileAccess.READ)
    if file == null:
        stt_error.emit("Unable to open audio file")
        return

    var audio_bytes := file.get_buffer(file.get_length())
    var boundary := "----AutomataValleyBoundary%s" % Time.get_ticks_usec()
    var body := PackedByteArray()
    body.append_array(_append_form_field(boundary, "simulated_transcript", simulated_transcript))
    body.append_array(_append_file_field(boundary, "audio", file_path.get_file(), _guess_mime_type(file_path), audio_bytes))
    body.append_array(("--%s--\r\n" % boundary).to_utf8_buffer())

    var headers := PackedStringArray([
        "Content-Type: multipart/form-data; boundary=%s" % boundary
    ])
    _request_in_progress = true
    var err := _http.request_raw(
        "%s/transcribe" % stt_base_url,
        headers,
        HTTPClient.METHOD_POST,
        body
    )
    if err != OK:
        _request_in_progress = false
        stt_error.emit("Failed to upload audio to STT: %s" % err)

func _on_request_completed(result: int, response_code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
    _request_in_progress = false
    if result != HTTPRequest.RESULT_SUCCESS:
        stt_error.emit("STT request failed: %s" % result)
        return

    var text := body.get_string_from_utf8()
    if response_code >= 400:
        var detail := "STT returned HTTP %s" % response_code
        var parsed_error = JSON.parse_string(text)
        if parsed_error is Dictionary and parsed_error.has("detail"):
            detail = str(parsed_error.get("detail"))
        elif text.strip_edges() != "":
            detail = text
        stt_error.emit(detail)
        return

    var parsed = JSON.parse_string(text)
    if parsed == null:
        stt_error.emit("STT returned invalid JSON")
        return

    transcript_ready.emit(parsed)

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
        "wav":
            return "audio/wav"
        "ogg":
            return "audio/ogg"
        "mp3":
            return "audio/mpeg"
        _:
            return "application/octet-stream"
