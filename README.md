# FlowLocal

Private, on-device voice dictation for macOS. Hold a hotkey, speak, release — polished text lands in whatever app you're in. A local Wispr Flow: zero network calls, zero subscription, free forever.

## How it works

```
hold hotkey → mic capture → Whisper (MLX, on-GPU) → LLM cleanup (Ollama, local)
                                                        → paste into frontmost app
```

- **Transcription:** `whisper-large-v3-turbo` via [mlx-whisper](https://github.com/ml-explore/mlx-examples) — runs on the Apple Silicon GPU, ~0.5s for a typical utterance.
- **Cleanup:** `llama3.2:3b` via [Ollama](https://ollama.com) strips fillers ("um", "uh"), fixes punctuation, applies spoken self-corrections ("no wait, actually Friday" → "Friday"), and adapts tone to the frontmost app (formal in Mail, casual in Slack, verbatim-technical in VS Code/terminals). If Ollama isn't running, a regex fallback strips fillers so dictation always works.
- **Injection:** text is pasted via a synthesized ⌘V; your previous clipboard is restored afterward.

Everything runs on your machine. The only network access ever is the one-time model download.

## Usage

```bash
cd ~/flowlocal
uv run flowlocal
```

A 🎙 appears in the menu bar (⏳ while the model loads, ~5s).

| Action | Gesture |
|---|---|
| Dictate | **Hold Right-Option**, speak, release |
| Hands-free | **Double-tap Right-Option**, speak freely, tap once to finish |
| Toggle AI cleanup | Menu bar → "AI Cleanup (Ollama)" |

Menu bar states: 🎙 idle · 🔴 recording · ✍️ transcribing · ⚠️ model failed to load.

### First-run permissions

macOS will prompt for (grant to your terminal app, or whatever launches FlowLocal):

1. **Microphone** — record your voice
2. **Input Monitoring** — see the global hotkey
3. **Accessibility** — synthesize the ⌘V paste

System Settings → Privacy & Security if a prompt doesn't appear.

### Ollama (optional but recommended)

```bash
ollama serve          # if not already running
ollama pull llama3.2:3b
```

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

## Start at login (optional)

```bash
cp scripts/com.flowlocal.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.flowlocal.plist
```

## Development

```bash
uv run pytest    # includes a real end-to-end Whisper test using macOS `say`
```
