"""Bottom-of-screen recording pill, Wispr Flow style.

A borderless, non-activating panel (never steals focus from the app being
dictated into) showing a live waveform while recording and dots while
transcribing. All AppKit calls are marshalled onto the main thread.
"""

import warnings
from collections import deque

import objc

# pyobjc can't type CGColorRef precisely; the pointers it warns about are fine.
warnings.filterwarnings("ignore", category=objc.ObjCPointerWarning)

from AppKit import (
    NSBackingStoreBuffered,
    NSColor,
    NSFont,
    NSMakeRect,
    NSOperationQueue,
    NSPanel,
    NSScreen,
    NSStatusWindowLevel,
    NSTextAlignmentCenter,
    NSTextField,
    NSView,
    NSWindowCollectionBehaviorCanJoinAllSpaces,
    NSWindowCollectionBehaviorFullScreenAuxiliary,
    NSWindowCollectionBehaviorStationary,
    NSWindowStyleMaskBorderless,
    NSWindowStyleMaskNonactivatingPanel,
)

WIDTH, HEIGHT = 172, 36
BAR_COUNT = 15
BAR_WIDTH, BAR_GAP = 3.0, 4.5
BAR_MIN, BAR_MAX = 3.0, 20.0
BOTTOM_MARGIN = 28


def _on_main(fn):
    NSOperationQueue.mainQueue().addOperationWithBlock_(fn)


class Overlay:
    def __init__(self):
        self._panel = None
        self._bars: list = []
        self._label = None
        self._levels = deque([0.0] * BAR_COUNT, maxlen=BAR_COUNT)

    # -- construction (main thread only) -------------------------------------

    def _ensure_panel(self) -> None:
        if self._panel is not None:
            return
        panel = NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(0, 0, WIDTH, HEIGHT),
            NSWindowStyleMaskBorderless | NSWindowStyleMaskNonactivatingPanel,
            NSBackingStoreBuffered,
            False,
        )
        panel.setLevel_(NSStatusWindowLevel)
        panel.setOpaque_(False)
        panel.setBackgroundColor_(NSColor.clearColor())
        panel.setIgnoresMouseEvents_(True)
        panel.setHasShadow_(True)
        panel.setCollectionBehavior_(
            NSWindowCollectionBehaviorCanJoinAllSpaces
            | NSWindowCollectionBehaviorStationary
            | NSWindowCollectionBehaviorFullScreenAuxiliary
        )

        content = NSView.alloc().initWithFrame_(NSMakeRect(0, 0, WIDTH, HEIGHT))
        content.setWantsLayer_(True)
        content.layer().setBackgroundColor_(
            NSColor.colorWithCalibratedWhite_alpha_(0.07, 0.93).CGColor())
        content.layer().setCornerRadius_(HEIGHT / 2)
        panel.setContentView_(content)

        total = BAR_COUNT * BAR_WIDTH + (BAR_COUNT - 1) * BAR_GAP
        x0 = (WIDTH - total) / 2
        for i in range(BAR_COUNT):
            bar = NSView.alloc().initWithFrame_(
                NSMakeRect(x0 + i * (BAR_WIDTH + BAR_GAP),
                           (HEIGHT - BAR_MIN) / 2, BAR_WIDTH, BAR_MIN))
            bar.setWantsLayer_(True)
            bar.layer().setBackgroundColor_(NSColor.whiteColor().CGColor())
            bar.layer().setCornerRadius_(BAR_WIDTH / 2)
            content.addSubview_(bar)
            self._bars.append(bar)

        label = NSTextField.labelWithString_("")
        label.setFrame_(NSMakeRect(0, (HEIGHT - 18) / 2 - 1, WIDTH, 18))
        label.setAlignment_(NSTextAlignmentCenter)
        label.setFont_(NSFont.systemFontOfSize_(13))
        label.setTextColor_(NSColor.colorWithCalibratedWhite_alpha_(1.0, 0.85))
        content.addSubview_(label)
        self._label = label
        self._panel = panel

    def _position(self) -> None:
        screen = NSScreen.mainScreen()
        if screen is None:
            return
        vf = screen.visibleFrame()
        self._panel.setFrameOrigin_((
            vf.origin.x + (vf.size.width - WIDTH) / 2,
            vf.origin.y + BOTTOM_MARGIN,
        ))

    # -- state changes (safe from any thread) ---------------------------------

    def show_recording(self) -> None:
        def apply():
            self._ensure_panel()
            self._levels.extend([0.0] * BAR_COUNT)
            self._redraw_bars()
            for bar in self._bars:
                bar.setHidden_(False)
            self._label.setStringValue_("")
            self._position()
            self._panel.orderFrontRegardless()
        _on_main(apply)

    def show_processing(self) -> None:
        def apply():
            self._ensure_panel()
            for bar in self._bars:
                bar.setHidden_(True)
            self._label.setStringValue_("• • •")
            self._position()
            self._panel.orderFrontRegardless()
        _on_main(apply)

    def hide(self) -> None:
        def apply():
            if self._panel is not None:
                self._panel.orderOut_(None)
        _on_main(apply)

    def push_level(self, rms: float) -> None:
        """Feed a mic level sample (called from the audio thread)."""
        level = min(1.0, rms * 18.0)
        def apply():
            if self._panel is None or self._panel.isVisible() is False:
                return
            self._levels.append(level)
            self._redraw_bars()
        _on_main(apply)

    def _redraw_bars(self) -> None:
        for bar, lvl in zip(self._bars, self._levels):
            h = BAR_MIN + lvl * (BAR_MAX - BAR_MIN)
            frame = bar.frame()
            frame.origin.y = (HEIGHT - h) / 2
            frame.size.height = h
            bar.setFrame_(frame)
