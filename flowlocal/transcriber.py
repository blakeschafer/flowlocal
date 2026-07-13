"""On-device speech-to-text via mlx-whisper (Apple Silicon GPU)."""

import numpy as np

import mlx_whisper

from .recorder import SAMPLE_RATE

MIN_DURATION_S = 0.3
MIN_RMS = 0.003  # below this the clip is effectively silence

# Whisper hallucinates these on (near-)silent audio; drop them when they are the whole output.
_SILENCE_ARTIFACTS = {
    "you", "thank you.", "thank you", "thanks for watching!", "thank you for watching!",
    "bye.", "bye", "the end.", ".",
}


class Transcriber:
    def __init__(self, model_repo: str, language: str | None = None):
        self.model_repo = model_repo
        self.language = language

    def warm_up(self) -> None:
        """Load the model into memory so the first real dictation is fast."""
        self.transcribe(np.zeros(SAMPLE_RATE, dtype=np.float32), _skip_gates=True)

    def transcribe(self, audio: np.ndarray, _skip_gates: bool = False) -> str:
        if not _skip_gates:
            if audio.size < MIN_DURATION_S * SAMPLE_RATE:
                return ""
            if float(np.sqrt(np.mean(audio**2))) < MIN_RMS:
                return ""
        result = mlx_whisper.transcribe(
            audio,
            path_or_hf_repo=self.model_repo,
            language=self.language,
            fp16=True,
        )
        text = result["text"].strip()
        if not _skip_gates and text.lower() in _SILENCE_ARTIFACTS:
            return ""
        return text
