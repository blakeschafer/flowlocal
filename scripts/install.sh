#!/bin/bash
# FlowLocal installer: sets up the venv and registers a LaunchAgent so
# FlowLocal starts at every login and restarts if it crashes.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PLIST=~/Library/LaunchAgents/com.flowlocal.plist
BIN="$REPO_DIR/.venv/bin/flowlocal"

if [[ "$(uname -s)" != "Darwin" || "$(uname -m)" != "arm64" ]]; then
    echo "FlowLocal requires an Apple Silicon Mac (MLX runs on the Apple GPU)." >&2
    exit 1
fi

if ! command -v uv >/dev/null; then
    echo "uv is required. Install it first:" >&2
    echo "  curl -LsSf https://astral.sh/uv/install.sh | sh" >&2
    exit 1
fi

echo "==> Installing Python environment (uv sync)"
(cd "$REPO_DIR" && uv sync)

if command -v ollama >/dev/null; then
    echo "==> Ollama found. Pulling cleanup model (llama3.2:3b, ~2GB, one time)"
    ollama pull llama3.2:3b || echo "    (pull failed — FlowLocal will use its regex fallback until the model exists)"
else
    echo "==> Ollama not found — AI cleanup will use the built-in regex fallback."
    echo "    For the full experience: brew install ollama && brew services start ollama && ollama pull llama3.2:3b"
fi

echo "==> Registering LaunchAgent ($PLIST)"
mkdir -p ~/Library/LaunchAgents
cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.flowlocal</string>
    <key>ProgramArguments</key>
    <array>
        <string>$BIN</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
    </dict>
    <key>ProcessType</key>
    <string>Interactive</string>
    <key>StandardOutPath</key>
    <string>/tmp/flowlocal.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/flowlocal.err</string>
</dict>
</plist>
EOF

# bootout is asynchronous — wait for the old instance to fully unload
# before bootstrapping, or launchd returns EIO.
launchctl bootout "gui/$(id -u)/com.flowlocal" 2>/dev/null || true
for _ in $(seq 1 50); do
    launchctl print "gui/$(id -u)/com.flowlocal" >/dev/null 2>&1 || break
    sleep 0.2
done
launchctl bootstrap "gui/$(id -u)" "$PLIST"

cat <<'EOF'

✅ FlowLocal is installed and running (look for 🎙 in the menu bar;
   ⏳ means the Whisper model is downloading — first run only, ~1.6GB).

⚠️  One-time macOS permissions (System Settings → Privacy & Security):
   1. Microphone        — allow when prompted on first dictation
   2. Input Monitoring  — add the Python binary FlowLocal runs under
   3. Accessibility     — same binary (needed to paste via ⌘V)

   The binary to grant is the target of:
      readlink -f .venv/bin/python3
   After granting, restart FlowLocal:
      launchctl kickstart -k gui/$(id -u)/com.flowlocal

Hold Right-Option, speak, release. Enjoy!
EOF
