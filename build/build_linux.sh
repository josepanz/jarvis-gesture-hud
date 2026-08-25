#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt pyinstaller

pyinstaller build/jarvis.spec --distpath dist --workpath build/work --noconfirm

echo "Portable binary: dist/Jarvis"
