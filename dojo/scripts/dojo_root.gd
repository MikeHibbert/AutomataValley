extends Node3D

const MIC_BUS_NAME := "DojoRecord"
const MIC_SINK_BUS_NAME := "DojoRecordSink"
const TEMP_RECORDING_PATH := "user://dojo_voice_capture.wav"
const VISION_CAPTURE_DIR := "user://vision_snapshots"

@onready var bridge_client: Node = $BridgeClient
@onready var stt_client: Node = $SttClient
@onready var tts_client: Node = $TtsClient
@onready var observation_client: Node = $ObservationClient
@onready var vision_client: Node = $VisionClient
@onready var operator_camera: Camera3D = $Camera3D
@onready var overlay: CanvasLayer = $Overlay
@onready var robot: MeshInstance3D = $Robot
@onready var robot_camera_rig: Node3D = $Robot/RobotCameraRig
@onready var world_objects_root: Node3D = $WorldObjects
@onready var status_label: Label = $Overlay/StatusLabel
@onready var command_label: Label = $Overlay/CommandLabel
@onready var target_label: Label = $Overlay/TargetLabel
@onready var command_input: LineEdit = $Overlay/CommandPanel/PanelMargin/CommandVBox/CommandInput
@onready var submit_button: Button = $Overlay/CommandPanel/PanelMargin/CommandVBox/ButtonRow/SubmitButton
@onready var move_north_button: Button = $Overlay/CommandPanel/PanelMargin/CommandVBox/ButtonRow/MoveNorthButton
@onready var go_to_table_button: Button = $Overlay/CommandPanel/PanelMargin/CommandVBox/ButtonRow/GoToTableButton
@onready var voice_state_label: Label = $Overlay/VoicePanel/VoiceMargin/VoiceVBox/VoiceStateLabel
@onready var transcript_label: Label = $Overlay/VoicePanel/VoiceMargin/VoiceVBox/TranscriptLabel
@onready var audio_file_label: Label = $Overlay/VoicePanel/VoiceMargin/VoiceVBox/AudioFileLabel
@onready var push_to_talk_button: Button = $Overlay/VoicePanel/VoiceMargin/VoiceVBox/VoiceButtonRow/PushToTalkButton
@onready var use_transcript_button: Button = $Overlay/VoicePanel/VoiceMargin/VoiceVBox/VoiceButtonRow/UseTranscriptButton
@onready var clear_transcript_button: Button = $Overlay/VoicePanel/VoiceMargin/VoiceVBox/VoiceButtonRow/ClearTranscriptButton
@onready var upload_audio_button: Button = $Overlay/VoicePanel/VoiceMargin/VoiceVBox/AudioButtonRow/UploadAudioButton
@onready var transcribe_audio_button: Button = $Overlay/VoicePanel/VoiceMargin/VoiceVBox/AudioButtonRow/TranscribeAudioButton
@onready var suggestion_label: Label = $Overlay/VoicePanel/VoiceMargin/VoiceVBox/SuggestionLabel
@onready var suggestion_one_button: Button = $Overlay/VoicePanel/VoiceMargin/VoiceVBox/SuggestionButtonRow/SuggestionOneButton
@onready var suggestion_two_button: Button = $Overlay/VoicePanel/VoiceMargin/VoiceVBox/SuggestionButtonRow/SuggestionTwoButton
@onready var audio_file_dialog: FileDialog = $AudioFileDialog
@onready var live_feed_label: Label = $Overlay/WorldPanel/WorldMargin/WorldVBox/LiveFeedLabel
@onready var vision_session_label: Label = $Overlay/WorldPanel/WorldMargin/WorldVBox/VisionSessionLabel
@onready var vision_tools_label: Label = $Overlay/WorldPanel/WorldMargin/WorldVBox/VisionToolsLabel
@onready var camera_picker: OptionButton = $Overlay/WorldPanel/WorldMargin/WorldVBox/CameraPicker
@onready var held_object_label: Label = $Overlay/WorldPanel/WorldMargin/WorldVBox/HeldObjectLabel
@onready var world_objects_label: Label = $Overlay/WorldPanel/WorldMargin/WorldVBox/WorldObjectsLabel
@onready var start_vision_button: Button = $Overlay/WorldPanel/WorldMargin/WorldVBox/WorldButtonRow/StartVisionButton
@onready var snapshot_vision_button: Button = $Overlay/WorldPanel/WorldMargin/WorldVBox/WorldButtonRow/SnapshotVisionButton
@onready var stop_vision_button: Button = $Overlay/WorldPanel/WorldMargin/WorldVBox/WorldButtonRow/StopVisionButton
@onready var upload_image_button: Button = $Overlay/WorldPanel/WorldMargin/WorldVBox/ImageButtonRow/UploadImageButton
@onready var observe_image_button: Button = $Overlay/WorldPanel/WorldMargin/WorldVBox/ImageButtonRow/ObserveImageButton
@onready var observation_label: Label = $Overlay/WorldPanel/WorldMargin/WorldVBox/ObservationLabel
@onready var image_file_dialog: FileDialog = $ImageFileDialog

