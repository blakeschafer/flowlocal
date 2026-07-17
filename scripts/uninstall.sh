#!/bin/bash
# Stops FlowLocal and removes its LaunchAgent. The repo, models, and config
# are left on disk; see README for how to remove those too.
set -euo pipefail

launchctl bootout "gui/$(id -u)/com.flowlocal" 2>/dev/null || true
rm -f ~/Library/LaunchAgents/com.flowlocal.plist
echo "FlowLocal service removed. It will no longer start at login."
echo "Optional cleanup:"
echo "  rm -rf ~/.flowlocal                        # settings"
echo "  rm -rf ~/.cache/huggingface/hub/models--mlx-community--whisper-large-v3-turbo  # whisper model"
echo "  ollama rm llama3.2:3b                      # cleanup model"
