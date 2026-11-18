import llmtools
from llmtools import audio


class _Seg:
    def __init__(self, text):
        self.text = text


class _FakeModel:
    def transcribe(self, path, **kwargs):
        return [_Seg("hola "), _Seg("mundo")], None


def test_transcribe_audio(tmp_path, monkeypatch):
    monkeypatch.setattr(audio, "_get_whisper", lambda: _FakeModel())
    p = tmp_path / "a.wav"
    p.write_bytes(b"RIFF0000WAVE")
    out = audio.transcribe_audio(str(p))
    assert "hola" in out and "mundo" in out


def test_transcribe_rejects_outside_root():
    out = llmtools.call_tool("transcribe_audio", {"path": "/etc/hosts"})
    assert "outside allowed roots" in out.lower()


def test_speak_text_requires_voice(tmp_path):
    out = audio.speak_text("hi", str(tmp_path / "o.wav"))
    assert "PIPER_VOICE" in out


def test_list_tts_voices(tmp_path, configure):
    configure(PIPER_VOICES_DIR=str(tmp_path))
    (tmp_path / "es_ES-davefx-medium.onnx").write_text("x")
    assert "es_ES-davefx-medium" in audio.list_tts_voices()
