"""Microphone capture. Records 16 kHz mono float32, which Whisper consumes directly."""

import threading

import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16_000


class Recorder:
    def __init__(self):
        self._chunks: list[np.ndarray] = []
        self._stream: sd.InputStream | None = None
        self._lock = threading.Lock()
        # Optional callback fed the RMS level of each chunk (for UI meters).
        self.on_level = None

    @property
    def recording(self) -> bool:
        return self._stream is not None

    def start(self) -> None:
        with self._lock:
            if self._stream is not None:
                return
            self._chunks = []
            self._stream = sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype="float32",
                blocksize=800,  # 50ms chunks -> 20 level updates/s for the UI meter
                callback=self._on_audio,
            )
            self._stream.start()

    def _on_audio(self, indata, frames, time_info, status) -> None:
        chunk = indata[:, 0].copy()
        self._chunks.append(chunk)
        if self.on_level is not None:
            self.on_level(float(np.sqrt(np.mean(chunk**2))))

    def stop(self) -> np.ndarray:
        """Stop capture and return the recorded audio as 1-D float32."""
        with self._lock:
            if self._stream is None:
                return np.zeros(0, dtype=np.float32)
            self._stream.stop()
            self._stream.close()
            self._stream = None
            if not self._chunks:
                return np.zeros(0, dtype=np.float32)
            return np.concatenate(self._chunks)

    def abort(self) -> None:
        self.stop()
