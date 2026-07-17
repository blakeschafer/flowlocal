"""Bottom-of-screen recording pill for Windows (tkinter).

Same look as the macOS overlay: a dark pill with a live waveform while
recording, dots while transcribing. tkinter is not thread-safe, so public
methods enqueue commands that the tk main loop drains every 30ms; the app
owns the (hidden) tk root and its mainloop.
"""

import queue
import tkinter as tk
from collections import deque

WIDTH, HEIGHT = 172, 36
BAR_COUNT = 15
BAR_WIDTH, BAR_GAP = 3, 4
BAR_MIN, BAR_MAX = 3, 20
BOTTOM_MARGIN = 60  # clears the taskbar

_PILL = "#1d1d20"
_CHROMA = "#010203"  # rendered transparent so the pill has rounded corners
_POLL_MS = 30


class Overlay:
    def __init__(self, root: tk.Tk):
        self._root = root
        self._queue: queue.Queue = queue.Queue()
        self._levels = deque([0.0] * BAR_COUNT, maxlen=BAR_COUNT)
        self._mode = "hidden"

        win = tk.Toplevel(root)
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        win.configure(bg=_CHROMA)
        try:
            win.attributes("-transparentcolor", _CHROMA)
        except tk.TclError:
            pass  # non-Windows tk: square corners, still functional
        sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
        win.geometry(f"{WIDTH}x{HEIGHT}+{(sw - WIDTH) // 2}+{sh - HEIGHT - BOTTOM_MARGIN}")
        win.withdraw()

        self._canvas = tk.Canvas(
            win, width=WIDTH, height=HEIGHT, bg=_CHROMA, highlightthickness=0)
        self._canvas.pack()
        self._win = win
        self._root.after(_POLL_MS, self._poll)

    # -- thread-safe API ------------------------------------------------------

    def show_recording(self) -> None:
        self._queue.put(("record", None))

    def show_processing(self) -> None:
        self._queue.put(("process", None))

    def hide(self) -> None:
        self._queue.put(("hide", None))

    def push_level(self, rms: float) -> None:
        """Feed a mic level sample (called from the audio thread)."""
        self._queue.put(("level", min(1.0, rms * 18.0)))

    # -- tk thread ------------------------------------------------------------

    def _poll(self) -> None:
        try:
            while True:
                cmd, arg = self._queue.get_nowait()
                if cmd == "record":
                    self._mode = "record"
                    self._levels.extend([0.0] * BAR_COUNT)
                    self._redraw()
                    self._win.deiconify()
                    self._win.attributes("-topmost", True)
                elif cmd == "process":
                    self._mode = "process"
                    self._redraw()
                    self._win.deiconify()
                elif cmd == "hide":
                    self._mode = "hidden"
                    self._win.withdraw()
                elif cmd == "level" and self._mode == "record":
                    self._levels.append(arg)
                    self._redraw()
        except queue.Empty:
            pass
        self._root.after(_POLL_MS, self._poll)

    def _redraw(self) -> None:
        c = self._canvas
        c.delete("all")
        r = HEIGHT / 2
        c.create_oval(0, 0, HEIGHT, HEIGHT, fill=_PILL, outline=_PILL)
        c.create_oval(WIDTH - HEIGHT, 0, WIDTH, HEIGHT, fill=_PILL, outline=_PILL)
        c.create_rectangle(r, 0, WIDTH - r, HEIGHT, fill=_PILL, outline=_PILL)
        if self._mode == "process":
            c.create_text(WIDTH / 2, HEIGHT / 2, text="• • •",
                          fill="#d9d9d9", font=("Segoe UI", 10))
            return
        total = BAR_COUNT * BAR_WIDTH + (BAR_COUNT - 1) * BAR_GAP
        x = (WIDTH - total) / 2
        for lvl in self._levels:
            h = BAR_MIN + lvl * (BAR_MAX - BAR_MIN)
            c.create_rectangle(x, (HEIGHT - h) / 2, x + BAR_WIDTH, (HEIGHT + h) / 2,
                               fill="white", outline="white")
            x += BAR_WIDTH + BAR_GAP
