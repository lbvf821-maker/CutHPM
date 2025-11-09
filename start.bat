@echo off
echo Starting AlmaCut3D Server...
cd /d %~dp0
call venv\Scripts\activate.bat
python run.py

