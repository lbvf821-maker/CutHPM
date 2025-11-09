@echo off
echo Starting API server in debug mode...
echo Watch console for errors!
echo.
cd /d "%~dp0"
python -m uvicorn api:app --reload --host 127.0.0.1 --port 3000
pause
