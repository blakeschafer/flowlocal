"""Regression test for the pill overlay startup race: the panel used to be
built lazily on the first show_recording() call, which could race a short
first dictation and never get composited (see overlay.py warm_up())."""

import sys
import time

import pytest

pytestmark = pytest.mark.skipif(sys.platform != "darwin", reason="AppKit-only")


def _pump(seconds: float) -> None:
    from Foundation import NSDate, NSRunLoop
    end = time.time() + seconds
    while time.time() < end:
        NSRunLoop.currentRunLoop().runUntilDate_(NSDate.dateWithTimeIntervalSinceNow_(0.01))


@pytest.fixture(scope="module", autouse=True)
def _nsapp():
    from AppKit import NSApplication
    NSApplication.sharedApplication()


def test_warm_up_builds_the_panel_ahead_of_any_recording():
    from flowlocal.overlay import Overlay
    ov = Overlay()
    assert ov._panel is None
    ov.warm_up()
    _pump(0.2)
    assert ov._panel is not None


def test_show_and_hide_toggle_visibility():
    from flowlocal.overlay import Overlay
    ov = Overlay()
    ov.warm_up()
    _pump(0.2)
    ov.show_recording()
    _pump(0.2)
    assert ov._panel.isVisible()
    ov.hide()
    _pump(0.2)
    assert not ov._panel.isVisible()


def test_fast_hold_right_after_warm_up_is_still_visible():
    """The exact bug reported: a quick dictation immediately after launch.
    With the panel already built by warm_up(), even a ~50ms hold must
    still get composited before anything can hide it again."""
    from flowlocal.overlay import Overlay
    ov = Overlay()
    ov.warm_up()
    _pump(0.2)  # mirrors the real app: warm_up() completes well before
                # model_ready flips true and a recording can start
    ov.show_recording()
    _pump(0.05)
    assert ov._panel.isVisible()
