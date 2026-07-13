"""Text injection: put text on the clipboard, synthesize Cmd+V, restore the clipboard."""

import time

from AppKit import NSPasteboard, NSPasteboardTypeString, NSWorkspace
from Quartz import (
    CGEventCreateKeyboardEvent,
    CGEventPost,
    CGEventSetFlags,
    kCGEventFlagMaskCommand,
    kCGHIDEventTap,
)

_KEY_V = 9  # kVK_ANSI_V


def frontmost_app() -> str | None:
    app = NSWorkspace.sharedWorkspace().frontmostApplication()
    return str(app.localizedName()) if app else None


def _read_clipboard() -> str | None:
    return NSPasteboard.generalPasteboard().stringForType_(NSPasteboardTypeString)


def _write_clipboard(text: str) -> None:
    pb = NSPasteboard.generalPasteboard()
    pb.clearContents()
    pb.setString_forType_(text, NSPasteboardTypeString)


def _press_cmd_v() -> None:
    for down in (True, False):
        event = CGEventCreateKeyboardEvent(None, _KEY_V, down)
        CGEventSetFlags(event, kCGEventFlagMaskCommand)
        CGEventPost(kCGHIDEventTap, event)


def paste_text(text: str, restore_clipboard: bool = True) -> None:
    if not text:
        return
    previous = _read_clipboard() if restore_clipboard else None
    _write_clipboard(text)
    time.sleep(0.05)  # let the pasteboard settle before the app reads it
    _press_cmd_v()
    if restore_clipboard and previous is not None:
        time.sleep(0.25)  # the paste target reads the clipboard asynchronously
        _write_clipboard(previous)
