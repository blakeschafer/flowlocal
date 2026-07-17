"""Text injection on Windows: clipboard + synthesized Ctrl+V, clipboard restored.

Clipboard access goes through the raw Win32 API (ctypes) to avoid extra
dependencies; the keystroke is synthesized with pynput.
"""

import ctypes
import time

from pynput.keyboard import Controller, Key

_user32 = ctypes.windll.user32
_kernel32 = ctypes.windll.kernel32

# Explicit types: handles/pointers are 64-bit and get truncated without these.
_user32.GetClipboardData.restype = ctypes.c_void_p
_kernel32.GlobalAlloc.restype = ctypes.c_void_p
_kernel32.GlobalLock.restype = ctypes.c_void_p
_kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
_kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
_kernel32.GlobalFree.argtypes = [ctypes.c_void_p]
_user32.SetClipboardData.argtypes = [ctypes.c_uint, ctypes.c_void_p]

CF_UNICODETEXT = 13
GMEM_MOVEABLE = 0x0002

_kb = Controller()


def frontmost_app() -> str | None:
    """Title of the foreground window; usually contains the app name, which is
    all the per-app tone matching needs ("... - Slack", "... - Visual Studio Code")."""
    hwnd = _user32.GetForegroundWindow()
    if not hwnd:
        return None
    length = _user32.GetWindowTextLengthW(hwnd)
    if length == 0:
        return None
    buf = ctypes.create_unicode_buffer(length + 1)
    _user32.GetWindowTextW(hwnd, buf, length + 1)
    return buf.value or None


def _open_clipboard(retries: int = 10) -> bool:
    # Another app may hold the clipboard for a few ms; retry briefly.
    for _ in range(retries):
        if _user32.OpenClipboard(None):
            return True
        time.sleep(0.01)
    return False


def _read_clipboard() -> str | None:
    if not _open_clipboard():
        return None
    try:
        handle = _user32.GetClipboardData(CF_UNICODETEXT)
        if not handle:
            return None
        ptr = _kernel32.GlobalLock(handle)
        if not ptr:
            return None
        try:
            return ctypes.wstring_at(ptr)
        finally:
            _kernel32.GlobalUnlock(handle)
    finally:
        _user32.CloseClipboard()


def _write_clipboard(text: str) -> None:
    data = text.encode("utf-16-le") + b"\x00\x00"
    handle = _kernel32.GlobalAlloc(GMEM_MOVEABLE, len(data))
    if not handle:
        return
    ptr = _kernel32.GlobalLock(handle)
    ctypes.memmove(ptr, data, len(data))
    _kernel32.GlobalUnlock(handle)
    if not _open_clipboard():
        _kernel32.GlobalFree(handle)
        return
    try:
        _user32.EmptyClipboard()
        # On success the system owns the handle; do not free it.
        if not _user32.SetClipboardData(CF_UNICODETEXT, handle):
            _kernel32.GlobalFree(handle)
    finally:
        _user32.CloseClipboard()


def _press_ctrl_v() -> None:
    with _kb.pressed(Key.ctrl):
        _kb.press("v")
        _kb.release("v")


def paste_text(text: str, restore_clipboard: bool = True) -> None:
    if not text:
        return
    previous = _read_clipboard() if restore_clipboard else None
    _write_clipboard(text)
    time.sleep(0.05)  # let the clipboard settle before the app reads it
    _press_ctrl_v()
    if restore_clipboard and previous is not None:
        time.sleep(0.25)  # the paste target reads the clipboard asynchronously
        _write_clipboard(previous)
