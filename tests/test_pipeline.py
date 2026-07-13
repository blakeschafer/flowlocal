"""Pipeline tests. The transcription test synthesizes speech with macOS `say`,
so it exercises the real Whisper model without a microphone."""

import subprocess
import wave
from pathlib import Path

import numpy as np
import pytest

from flowlocal import cleanup
from flowlocal.config import DEFAULTS
from flowlocal.transcriber import Transcriber


def synth_speech(text: str, tmp_path: Path) -> np.ndarray:
    """Render `text` to 16 kHz mono float32 via the macOS TTS engine."""
    wav = tmp_path / "speech.wav"
    subprocess.run(
        ["say", "-o", str(wav), "--data-format=LEI16@16000", text],
        check=True,
    )
    with wave.open(str(wav)) as f:
        assert f.getframerate() == 16_000
        pcm = np.frombuffer(f.readframes(f.getnframes()), dtype=np.int16)
    return pcm.astype(np.float32) / 32768.0


def test_fallback_clean_strips_fillers():
    raw = "um so like, I think we should uh ship it you know, tomorrow"
    out = cleanup.fallback_clean(raw)
    lowered = out.lower()
    assert "um" not in lowered.split()
    assert "uh" not in lowered.split()
    assert "you know" not in lowered
    assert out[0].isupper()
    assert "ship it" in lowered


def test_fallback_clean_keeps_normal_text():
    raw = "Send the report to Sarah by Friday."
    assert cleanup.fallback_clean(raw) == raw


def test_clean_disabled_uses_fallback():
    cfg = {**DEFAULTS["cleanup"], "enabled": False}
    assert "um" not in cleanup.clean("um hello there", cfg).lower().split()


def test_llm_clean_unreachable_falls_back():
    cfg = {**DEFAULTS["cleanup"], "enabled": True,
           "ollama_url": "http://localhost:1", "timeout_s": 1}
    out = cleanup.clean("uh testing the fallback path", cfg)
    assert "uh" not in out.lower().split()
    assert "testing the fallback path" in out.lower()


def test_tone_hint_selected_for_known_apps():
    assert cleanup._tone_for_app("Slack") is not None
    assert cleanup._tone_for_app("Visual Studio Code") is not None
    assert cleanup._tone_for_app("SomeRandomApp") is None


@pytest.fixture(scope="module")
def transcriber():
    return Transcriber(DEFAULTS["model"], language="en")


def test_silence_returns_empty(transcriber):
    silence = np.zeros(16_000, dtype=np.float32)
    assert transcriber.transcribe(silence) == ""


def test_too_short_returns_empty(transcriber):
    blip = np.random.default_rng(0).normal(0, 0.1, 1000).astype(np.float32)
    assert transcriber.transcribe(blip) == ""


def test_transcribes_synthesized_speech(transcriber, tmp_path):
    audio = synth_speech(
        "The quick brown fox jumps over the lazy dog", tmp_path)
    text = transcriber.transcribe(audio).lower()
    for word in ("quick", "brown", "fox", "lazy", "dog"):
        assert word in text
