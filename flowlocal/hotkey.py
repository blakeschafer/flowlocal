"""Global hotkey: hold to talk, double-tap to lock hands-free.

Hold the key (>0.3s), speak, release -> transcribe.
Double-tap quickly -> hands-free recording until the next tap.
"""

import threading
import time
from collections.abc import Callable

from pynput import keyboard

TAP_MAX_S = 0.3        # press shorter than this counts as a tap
DOUBLE_TAP_MAX_S = 0.5  # two taps within this window lock hands-free


def resolve_key(name: str):
    try:
        return getattr(keyboard.Key, name)
    except AttributeError:
        return keyboard.KeyCode.from_char(name)


class HotkeyListener:
    def __init__(self, key_name: str, on_start: Callable[[], None],
                 on_finish: Callable[[], None], on_abort: Callable[[], None]):
        self._key = resolve_key(key_name)
        self._on_start = on_start      # begin recording
        self._on_finish = on_finish    # stop recording and process
        self._on_abort = on_abort      # stop recording, discard
        self._pressed_at: float | None = None
        self._last_tap_at = 0.0
        self._handsfree = False
        self._abort_timer: threading.Timer | None = None
        self._listener = keyboard.Listener(
            on_press=self._on_press, on_release=self._on_release)

    def start(self) -> None:
        self._listener.start()

    def stop(self) -> None:
        self._listener.stop()

    def _on_press(self, key) -> None:
        if key != self._key or self._pressed_at is not None:
            return
        self._pressed_at = time.monotonic()
        if self._handsfree:
            return  # this press will end the hands-free session on release
        if self._abort_timer:
            self._abort_timer.cancel()
            self._abort_timer = None
        self._on_start()

    def _on_release(self, key) -> None:
        if key != self._key or self._pressed_at is None:
            return
        held = time.monotonic() - self._pressed_at
        self._pressed_at = None

        if self._handsfree:
            self._handsfree = False
            self._on_finish()
            return

        if held >= TAP_MAX_S:  # normal push-to-talk
            self._on_finish()
            return

        # A tap. Second tap within the window locks hands-free (recording is
        # already running since the first tap's press); otherwise wait to see
        # if a second tap arrives, and abort the stub recording if not.
        now = time.monotonic()
        if now - self._last_tap_at <= DOUBLE_TAP_MAX_S:
            self._last_tap_at = 0.0
            self._handsfree = True
            if self._abort_timer:
                self._abort_timer.cancel()
                self._abort_timer = None
            return
        self._last_tap_at = now
        self._abort_timer = threading.Timer(DOUBLE_TAP_MAX_S, self._abort_single_tap)
        self._abort_timer.daemon = True
        self._abort_timer.start()

    def _abort_single_tap(self) -> None:
        self._abort_timer = None
        if not self._handsfree:
            self._on_abort()
