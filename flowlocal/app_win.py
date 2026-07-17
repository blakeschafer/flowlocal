"""FlowLocal Windows app: system-tray icon + tk-hosted overlay.

Mirrors the macOS app: hotkey -> recorder -> whisper -> cleanup -> paste.
The (hidden) tk root runs on the main thread and hosts the overlay; the
pystray icon runs on its own thread.
"""

import sys
import threading
import tkinter as tk

import pystray
from PIL import Image, ImageDraw

from . import cleanup, config
from . import paster_win as paster
from .hotkey import HotkeyListener
from .overlay_win import Overlay
from .recorder import Recorder
from .transcriber import Transcriber

_STATE_COLORS = {
    "loading": "#8a8a8a",
    "idle": "#e8e8e8",
    "recording": "#ff453a",
    "busy": "#ffd60a",
}


def _mic_image(color: str) -> Image.Image:
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([24, 6, 40, 36], radius=8, fill=color)
    d.arc([14, 18, 50, 50], start=0, end=180, fill=color, width=5)
    d.line([32, 50, 32, 58], fill=color, width=5)
    d.line([20, 58, 44, 58], fill=color, width=5)
    return img


class FlowLocalApp:
    def __init__(self, root: tk.Tk):
        self._root = root
        self.cfg = config.load()
        self.recorder = Recorder()
        self.overlay = Overlay(root)
        self.recorder.on_level = self.overlay.push_level
        self.transcriber = Transcriber(self.cfg["model"], self.cfg["language"])
        self.model_ready = False
        self._stopping = threading.Event()

        self.icon = pystray.Icon(
            "FlowLocal",
            icon=_mic_image(_STATE_COLORS["loading"]),
            title="FlowLocal — loading model…",
            menu=pystray.Menu(
                pystray.MenuItem(f"Model: {self.cfg['model'].split('/')[-1]}",
                                 None, enabled=False),
                pystray.MenuItem(
                    f"Hotkey: hold {self.cfg['hotkey']} · double-tap for hands-free",
                    None, enabled=False),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("AI Cleanup (Ollama)", self._toggle_cleanup,
                                 checked=lambda item: bool(self.cfg["cleanup"]["enabled"])),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Quit FlowLocal", self._quit),
            ),
        )

        self.hotkey = HotkeyListener(
            self.cfg["hotkey"],
            on_start=self.start_recording,
            on_finish=self.finish_recording,
            on_abort=self.abort_recording,
        )
        self.hotkey.start()
        threading.Thread(target=self.icon.run, daemon=True).start()
        threading.Thread(target=self._warm_up, daemon=True).start()
        self._watch_stop()

    # -- helpers --------------------------------------------------------------

    def _set_state(self, state: str, tooltip: str) -> None:
        self.icon.icon = _mic_image(_STATE_COLORS[state])
        self.icon.title = tooltip

    def _warm_up(self) -> None:
        if self.cfg["cleanup"]["enabled"]:
            threading.Thread(
                target=cleanup.warm_up, args=(self.cfg["cleanup"],), daemon=True
            ).start()
        try:
            self.transcriber.warm_up()
            self.model_ready = True
            self._set_state("idle", "FlowLocal — ready")
        except Exception as exc:  # model download/load failure is fatal for usefulness
            self._set_state("loading", f"FlowLocal — model failed: {exc}")
            print(f"FlowLocal: failed to load whisper model: {exc}", file=sys.stderr)

    def _watch_stop(self) -> None:
        # tk isn't thread-safe, so Quit (from the tray thread) sets an event
        # that the tk thread polls.
        if self._stopping.is_set():
            self._root.destroy()
            return
        self._root.after(200, self._watch_stop)

    # -- dictation flow -------------------------------------------------------

    def start_recording(self) -> None:
        if not self.model_ready:
            return
        self.recorder.start()
        self.overlay.show_recording()
        self._set_state("recording", "FlowLocal — recording")

    def abort_recording(self) -> None:
        self.recorder.abort()
        self.overlay.hide()
        self._set_state("idle", "FlowLocal — ready")

    def finish_recording(self) -> None:
        audio = self.recorder.stop()
        self.overlay.show_processing()
        self._set_state("busy", "FlowLocal — transcribing")
        threading.Thread(target=self._process, args=(audio,), daemon=True).start()

    def _process(self, audio) -> None:
        try:
            app_name = paster.frontmost_app()
            text = self.transcriber.transcribe(audio)
            if text:
                text = cleanup.clean(text, self.cfg["cleanup"], app_name)
            if text:
                paster.paste_text(text)
        except Exception as exc:
            print(f"FlowLocal: dictation failed: {exc}", file=sys.stderr)
        finally:
            self.overlay.hide()
            self._set_state("idle", "FlowLocal — ready")

    # -- menu -----------------------------------------------------------------

    def _toggle_cleanup(self, icon, item) -> None:
        self.cfg["cleanup"]["enabled"] = not self.cfg["cleanup"]["enabled"]
        config.save(self.cfg)

    def _quit(self, icon, item) -> None:
        self.hotkey.stop()
        self.icon.stop()
        self._stopping.set()


def main() -> None:
    root = tk.Tk()
    root.withdraw()
    FlowLocalApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
