@echo off
echo ============================================
echo AlmaCut3D Server - Clean Start
echo ============================================
echo.
echo Step 1: Clearing Python cache...
python -c "import os, shutil; shutil.rmtree('__pycache__', ignore_errors=True); print('Cache cleared!')"
echo.
echo Step 2: Starting uvicorn server...
echo Server will run on: http://127.0.0.1:8000
echo.
python -B -m uvicorn api:app --host 0.0.0.0 --port 8000 --reload
