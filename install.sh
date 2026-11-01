#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
PY="python3"; command -v $PY >/dev/null || PY="python"
echo "=== SHELLFORGE web installer ==="
$PY -m pip install --upgrade pip >/dev/null 2>&1 || true
$PY -m pip install -r requirements.txt
echo
echo "[✓] dependencies installed"
echo "[✓] run: $PY run.py"
echo "[✓] open: http://127.0.0.1:8080"
