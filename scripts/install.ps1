# FlowLocal Windows installer: sets up the venv and registers FlowLocal to
# start at login (HKCU Run key — no admin rights needed).
# Run with:  powershell -ExecutionPolicy Bypass -File scripts\install.ps1
$ErrorActionPreference = "Stop"

$RepoDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Exe = Join-Path $RepoDir ".venv\Scripts\flowlocalw.exe"

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "uv is required. Install it first:" -ForegroundColor Red
    Write-Host "  winget install --id=astral-sh.uv -e"
    Write-Host "then reopen this terminal and re-run the installer."
    exit 1
}

Write-Host "==> Installing Python environment (uv sync)"
Push-Location $RepoDir
uv sync
Pop-Location

if (Get-Command ollama -ErrorAction SilentlyContinue) {
    Write-Host "==> Ollama found. Pulling cleanup model (llama3.2:3b, ~2GB, one time)"
    ollama pull llama3.2:3b
    if ($LASTEXITCODE -ne 0) {
        Write-Host "    (pull failed - FlowLocal will use its regex fallback until the model exists)"
    }
} else {
    Write-Host "==> Ollama not found - AI cleanup will use the built-in regex fallback."
    Write-Host "    For the full experience: install Ollama from https://ollama.com, then: ollama pull llama3.2:3b"
}

Write-Host "==> Registering FlowLocal to start at login"
Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" `
    -Name "FlowLocal" -Value "`"$Exe`""

Write-Host "==> Starting FlowLocal"
Stop-Process -Name flowlocalw -ErrorAction SilentlyContinue
Start-Process $Exe

Write-Host ""
Write-Host "FlowLocal is installed and running - look for the mic icon in the" -ForegroundColor Green
Write-Host "system tray (gray while the Whisper model downloads; first run only)." -ForegroundColor Green
Write-Host ""
Write-Host "If dictation stays silent, allow microphone access:"
Write-Host "  Settings > Privacy & security > Microphone > 'Let desktop apps access your microphone'"
Write-Host ""
Write-Host "Hold Right-Ctrl, speak, release. Enjoy!"
