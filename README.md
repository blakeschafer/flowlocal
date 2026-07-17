# FlowLocal 🎙

Private, on-device voice dictation for macOS. Hold a hotkey, speak, release — polished text lands in whatever app you're in.

A local, open-source alternative to Wispr Flow: **zero network calls, zero subscription, free forever**. Your voice never leaves your Mac.

## How it works

```
hold hotkey → mic capture → Whisper (MLX, on-GPU) → LLM cleanup (Ollama, local)
                                                       → paste into frontmost app
```

- **Transcription:** `whisper-large-v3-turbo` via [mlx-whisper](https://github.com/ml-explore/mlx-examples) — runs on the Apple Silicon GPU, ~0.5s for a typical utterance.
- **Cleanup:** `llama3.2:3b` via [Ollama](https://ollama.com) strips fillers ("um", "uh"), fixes punctuation, applies spoken self-corrections ("no wait, actually Friday" → "Friday"), and adapts tone to the frontmost app (formal in Mail, casual in Slack, verbatim-technical in editors/terminals). If Ollama isn't running, a regex fallback strips fillers so dictation always works.
- **Injection:** text is pasted via a synthesized ⌘V; your previous clipboard is restored afterward.
- **UI:** a Wispr-style pill at the bottom of the screen shows a live waveform while you speak.

The only network access, ever, is the one-time model download.

## Requirements

- Apple Silicon Mac (M1 or later — MLX runs on the Apple GPU)
- [uv](https://docs.astral.sh/uv/) (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- [Ollama](https://ollama.com) — optional, for AI cleanup (`brew install ollama && brew services start ollama`)

## Install

```bash
git clone https://github.com/blakeschafer/flowlocal.git
cd flowlocal
./scripts/install.sh
```

The installer sets up the Python environment, pulls the cleanup model if Ollama is present, and registers a LaunchAgent so FlowLocal **starts at every login and restarts if it crashes** — install once, never think about it again.

A 🎙 appears in the menu bar (⏳ while the Whisper model downloads — first run only, ~1.6GB).

### One-time permissions

macOS will ask for three permissions (System Settings → Privacy & Security):

1. **Microphone** — allow when prompted on first dictation
2. **Input Monitoring** — add the Python binary FlowLocal runs under
3. **Accessibility** — same binary (needed to synthesize the ⌘V paste)

The binary to grant is the target of `readlink -f .venv/bin/python3`. After granting, restart FlowLocal: `launchctl kickstart -k gui/$(id -u)/com.flowlocal`.

> Prefer to run it manually instead of always-on? Skip the installer and use `uv sync && uv run flowlocal`.

## Usage

| Action | Gesture |
|---|---|
| Dictate | **Hold Right-Option**, speak, release |
| Hands-free | **Double-tap Right-Option**, speak freely, tap once to finish |
| Toggle AI cleanup | Menu bar → "AI Cleanup (Ollama)" |

Menu bar states: 🎙 idle · 🔴 recording · ✍️ transcribing · ⚠️ model failed to load.

## Configuration

`~/.flowlocal/config.json` (created on first settings change; all keys optional):

```json
{
  "hotkey": "alt_r",
  "model": "mlx-community/whisper-large-v3-turbo",
  "language": null,
  "cleanup": {
    "enabled": true,
    "ollama_model": "llama3.2:3b",
    "per_app_tone": true
  }
}
```

- `hotkey`: any [pynput key name](https://pynput.readthedocs.io/en/latest/keyboard.html#pynput.keyboard.Key) — `alt_r`, `cmd_r`, `f13`…
- `model`: any mlx-community Whisper repo; `whisper-small` is faster, `large-v3-turbo` more accurate.
- `language`: `"en"` locks English and speeds decoding; `null` autodetects.

After changing config, restart: `launchctl kickstart -k gui/$(id -u)/com.flowlocal`.

## Uninstall

```bash
./scripts/uninstall.sh   # stops the service and removes the LaunchAgent
```

## Development

```bash
uv run pytest    # includes a real end-to-end Whisper test using macOS `say`
```

Logs live at `/tmp/flowlocal.log` and `/tmp/flowlocal.err`.

## License

[MIT](LICENSE)
