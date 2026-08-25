$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt pyinstaller

pyinstaller build/jarvis.spec --distpath dist --workpath build/work --noconfirm

Write-Host "Portable exe: dist/Jarvis.exe"