var _voice_state: String = "idle"
var _pending_transcript: String = ""
var _selected_audio_path: String = ""
var _record_bus_index: int = -1
var _record_sink_bus_index: int = -1
var _record_effect: AudioEffectRecord
var _mic_player: AudioStreamPlayer
var _suggestions: Array[String] = []
var _voice_watchdog: Timer
var _voice_watchdog_reason: String = ""
var _selected_image_path: String = ""
var _held_object_id: String = ""
var _world_objects: Array = []
var _object_nodes: Dictionary = {}
var _vision_poll_timer: Timer
var _vision_session_id: String = ""
var _robot_camera_nodes: Dictionary = {}
var _robot_cameras: Array = []
var _selected_robot_camera_id: String = "front_cam"
var _vision_capture_in_progress: bool = false
var _pending_vision_job_id: String = ""

func _ready() -> void:
    bridge_client.bootstrap_loaded.connect(_on_bootstrap_loaded)
    bridge_client.command_completed.connect(_on_command_completed)
    bridge_client.bridge_error.connect(_on_bridge_error)
    stt_client.transcript_ready.connect(_on_transcript_ready)
    stt_client.stt_error.connect(_on_stt_error)
    tts_client.speech_ready.connect(_on_tts_speech_ready)
    tts_client.tts_error.connect(_on_tts_error)
    observation_client.observation_ready.connect(_on_observation_ready)
    observation_client.observation_error.connect(_on_observation_error)
    vision_client.vision_status_loaded.connect(_on_vision_status_loaded)
    vision_client.vision_action_completed.connect(_on_vision_action_completed)
    vision_client.vision_error.connect(_on_vision_error)
    submit_button.pressed.connect(_on_submit_pressed)
    move_north_button.pressed.connect(_on_move_north_pressed)
    go_to_table_button.pressed.connect(_on_go_to_table_pressed)
    command_input.text_submitted.connect(_on_command_text_submitted)
    push_to_talk_button.pressed.connect(_on_push_to_talk_pressed)
    use_transcript_button.pressed.connect(_on_use_transcript_pressed)
    clear_transcript_button.pressed.connect(_on_clear_transcript_pressed)
    upload_audio_button.pressed.connect(_on_upload_audio_pressed)
    transcribe_audio_button.pressed.connect(_on_transcribe_audio_pressed)
    suggestion_one_button.pressed.connect(_on_suggestion_one_pressed)
    suggestion_two_button.pressed.connect(_on_suggestion_two_pressed)
    start_vision_button.pressed.connect(_on_start_vision_pressed)
    snapshot_vision_button.pressed.connect(_on_snapshot_vision_pressed)
    stop_vision_button.pressed.connect(_on_stop_vision_pressed)
    camera_picker.item_selected.connect(_on_camera_picker_selected)
    audio_file_dialog.file_selected.connect(_on_audio_file_selected)
    upload_image_button.pressed.connect(_on_upload_image_pressed)
    observe_image_button.pressed.connect(_on_observe_image_pressed)
    image_file_dialog.file_selected.connect(_on_image_file_selected)
    _voice_watchdog = Timer.new()
    _voice_watchdog.one_shot = true
    _voice_watchdog.timeout.connect(_on_voice_watchdog_timeout)
    add_child(_voice_watchdog)
    _vision_poll_timer = Timer.new()
    _vision_poll_timer.one_shot = false
    _vision_poll_timer.wait_time = 3.0
    _vision_poll_timer.timeout.connect(_on_vision_poll_timeout)
    add_child(_vision_poll_timer)
    _set_controls_enabled(false)
    _register_robot_cameras()
    _update_voice_ui()
    status_label.text = "Connecting to bridge..."

