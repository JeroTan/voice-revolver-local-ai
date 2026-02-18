@echo off
REM Voice Revolver AI - Development Runner (Batch)
REM This script uses Python 3.11 from virtual environment directly

echo Activating Python 3.11 virtual environment...
call .\venv\Scripts\activate.bat

echo Verifying Python version...
.\venv\Scripts\python.exe --version

echo Launching Voice Revolver AI...
.\venv\Scripts\python.exe run.py
pause
