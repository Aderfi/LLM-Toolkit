import io
import os
import re
import tempfile
import threading
import wave

from .config import get_settings
from .core import resolve_safe_path, tool

_AUDIO_DEPS_MSG = "Error: install audio deps (uv sync --extra audio)."

# Cached faster-whisper model (loaded once, reused).
_whisper_model = None


def _load_cuda12_libs() -> None:
    """ctranslate2 looks up cuBLAS 12 / cuDNN 9 by name; the ``gpu`` extra installs them inside
    the venv (not on LD_LIBRARY_PATH), so they are preloaded by hand before using CUDA."""
    import ctypes
    import importlib.util

    for pkg, libs in (
        ("nvidia.cublas", ("libcublasLt.so.12", "libcublas.so.12")),
        ("nvidia.cudnn", ("libcudnn.so.9",)),
    ):
        spec = importlib.util.find_spec(pkg)
        if spec is None or not spec.submodule_search_locations:
            continue  # no gpu extra: fall back to system libraries, if any
        libdir = os.path.join(spec.submodule_search_locations[0], "lib")
        for lib in libs:
            path = os.path.join(libdir, lib)
            if os.path.exists(path):
                ctypes.CDLL(path, mode=ctypes.RTLD_GLOBAL)


def _get_whisper():
    global _whisper_model
    if _whisper_model is None:
        from faster_whisper import WhisperModel

        s = get_settings()
        if s.whisper_device in ("cuda", "auto"):
            _load_cuda12_libs()

        _whisper_model = WhisperModel(
            s.whisper_model, device=s.whisper_device, compute_type=s.whisper_compute
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
# Cached Piper voices by model path (each loaded once, reused). The lock avoids
# loading the same model twice when two chats synthesize at the same time.
_piper_voices: dict[str, object] = {}
_piper_lock = threading.Lock()


def _get_piper(path: str = ""):
    path = os.path.expanduser(path or get_settings().piper_voice)
    if not path:
        raise ValueError("set PIPER_VOICE (path to a Piper .onnx voice model).")
    with _piper_lock:
        if path not in _piper_voices:
            from piper import PiperVoice

            _piper_voices[path] = PiperVoice.load(path)
        return _piper_voices[path]


def _synthesis_config(voice):
    """SynthesisConfig from PIPER_SPEED / PIPER_SPEAKER (speaker only for multi-speaker voices)."""
    from piper import SynthesisConfig

    s = get_settings()
    speaker = s.piper_speaker if voice.config.num_speakers > 1 else None
    return SynthesisConfig(speaker_id=speaker, length_scale=1 / s.piper_speed)


def available_voices() -> dict[str, str]:
    """Piper voices in PIPER_VOICES_DIR: {name: .onnx path}, e.g. 'es_AR-daniela-high'."""
    d = get_settings().piper_voices_dir
    if not d.is_dir():
        return {}
    return {p.stem: str(p) for p in sorted(d.glob("*.onnx"))}


def preload_voice(path: str = "") -> None:
    """Load a voice ahead of time ('high' voices take a few seconds the first time)."""
    _get_piper(path)


def text_for_speech(md: str, max_chars: int = 1500) -> str:
    """Strip Markdown so Piper does not read symbols, URLs or code blocks aloud."""
    t = re.sub(r"```.*?```", " (code omitted) ", md, flags=re.S)
    t = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", t)  # [text](url) -> text
    t = re.sub(r"https?://\S+", "", t)
    t = re.sub(r"^\s*(?:[-•*]|\d+\.)\s+", "", t, flags=re.M)  # bullets
    t = re.sub(r"[*_`#>|~]", "", t)
    t = re.sub(r"[ \t]+", " ", t).strip()
    if len(t) > max_chars:  # cut at the last sentence end
        cut = t[:max_chars]
        t = cut[: max(cut.rfind(". "), cut.rfind("\n")) + 1] or cut
    return t


def synthesize_ogg(text: str, voice_path: str = "") -> bytes:
    """Text -> OGG/Opus voice note (Piper + PyAV, no ffmpeg needed).

    Empty ``voice_path`` = PIPER_VOICE.
    """
    import av
    import numpy as np

    voice = _get_piper(voice_path)
    buf = io.BytesIO()
    with av.open(buf, "w", format="ogg") as container:
        stream = container.add_stream("libopus", rate=48000, layout="mono")
        # 48 kbps: at 32 kbps compression is audible on "high" voices.
        stream.bit_rate = 48000
        resampler = av.AudioResampler(format="s16", layout="mono", rate=48000)
        for chunk in voice.synthesize(text, syn_config=_synthesis_config(voice)):
            samples = chunk.audio_int16_array.astype(np.int16).reshape(1, -1)
            frame = av.AudioFrame.from_ndarray(samples, format="s16", layout="mono")
            frame.sample_rate = chunk.sample_rate
            for rframe in resampler.resample(frame):
                for packet in stream.encode(rframe):
                    container.mux(packet)
        for rframe in resampler.resample(None):
            for packet in stream.encode(rframe):
                container.mux(packet)
        for packet in stream.encode(None):
            container.mux(packet)
    return buf.getvalue()


@tool
def speak_text(text: str, out_path: str = "output.wav", voice: str = "") -> str:
    """Synthesize speech from text using Piper, saving a WAV file.

    Args:
        text: Text to speak.
        out_path: Output WAV file path.
        voice: Path to a Piper voice .onnx model (empty = PIPER_VOICE setting).
    """
    out = resolve_safe_path(out_path)
    model_path = voice or get_settings().piper_voice
    if not model_path:
        return "Error: set PIPER_VOICE (path to a Piper .onnx voice model)."

    # Prefer the Python API; fall back to the piper CLI binary.
    try:
        v = _get_piper(voice)
        with wave.open(out, "wb") as wf:
            v.synthesize_wav(text, wf, syn_config=_synthesis_config(v))
        return f"Wrote speech to {out}"
    except Exception:
        pass

    import shutil
    import subprocess

    if shutil.which(get_settings().piper_bin) is None:
        return "Error: install 'piper-tts' (pip) or the piper binary."
    r = subprocess.run(
        [get_settings().piper_bin, "-m", model_path, "-f", out],
        input=text.encode(),
        capture_output=True,
    )
    if r.returncode != 0:
        return f"Piper error: {r.stderr.decode(errors='replace')[:200]}"
    return f"Wrote speech to {out}"


@tool
def list_tts_voices() -> str:
    """List available Piper voice models (.onnx) in the voices directory."""
    d = get_settings().piper_voices_dir
    if not d.is_dir():
        return f"Voices dir not found: {d} (set PIPER_VOICES_DIR)."
    voices = available_voices()
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