func _on_bootstrap_loaded(payload: Dictionary) -> void:
    var stt_payload: Dictionary = payload.get("stt", {})
    var tts_payload: Dictionary = payload.get("tts", {})
    stt_client.configure(stt_payload.get("url", ""))
    tts_client.configure(tts_payload.get("url", ""))
    _set_controls_enabled(true)
    status_label.text = "Connected to AutomataValley bridge"
    command_label.text = "Robot: %s" % payload.get("robot", {}).get("id", "unknown")
    target_label.text = "Ready for navigation commands"
    _apply_world_state(payload.get("world", {}))
    _apply_mcp_tools(payload.get("mcp_tools", []))
    vision_client.request_status()
    _vision_poll_timer.start()
    command_input.grab_focus()

func _on_command_completed(payload: Dictionary) -> void:
    _clear_voice_watchdog()
    var submitted: Dictionary = payload.get("submitted_command", {})
    var interpretation: Dictionary = payload.get("interpretation", {})
    var events: Array = payload.get("events", [])
    var disposition := str(interpretation.get("disposition", "execute"))
    var message := str(interpretation.get("message", "Task complete"))
    var spoken_response := str(interpretation.get("spoken_response", message))
    var canonical_command := str(interpretation.get("canonical_command", "")).strip_edges()
    var suggestions: Array = interpretation.get("suggestions", [])

    _apply_suggestions(suggestions)
    command_label.text = "Command: %s" % (canonical_command if canonical_command != "" else submitted.get("command_text", "unknown"))

    if spoken_response != "":
        tts_client.speak_text(spoken_response)

    if disposition != "execute":
        status_label.text = message
        target_label.text = "Target: awaiting clarification" if disposition == "clarify" else "Target: none"
        _voice_state = "ready" if disposition == "clarify" else "idle"
        _update_voice_ui()
        return

    if events.is_empty():
        status_label.text = message
        target_label.text = "Target: none"
        _voice_state = "idle"
        _update_voice_ui()
        return

    var latest_event: Dictionary = events[events.size() - 1]
    var data: Dictionary = latest_event.get("data", {})
    _apply_task_event(latest_event)
    target_label.text = "Target: %s" % data.get("target", "unknown")

    var position: Dictionary = data.get("position", {})
    if not position.is_empty():
        robot.position = Vector3(
            float(position.get("x", 0.0)),
            float(position.get("y", 0.95)),
            float(position.get("z", 0.0))
        )
    status_label.text = message
    command_input.clear()
    _voice_state = "idle"
    _update_voice_ui()

func _on_bridge_error(message: String) -> void:
    _clear_voice_watchdog()
    status_label.text = message
    target_label.text = "Target: bridge request failed"
    _voice_state = "error"
    _update_voice_ui()

func _on_submit_pressed() -> void:
    _submit_current_command()

func _on_move_north_pressed() -> void:
    _send_command("move north")

func _on_go_to_table_pressed() -> void:
    _send_command("go to table")

func _on_command_text_submitted(_new_text: String) -> void:
    _submit_current_command()

func _on_push_to_talk_pressed() -> void:
    if _voice_state == "idle":
        _start_microphone_capture()
        return

    if _voice_state == "listening":
        _stop_microphone_capture()
        return

    status_label.text = "Voice request already in progress"
    _update_voice_ui()

func _on_use_transcript_pressed() -> void:
    if _pending_transcript == "":
        status_label.text = "No transcript available"
        return
    _send_command(_pending_transcript, _pending_transcript)

func _on_clear_transcript_pressed() -> void:
    _pending_transcript = ""
    if _voice_state != "error":
        _voice_state = "idle"
    _update_voice_ui()

func _on_upload_audio_pressed() -> void:
    audio_file_dialog.popup_centered_ratio(0.6)

func _on_transcribe_audio_pressed() -> void:
    if _selected_audio_path == "":
        status_label.text = "Select an audio file first"
        return
    _voice_state = "transcribing"
    status_label.text = "Uploading audio to STT service..."
    target_label.text = "Target: waiting for STT"
    _arm_voice_watchdog(120.0, "STT request timed out while transcribing audio.")
    _update_voice_ui()
    stt_client.transcribe_audio_file(_selected_audio_path, command_input.text.strip_edges())

func _on_audio_file_selected(path: String) -> void:
    _selected_audio_path = path
    audio_file_label.text = "Audio File: %s" % path.get_file()
    status_label.text = "Audio file ready"
    _update_voice_ui()

