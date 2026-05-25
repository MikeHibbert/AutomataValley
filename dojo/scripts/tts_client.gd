extends Node
class_name TtsClient

signal speech_ready(spoken_text)
signal tts_error(message)

@export var tts_base_url: String = "http://127.0.0.1:8004"

var _voice_id: String = ""

func _ready() -> void:
    _voice_id = _select_voice_id()

func configure(base_url: String) -> void:
    if base_url != "":
        tts_base_url = base_url

func speak_text(text: String) -> void:
    var cleaned := text.strip_edges()
    if cleaned == "":
        return

    if _voice_id == "":
        _voice_id = _select_voice_id()

    if _voice_id == "":
        tts_error.emit("No system TTS voice is available in Godot.")
        return

    DisplayServer.tts_stop()
    DisplayServer.tts_speak(cleaned, _voice_id)
    speech_ready.emit(cleaned)

func _select_voice_id() -> String:
    var english_voices: PackedStringArray = DisplayServer.tts_get_voices_for_language("en")
    if not english_voices.is_empty():
        return english_voices[0]

    var available_voices: PackedStringArray = DisplayServer.tts_get_voices()
    if not available_voices.is_empty():
        return available_voices[0]

    return ""
