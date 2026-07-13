"""User config, stored at ~/.flowlocal/config.json."""

import json
from pathlib import Path

CONFIG_DIR = Path.home() / ".flowlocal"
CONFIG_PATH = CONFIG_DIR / "config.json"

DEFAULTS = {
    # pynput key name: "alt_r" = right Option. Also accepts "cmd_r", "ctrl_r", "f13", etc.
    "hotkey": "alt_r",
    # Any mlx-community whisper repo. large-v3-turbo is the best speed/accuracy on M-series.
    "model": "mlx-community/whisper-large-v3-turbo",
    # None = autodetect. Set to "en" to lock language and speed up decoding.
    "language": None,
    "cleanup": {
        "enabled": True,
        "ollama_url": "http://localhost:11434",
        "ollama_model": "llama3.2:3b",
        "timeout_s": 15,
        # Adjust tone based on the frontmost app (Slack casual, Mail formal, ...)
        "per_app_tone": True,
    },
}


def _merge(base: dict, override: dict) -> dict:
    out = dict(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def load() -> dict:
    if CONFIG_PATH.exists():
        try:
            return _merge(DEFAULTS, json.loads(CONFIG_PATH.read_text()))
        except (json.JSONDecodeError, OSError):
            pass
    return dict(DEFAULTS)


def save(cfg: dict) -> None:
    CONFIG_DIR.mkdir(exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2) + "\n")