func _on_transcript_ready(payload: Dictionary) -> void:
    _clear_voice_watchdog()
    _pending_transcript = str(payload.get("transcript", "")).strip_edges()
    if _pending_transcript == "":
        status_label.text = "STT returned an empty transcript"
        target_label.text = "Target: transcript empty"
        _voice_state = "idle"
        _update_voice_ui()
        return
    command_input.text = _pending_transcript
    _voice_state = "ready"
    target_label.text = "Target: transcript ready"
    _update_voice_ui()
    status_label.text = "Transcript ready"

func _on_stt_error(message: String) -> void:
    _clear_voice_watchdog()
    status_label.text = message
    target_label.text = "Target: STT request failed"
    _voice_state = "error"
    _update_voice_ui()

func _on_tts_speech_ready(_spoken_text: String) -> void:
    pass

func _on_tts_error(message: String) -> void:
    status_label.text = "TTS unavailable: %s" % message

func _on_upload_image_pressed() -> void:
    image_file_dialog.popup_centered_ratio(0.6)

func _on_observe_image_pressed() -> void:
    if _selected_image_path == "":
        observation_label.text = "Observation: select an image first"
        return
    observation_label.text = "Observation: uploading scene image..."
    observation_client.observe_image(_selected_image_path, command_input.text.strip_edges())

func _on_image_file_selected(path: String) -> void:
    _selected_image_path = path
    observation_label.text = "Observation: image ready (%s)" % path.get_file()

func _on_observation_ready(payload: Dictionary) -> void:
    observation_label.text = "Observation: %s" % str(payload.get("message", "Image observation complete"))
    _apply_world_state(payload.get("world", {}))
    var observations: Array = payload.get("observations", [])
    if not observations.is_empty():
        var labels: Array[String] = []
        for item in observations:
            labels.append(str(item.get("label", "unknown")))
        world_objects_label.text = "Known Objects: %s" % ", ".join(labels)

func _on_observation_error(message: String) -> void:
    observation_label.text = "Observation: %s" % message

func _on_start_vision_pressed() -> void:
    observation_label.text = "Observation: starting on-demand vision session..."
    vision_client.start_session("dojo_operator", "manual dojo inspection", "snapshot", _selected_robot_camera_id)

func _on_snapshot_vision_pressed() -> void:
    observation_label.text = "Observation: capturing dojo vision snapshot..."
    vision_client.request_snapshot(command_input.text.strip_edges(), _selected_robot_camera_id)

func _on_stop_vision_pressed() -> void:
    observation_label.text = "Observation: stopping dojo vision session..."
    vision_client.stop_session(_vision_session_id)

func _on_vision_status_loaded(payload: Dictionary) -> void:
    _apply_vision_payload(payload)

func _on_vision_action_completed(action: String, payload: Dictionary) -> void:
    _apply_vision_payload(payload)
    if action == "vision_snapshot":
        var snapshot: Dictionary = payload.get("snapshot", {})
        observation_label.text = "Observation: %s" % str(snapshot.get("frame_summary", payload.get("message", "Vision snapshot ready")))
        return
    observation_label.text = "Observation: %s" % str(payload.get("message", "Vision action complete"))

func _on_vision_error(message: String) -> void:
    observation_label.text = "Observation: %s" % message

func _on_vision_poll_timeout() -> void:
    if _vision_capture_in_progress:
        return
    vision_client.request_status()

func _on_camera_picker_selected(index: int) -> void:
    var camera_id := _camera_id_for_index(index)
    if camera_id != "":
        _selected_robot_camera_id = camera_id
        live_feed_label.text = "Live Feed: selected %s for the next vision request" % _format_entity_name(camera_id)

func _on_suggestion_one_pressed() -> void:
    _submit_suggestion(0)

func _on_suggestion_two_pressed() -> void:
    _submit_suggestion(1)

func _submit_current_command() -> void:
    var text := command_input.text.strip_edges()
    if text == "":
        status_label.text = "Enter a command first"
        return
    _send_command(text)

func _send_command(command_text: String, transcript: String = "") -> void:
    status_label.text = "Submitting command..."
    target_label.text = "Target: waiting for bridge"
    bridge_client.send_command(command_text, transcript)
    _voice_state = "submitting"
    _arm_voice_watchdog(30.0, "Bridge request timed out while submitting the command.")
    _update_voice_ui()

func _submit_suggestion(index: int) -> void:
    if index < 0 or index >= _suggestions.size():
        return
    var suggestion := _suggestions[index]
    command_input.text = suggestion
    _send_command(suggestion, _pending_transcript if _pending_transcript != "" else suggestion)

