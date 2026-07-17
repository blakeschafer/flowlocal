"""On-device speech-to-text.

macOS: mlx-whisper on the Apple Silicon GPU.
Windows: faster-whisper on an NVIDIA GPU when available, else quantized CPU.
"""

import sys

import numpy as np

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
        self._fw_model = None  # faster-whisper model, loaded lazily

    def warm_up(self) -> None:
        """Load the model into memory so the first real dictation is fast."""
        self.transcribe(np.zeros(SAMPLE_RATE, dtype=np.float32), _skip_gates=True)

    def _transcribe_raw(self, audio: np.ndarray) -> str:
        if sys.platform == "darwin":
            import mlx_whisper
            result = mlx_whisper.transcribe(
                audio,
                path_or_hf_repo=self.model_repo,
                language=self.language,
                fp16=True,
            )
            return result["text"]

        from faster_whisper import WhisperModel
        if self._fw_model is None:
            try:
                self._fw_model = WhisperModel(
                    self.model_repo, device="cuda", compute_type="float16")
            except Exception:  # no CUDA GPU / CUDA libs — quantized CPU still works
                self._fw_model = WhisperModel(
                    self.model_repo, device="cpu", compute_type="int8")
        segments, _ = self._fw_model.transcribe(audio, language=self.language)
        return "".join(seg.text for seg in segments)

    def transcribe(self, audio: np.ndarray, _skip_gates: bool = False) -> str:
        if not _skip_gates:
            if audio.size < MIN_DURATION_S * SAMPLE_RATE:
                return ""
            if float(np.sqrt(np.mean(audio**2))) < MIN_RMS:
                return ""
        text = self._transcribe_raw(audio).strip()
        if not _skip_gates and text.lower() in _SILENCE_ARTIFACTS:
            return ""
        return text
