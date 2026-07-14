"""FlowLocal menu-bar app: ties hotkey -> recorder -> whisper -> cleanup -> paste."""

import sys
import threading

import rumps
from AppKit import NSOperationQueue

from . import cleanup, config, paster
from .hotkey import HotkeyListener
from .overlay import Overlay
from .recorder import Recorder
from .transcriber import Transcriber

ICON_IDLE = "🎙"
ICON_RECORDING = "🔴"
ICON_BUSY = "✍️"
ICON_LOADING = "⏳"


class FlowLocalApp(rumps.App):
    def __init__(self):
        super().__init__("FlowLocal", title=ICON_LOADING, quit_button="Quit FlowLocal")
        self.cfg = config.load()
        self.recorder = Recorder()
        self.overlay = Overlay()
        self.recorder.on_level = self.overlay.push_level
        self.transcriber = Transcriber(self.cfg["model"], self.cfg["language"])
        self.model_ready = False

        self.cleanup_item = rumps.MenuItem("AI Cleanup (Ollama)", callback=self.toggle_cleanup)
        self.cleanup_item.state = bool(self.cfg["cleanup"]["enabled"])
        status = rumps.MenuItem(f"Model: {self.cfg['model'].split('/')[-1]}")
        hotkey_label = rumps.MenuItem(f"Hotkey: hold {self.cfg['hotkey']} · double-tap for hands-free")
        self.menu = [status, hotkey_label, None, self.cleanup_item, None]

        self.hotkey = HotkeyListener(
            self.cfg["hotkey"],
            on_start=self.start_recording,
            on_finish=self.finish_recording,
            on_abort=self.abort_recording,
        )
        self.hotkey.start()
        threading.Thread(target=self._warm_up, daemon=True).start()

    # -- helpers ------------------------------------------------------------

    def _set_title(self, title: str) -> None:
        def apply():
            self.title = title
        NSOperationQueue.mainQueue().addOperationWithBlock_(apply)

    def _warm_up(self) -> None:
        if self.cfg["cleanup"]["enabled"]:
            threading.Thread(
                target=cleanup.warm_up, args=(self.cfg["cleanup"],), daemon=True
            ).start()
        try:
            self.transcriber.warm_up()
            self.model_ready = True
            self._set_title(ICON_IDLE)
        except Exception as exc:  # model download/load failure is fatal for usefulness
            self._set_title("⚠️")
            print(f"FlowLocal: failed to load whisper model: {exc}", file=sys.stderr)

    # -- dictation flow -----------------------------------------------------

    def start_recording(self) -> None:
        if not self.model_ready:
            return
        self.recorder.start()
        self.overlay.show_recording()
        self._set_title(ICON_RECORDING)

    def abort_recording(self) -> None:
        self.recorder.abort()
        self.overlay.hide()
        self._set_title(ICON_IDLE)

    def finish_recording(self) -> None:
        audio = self.recorder.stop()
        self.overlay.show_processing()
        self._set_title(ICON_BUSY)
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
            self._set_title(ICON_IDLE)

    # -- menu ---------------------------------------------------------------

    def toggle_cleanup(self, item) -> None:
        item.state = not item.state
        self.cfg["cleanup"]["enabled"] = bool(item.state)
        config.save(self.cfg)


def main() -> None:
    FlowLocalApp().run()


if __name__ == "__main__":
    main()