func _set_controls_enabled(enabled: bool) -> void:
    command_input.editable = enabled
    submit_button.disabled = not enabled
    move_north_button.disabled = not enabled
    go_to_table_button.disabled = not enabled
    push_to_talk_button.disabled = not enabled
    clear_transcript_button.disabled = not enabled
    upload_audio_button.disabled = not enabled
    transcribe_audio_button.disabled = not enabled or _selected_audio_path == ""
    start_vision_button.disabled = not enabled
    snapshot_vision_button.disabled = not enabled or _selected_robot_camera_id == ""
    stop_vision_button.disabled = not enabled
    upload_image_button.disabled = not enabled
    observe_image_button.disabled = not enabled or _selected_image_path == ""
    use_transcript_button.disabled = not enabled or _pending_transcript == ""
    suggestion_one_button.disabled = not enabled or _suggestions.is_empty()
    suggestion_two_button.disabled = not enabled or _suggestions.size() < 2

func _setup_microphone_capture() -> bool:
    if _record_effect != null and is_instance_valid(_mic_player):
        return true

    var sink_bus_index := AudioServer.get_bus_index(MIC_SINK_BUS_NAME)
    if sink_bus_index == -1:
        sink_bus_index = AudioServer.bus_count
        AudioServer.add_bus(sink_bus_index)
        AudioServer.set_bus_name(sink_bus_index, MIC_SINK_BUS_NAME)
        AudioServer.set_bus_mute(sink_bus_index, true)

    var bus_index := AudioServer.get_bus_index(MIC_BUS_NAME)
    if bus_index == -1:
        bus_index = AudioServer.bus_count
        AudioServer.add_bus(bus_index)
        AudioServer.set_bus_name(bus_index, MIC_BUS_NAME)
        AudioServer.set_bus_send(bus_index, MIC_SINK_BUS_NAME)
        AudioServer.set_bus_mute(bus_index, false)
    elif AudioServer.get_bus_send(bus_index) != MIC_SINK_BUS_NAME:
        AudioServer.set_bus_send(bus_index, MIC_SINK_BUS_NAME)

    var record_effect: AudioEffectRecord = null
    for effect_index in range(AudioServer.get_bus_effect_count(bus_index)):
        var effect := AudioServer.get_bus_effect(bus_index, effect_index)
        if effect is AudioEffectRecord:
            record_effect = effect
            break

    if record_effect == null:
        record_effect = AudioEffectRecord.new()
        AudioServer.add_bus_effect(bus_index, record_effect, 0)

    _record_bus_index = bus_index
    _record_sink_bus_index = sink_bus_index
    _record_effect = record_effect

    if not is_instance_valid(_mic_player):
        _mic_player = AudioStreamPlayer.new()
        _mic_player.name = "MicCapturePlayer"
        _mic_player.bus = MIC_BUS_NAME
        _mic_player.volume_db = 0.0
        _mic_player.stream = AudioStreamMicrophone.new()
        add_child(_mic_player)

    return true

func _start_microphone_capture() -> void:
    if not _setup_microphone_capture():
        _voice_state = "error"
        status_label.text = "Unable to initialize microphone capture"
        _update_voice_ui()
        return

    _clear_voice_watchdog()
    _pending_transcript = ""
    _record_effect.set_recording_active(true)
    _mic_player.play()
    _voice_state = "listening"
    status_label.text = "Recording microphone input..."
    target_label.text = "Target: recording voice"
    _update_voice_ui()

func _stop_microphone_capture() -> void:
    if _record_effect == null or not is_instance_valid(_mic_player):
        _voice_state = "error"
        status_label.text = "Microphone capture is not ready"
        _update_voice_ui()
        return

    _voice_state = "transcribing"
    status_label.text = "Finalizing microphone audio..."
    target_label.text = "Target: preparing audio"
    _update_voice_ui()

    _record_effect.set_recording_active(false)
    _mic_player.stop()
    _finalize_microphone_capture()

