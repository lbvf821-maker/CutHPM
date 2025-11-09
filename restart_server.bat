@echo off
echo ========================================
echo KILLING OLD SERVER AND RESTARTING
echo ========================================
echo.

echo [1/4] Killing all Python processes...
taskkill /F /IM python.exe /T 2>nul
timeout /t 2 /nobreak >nul

echo [2/4] Deleting cache...
python -c "import shutil; shutil.rmtree('__pycache__', ignore_errors=True)"

echo [3/4] Waiting for ports to free...
timeout /t 3 /nobreak >nul

echo [4/4] Starting fresh server...
echo.
echo Server URL: http://127.0.0.1:8000
echo Frontend: http://127.0.0.1:3000
echo.
python -B -m uvicorn api:app --host 0.0.0.0 --port 8000 --reload --log-level debug
