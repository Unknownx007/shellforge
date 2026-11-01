@echo off
cd /d "%~dp0"
echo === SHELLFORGE web installer ===
python -m pip install --upgrade pip >nul 2>&1
python -m pip install -r requirements.txt
echo.
echo [OK] dependencies installed
echo [OK] run: python run.py
echo [OK] open: http://127.0.0.1:8080
pause