func _finalize_microphone_capture() -> void:
    await get_tree().process_frame

    var recording: AudioStreamWAV = _record_effect.get_recording()
    if recording == null:
        _voice_state = "error"
        status_label.text = "No microphone recording was captured"
        _update_voice_ui()
        return

    recording.set_format(AudioStreamWAV.FORMAT_16_BITS)
    var save_error := recording.save_to_wav(TEMP_RECORDING_PATH)
    if save_error != OK:
        _voice_state = "error"
        status_label.text = "Failed to save microphone audio"
        _update_voice_ui()
        return
    _selected_audio_path = ProjectSettings.globalize_path(TEMP_RECORDING_PATH)
    status_label.text = "Uploading recorded audio to STT service..."
    target_label.text = "Target: waiting for STT"
    audio_file_label.text = "Audio File: %s" % _selected_audio_path.get_file()
    _arm_voice_watchdog(120.0, "STT request timed out while uploading microphone audio.")
    _update_voice_ui()
    stt_client.transcribe_audio_file(_selected_audio_path)

func _arm_voice_watchdog(timeout_seconds: float, reason: String) -> void:
    if not is_instance_valid(_voice_watchdog):
        return
    _voice_watchdog_reason = reason
    _voice_watchdog.stop()
    _voice_watchdog.wait_time = timeout_seconds
    _voice_watchdog.start()

func _clear_voice_watchdog() -> void:
    if is_instance_valid(_voice_watchdog):
        _voice_watchdog.stop()
    _voice_watchdog_reason = ""

func _on_voice_watchdog_timeout() -> void:
    if _voice_watchdog_reason == "":
        return
    if _voice_state == "transcribing":
        stt_client.cancel_request()
    elif _voice_state == "submitting":
        bridge_client.cancel_request()
    _voice_state = "error"
    status_label.text = _voice_watchdog_reason
    target_label.text = "Target: request timed out"
    _update_voice_ui()

func _update_voice_ui() -> void:
    voice_state_label.text = "Voice: %s" % _voice_state
    transcript_label.text = "Transcript: %s" % (_pending_transcript if _pending_transcript != "" else "none")
    audio_file_label.text = "Audio File: %s" % (_selected_audio_path.get_file() if _selected_audio_path != "" else "none")
    suggestion_label.text = "Suggestions: %s" % (", ".join(_suggestions) if not _suggestions.is_empty() else "none")
    suggestion_one_button.visible = not _suggestions.is_empty()
    suggestion_two_button.visible = _suggestions.size() > 1
    suggestion_one_button.disabled = _suggestions.is_empty()
    suggestion_two_button.disabled = _suggestions.size() < 2
    if not _suggestions.is_empty():
        suggestion_one_button.text = _suggestions[0]
    if _suggestions.size() > 1:
        suggestion_two_button.text = _suggestions[1]

    match _voice_state:
        "idle":
            push_to_talk_button.text = "Push To Talk"
        "listening":
            push_to_talk_button.text = "Stop Listening"
        "transcribing":
            push_to_talk_button.text = "Transcribing..."
        _:
            push_to_talk_button.text = "Push To Talk"

    use_transcript_button.disabled = _pending_transcript == ""
    transcribe_audio_button.disabled = _selected_audio_path == ""

func _apply_suggestions(raw_suggestions: Array) -> void:
    _suggestions.clear()
    for suggestion in raw_suggestions:
        var cleaned := str(suggestion).strip_edges()
        if cleaned != "":
            _suggestions.append(cleaned)
        if _suggestions.size() == 2:
            break
    _update_voice_ui()

func _apply_world_state(world: Dictionary) -> void:
    var robot_state: Dictionary = world.get("robot_state", {})
    var vision: Dictionary = world.get("vision", {})
    var live_feed: Dictionary = vision.get("live_feed", {})
    _world_objects = world.get("objects", [])
    _robot_cameras = robot_state.get("cameras", [])
    _held_object_id = str(robot_state.get("held_object", "")).strip_edges()
    held_object_label.text = "Held Object: %s" % (_format_entity_name(_held_object_id) if _held_object_id != "" else "none")
    live_feed_label.text = "Live Feed: %s" % str(live_feed.get("notes", "placeholder"))
    _vision_session_id = str(live_feed.get("session", {}).get("session_id", "")).strip_edges()
    _selected_robot_camera_id = str(live_feed.get("camera_id", _selected_robot_camera_id)).strip_edges()
    vision_session_label.text = "Vision Session: %s" % ("active" if bool(live_feed.get("active", false)) else "inactive")
    _populate_camera_picker(_robot_cameras)

    var labels: Array[String] = []
    for object_payload in _world_objects:
        labels.append(str(object_payload.get("label", "unknown")))
    world_objects_label.text = "Known Objects: %s" % (", ".join(labels) if not labels.is_empty() else "none")
    _render_world_objects(_world_objects)
    snapshot_vision_button.disabled = not bool(live_feed.get("active", false))
    stop_vision_button.disabled = not bool(live_feed.get("active", false))

