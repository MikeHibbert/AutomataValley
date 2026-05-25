extends Node3D

const MIC_BUS_NAME := "DojoRecord"
const MIC_SINK_BUS_NAME := "DojoRecordSink"
const TEMP_RECORDING_PATH := "user://dojo_voice_capture.wav"

@onready var bridge_client: Node = $BridgeClient
@onready var stt_client: Node = $SttClient
@onready var tts_client: Node = $TtsClient
@onready var robot: MeshInstance3D = $Robot
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

var _voice_state: String = "idle"
var _pending_transcript: String = ""
var _selected_audio_path: String = ""
var _record_bus_index: int = -1
var _record_sink_bus_index: int = -1
var _record_effect: AudioEffectRecord
var _mic_player: AudioStreamPlayer
var _suggestions: Array[String] = []

func _ready() -> void:
    bridge_client.bootstrap_loaded.connect(_on_bootstrap_loaded)
    bridge_client.command_completed.connect(_on_command_completed)
    bridge_client.bridge_error.connect(_on_bridge_error)
    stt_client.transcript_ready.connect(_on_transcript_ready)
    stt_client.stt_error.connect(_on_stt_error)
    tts_client.speech_ready.connect(_on_tts_speech_ready)
    tts_client.tts_error.connect(_on_tts_error)
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
    audio_file_dialog.file_selected.connect(_on_audio_file_selected)
    _set_controls_enabled(false)
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
    command_input.grab_focus()

func _on_command_completed(payload: Dictionary) -> void:
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
    status_label.text = message
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
    _update_voice_ui()
    stt_client.transcribe_audio_file(_selected_audio_path, command_input.text.strip_edges())

func _on_audio_file_selected(path: String) -> void:
    _selected_audio_path = path
    audio_file_label.text = "Audio File: %s" % path.get_file()
    status_label.text = "Audio file ready"
    _update_voice_ui()

func _on_transcript_ready(payload: Dictionary) -> void:
    _pending_transcript = str(payload.get("transcript", "")).strip_edges()
    if _pending_transcript == "":
        status_label.text = "STT returned an empty transcript"
        _voice_state = "idle"
        _update_voice_ui()
        return
    command_input.text = _pending_transcript
    _voice_state = "ready"
    _update_voice_ui()
    status_label.text = "Transcript ready"

func _on_stt_error(message: String) -> void:
    status_label.text = message
    _voice_state = "error"
    _update_voice_ui()

func _on_tts_speech_ready(_spoken_text: String) -> void:
    pass

func _on_tts_error(message: String) -> void:
    status_label.text = "TTS unavailable: %s" % message

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
    target_label.text = "Target: resolving"
    bridge_client.send_command(command_text, transcript)
    _voice_state = "submitting"
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

    _pending_transcript = ""
    _record_effect.set_recording_active(true)
    _mic_player.play()
    _voice_state = "listening"
    status_label.text = "Recording microphone input..."
    _update_voice_ui()

func _stop_microphone_capture() -> void:
    if _record_effect == null or not is_instance_valid(_mic_player):
        _voice_state = "error"
        status_label.text = "Microphone capture is not ready"
        _update_voice_ui()
        return

    _voice_state = "transcribing"
    status_label.text = "Finalizing microphone audio..."
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
    audio_file_label.text = "Audio File: %s" % _selected_audio_path.get_file()
    _update_voice_ui()
    stt_client.transcribe_audio_file(_selected_audio_path)

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
