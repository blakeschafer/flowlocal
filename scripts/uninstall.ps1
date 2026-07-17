# Stops FlowLocal and removes its start-at-login registration. The repo,
# models, and config are left on disk; see README for how to remove those too.
# Run with:  powershell -ExecutionPolicy Bypass -File scripts\uninstall.ps1
Stop-Process -Name flowlocalw -ErrorAction SilentlyContinue
Remove-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" `
    -Name "FlowLocal" -ErrorAction SilentlyContinue

Write-Host "FlowLocal removed. It will no longer start at login."
Write-Host "Optional cleanup:"
Write-Host "  Remove-Item -Recurse ~\.flowlocal                  # settings"
Write-Host "  Remove-Item -Recurse ~\.cache\huggingface          # whisper model"
Write-Host "  ollama rm llama3.2:3b                              # cleanup model"