func _apply_vision_payload(payload: Dictionary) -> void:
    var status: Dictionary = payload.get("status", {})
    _apply_mcp_tools(payload.get("tools", []))
    if status.is_empty():
        return
    live_feed_label.text = "Live Feed: %s" % str(status.get("notes", "on-demand vision"))
    _selected_robot_camera_id = str(status.get("camera_id", _selected_robot_camera_id)).strip_edges()
    var session: Dictionary = status.get("session", {})
    var is_active := bool(status.get("active", false))
    _vision_session_id = str(session.get("session_id", "")).strip_edges()
    _pending_vision_job_id = str(status.get("pending_request", {}).get("job_id", "")).strip_edges()
    vision_session_label.text = "Vision Session: %s" % ("active (%s)" % _vision_session_id.left(8) if is_active and _vision_session_id != "" else "inactive")
    snapshot_vision_button.disabled = not is_active
    stop_vision_button.disabled = not is_active
    _select_camera_picker_id(_selected_robot_camera_id)

    var latest_snapshot: Dictionary = status.get("latest_snapshot", {})
    if not latest_snapshot.is_empty() and str(latest_snapshot.get("frame_summary", "")).strip_edges() != "":
        observation_label.text = "Observation: %s" % str(latest_snapshot.get("frame_summary", "Vision snapshot ready"))
    _maybe_service_pending_snapshot(status)

func _apply_mcp_tools(tools: Array) -> void:
    var names: Array[String] = []
    for tool_payload in tools:
        names.append(str(tool_payload.get("name", "")))
    vision_tools_label.text = "MCP Tools: %s" % (", ".join(names) if not names.is_empty() else "none")

func _register_robot_cameras() -> void:
    _robot_camera_nodes = {
        "front_cam": $Robot/RobotCameraRig/FrontCam,
        "left_cam": $Robot/RobotCameraRig/LeftCam,
        "right_cam": $Robot/RobotCameraRig/RightCam,
        "rear_cam": $Robot/RobotCameraRig/RearCam,
    }

func _populate_camera_picker(cameras: Array) -> void:
    camera_picker.clear()
    for camera_payload in cameras:
        camera_picker.add_item(str(camera_payload.get("label", camera_payload.get("id", "camera"))))
        camera_picker.set_item_metadata(camera_picker.item_count - 1, str(camera_payload.get("id", "")))
    if camera_picker.item_count > 0:
        _select_camera_picker_id(_selected_robot_camera_id)

func _select_camera_picker_id(camera_id: String) -> void:
    for index in range(camera_picker.item_count):
        if str(camera_picker.get_item_metadata(index)) == camera_id:
            camera_picker.select(index)
            return
    if camera_picker.item_count > 0:
        camera_picker.select(0)
        _selected_robot_camera_id = _camera_id_for_index(0)

func _camera_id_for_index(index: int) -> String:
    if index < 0 or index >= camera_picker.item_count:
        return ""
    return str(camera_picker.get_item_metadata(index))

func _maybe_service_pending_snapshot(status: Dictionary) -> void:
    if _vision_capture_in_progress:
        return
    var pending_request: Dictionary = status.get("pending_request", {})
    if pending_request.is_empty():
        _pending_vision_job_id = ""
        return
    var job_id := str(pending_request.get("job_id", "")).strip_edges()
    if job_id == "" or job_id == _pending_vision_job_id:
        return
    _pending_vision_job_id = job_id
    _capture_and_report_pending_snapshot(pending_request)

func _capture_and_report_pending_snapshot(pending_request: Dictionary) -> void:
    _vision_capture_in_progress = true
    var camera_id := str(pending_request.get("camera_id", _selected_robot_camera_id)).strip_edges()
    var capture := await _capture_robot_camera_snapshot(camera_id)
    if not bool(capture.get("ok", false)):
        observation_label.text = "Observation: %s" % str(capture.get("message", "Robot camera capture failed"))
        _pending_vision_job_id = ""
        _vision_capture_in_progress = false
        return

    vision_client.report_snapshot(
        str(pending_request.get("session_id", "")),
        str(pending_request.get("job_id", "")),
        camera_id,
        str(capture.get("image_base64", "")),
        "image/png",
        int(capture.get("width", 0)),
        int(capture.get("height", 0)),
        str(capture.get("summary", "")),
        capture.get("observations", []),
        Time.get_datetime_string_from_system(true, true)
    )
    _vision_capture_in_progress = false

