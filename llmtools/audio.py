import os
import tempfile
import wave

from llmtools import config
from llmtools.core import resolve_safe_path, tool

_AUDIO_DEPS_MSG = "Error: install audio deps (pip install -r requirements-audio.txt)."

# Cached faster-whisper model (loaded once, reused).
_whisper_model = None


def _get_whisper():
    global _whisper_model
    if _whisper_model is None:
        from faster_whisper import WhisperModel

        _whisper_model = WhisperModel(
            config.WHISPER_MODEL, device=config.WHISPER_DEVICE, compute_type=config.WHISPER_COMPUTE
        )
    return _whisper_model


def _transcribe_file(abs_path, language):
    model = _get_whisper()
    kwargs = {"language": language} if language else {}
    segments, _ = model.transcribe(abs_path, **kwargs)
    text = " ".join(s.text.strip() for s in segments).strip()
    return text or "(no speech detected)"


# --------------------------------------------------------------------------- #
# STT — speech to text
# --------------------------------------------------------------------------- #
@tool
def transcribe_audio(path: str, language: str = "") -> str:
    """Transcribe an audio file to text using faster-whisper.

    Args:
        path: Audio file path (wav/mp3/m4a/ogg/flac...).
        language: Force a language code like 'es' or 'en' (empty = auto-detect).
    """
    ap = resolve_safe_path(path)
    try:
        return _transcribe_file(ap, language)
    except ImportError:
        return _AUDIO_DEPS_MSG


@tool
def record_and_transcribe(seconds: int = 5, language: str = "") -> str:
    """Record from the default microphone for N seconds, then transcribe it.

    Args:
        seconds: Recording duration in seconds.
        language: Language code like 'es' (empty = auto-detect).
    """
    try:
        import sounddevice as sd
        import soundfile as sf
    except ImportError:
        return _AUDIO_DEPS_MSG
    sr = 16000
    rec = sd.rec(int(seconds * sr), samplerate=sr, channels=1)
    sd.wait()
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp.close()
    try:
        sf.write(tmp.name, rec, sr)
        try:
            return _transcribe_file(tmp.name, language)
        except ImportError:
            return _AUDIO_DEPS_MSG
    finally:
        os.unlink(tmp.name)


# --------------------------------------------------------------------------- #
# TTS — text to speech (Piper)
# --------------------------------------------------------------------------- #
@tool
def speak_text(text: str, out_path: str = "output.wav", voice: str = "") -> str:
    """Synthesize speech from text using Piper, saving a WAV file.

    Args:
        text: Text to speak.
        out_path: Output WAV file path.
        voice: Path to a Piper voice .onnx model (empty = config.PIPER_VOICE).
    """
    out = resolve_safe_path(out_path)
    model_path = voice or config.PIPER_VOICE
    if not model_path:
        return "Error: set config.PIPER_VOICE (path to a Piper .onnx voice model)."

    # Prefer the Python API; fall back to the piper CLI binary.
    try:
        from piper import PiperVoice

        v = PiperVoice.load(model_path)
        with wave.open(out, "wb") as wf:
            v.synthesize(text, wf)
        return f"Wrote speech to {out}"
    except Exception:
        pass

    import shutil
    import subprocess

    if shutil.which(config.PIPER_BIN) is None:
        return "Error: install 'piper-tts' (pip) or the piper binary."
    r = subprocess.run(
        [config.PIPER_BIN, "-m", model_path, "-f", out], input=text.encode(), capture_output=True
    )
    if r.returncode != 0:
        return f"Piper error: {r.stderr.decode(errors='replace')[:200]}"
    return f"Wrote speech to {out}"


@tool
def list_tts_voices() -> str:
    """List available Piper voice models (.onnx) in the voices directory."""
    d = config.PIPER_VOICES_DIR
    if not os.path.isdir(d):
        return f"Voices dir not found: {d} (set PIPER_VOICES_DIR)."
    voices = [f for f in sorted(os.listdir(d)) if f.endswith(".onnx")]
    return "\n".join(voices) if voices else "(no .onnx voices found)"


@tool
def play_audio(path: str) -> str:
    """Play an audio file through the default speaker.

    Args:
        path: Audio file path.
    """
    try:
        import sounddevice as sd
        import soundfile as sf
    except ImportError:
        return _AUDIO_DEPS_MSG
    ap = resolve_safe_path(path)
    data, sr = sf.read(ap)
    sd.play(data, sr)
    sd.wait()
    return f"Played {ap}"