func _capture_robot_camera_snapshot(camera_id: String) -> Dictionary:
    var camera: Camera3D = _robot_camera_nodes.get(camera_id)
    if camera == null:
        return {"ok": false, "message": "Robot camera %s is not available" % camera_id}

    var capture_dir := ProjectSettings.globalize_path(VISION_CAPTURE_DIR)
    DirAccess.make_dir_recursive_absolute(capture_dir)
    var capture_path := "%s/%s-%s.png" % [capture_dir, camera_id, Time.get_ticks_usec()]

    overlay.visible = false
    camera.current = true
    await get_tree().process_frame
    await get_tree().process_frame

    var image: Image = get_viewport().get_texture().get_image()
    operator_camera.current = true
    overlay.visible = true

    if image == null:
        return {"ok": false, "message": "Failed to capture image from %s" % camera_id}

    image.flip_y()
    var save_error := image.save_png(capture_path)
    if save_error != OK:
        return {"ok": false, "message": "Failed to save robot camera snapshot"}

    var file_bytes := FileAccess.get_file_as_bytes(capture_path)
    var observations: Array[Dictionary] = []
    for object_payload in _world_objects:
        observations.append(
            {
                "object_id": str(object_payload.get("id", "")),
                "label": str(object_payload.get("label", "")),
                "confidence": 0.66,
                "position": object_payload.get("position", {}),
                "located_on": object_payload.get("located_on", null),
            }
        )

    var summary := "Robot camera %s captured %sx%s and can currently see %s known dojo object(s)." % [
        _format_entity_name(camera_id),
        image.get_width(),
        image.get_height(),
        _world_objects.size(),
    ]
    return {
        "ok": true,
        "image_base64": Marshalls.raw_to_base64(file_bytes),
        "width": image.get_width(),
        "height": image.get_height(),
        "summary": summary,
        "observations": observations,
    }

func _render_world_objects(objects: Array) -> void:
    for child in world_objects_root.get_children():
        child.queue_free()
    _object_nodes.clear()

    for object_payload in objects:
        var mesh_instance := MeshInstance3D.new()
        mesh_instance.name = str(object_payload.get("id", "object"))
        var mesh := SphereMesh.new()
        mesh.radius = 0.22
        mesh.height = 0.44
        mesh_instance.mesh = mesh

        var material := StandardMaterial3D.new()
        material.albedo_color = _color_for_hint(str(object_payload.get("color_hint", "")))
        mesh_instance.set_surface_override_material(0, material)

        var position: Dictionary = object_payload.get("position", {})
        mesh_instance.position = Vector3(
            float(position.get("x", 0.0)),
            float(position.get("y", 0.4)),
            float(position.get("z", 0.0))
        )
        world_objects_root.add_child(mesh_instance)
        _object_nodes[str(object_payload.get("id", ""))] = mesh_instance

func _apply_task_event(event_payload: Dictionary) -> void:
    var event_type := str(event_payload.get("event_type", ""))
    var data: Dictionary = event_payload.get("data", {})
    if event_type == "object_picked_up":
        _held_object_id = str(data.get("held_object", "")).strip_edges()
        held_object_label.text = "Held Object: %s" % _format_entity_name(_held_object_id)
        return
    if event_type == "object_placed":
        _held_object_id = ""
        held_object_label.text = "Held Object: none"
        var placed_object_id := str(data.get("placed_object", "")).strip_edges()
        if placed_object_id != "" and _object_nodes.has(placed_object_id):
            var mesh_instance: MeshInstance3D = _object_nodes[placed_object_id]
            var position: Dictionary = data.get("position", {})
            mesh_instance.position = Vector3(
                float(position.get("x", 0.0)),
                float(position.get("y", 0.9)),
                float(position.get("z", 0.0))
            )

func _color_for_hint(hint: String) -> Color:
    match hint:
        "red":
            return Color(0.85, 0.2, 0.2)
        "orange":
            return Color(0.92, 0.55, 0.2)
        "blue":
            return Color(0.25, 0.45, 0.9)
        "yellow":
            return Color(0.9, 0.8, 0.2)
        _:
            return Color(0.7, 0.7, 0.7)

func _format_entity_name(entity_id: String) -> String:
    return entity_id.replace("_", " ")
