@echo off
REM Voice Revolver AI - Launch Script
REM Activates virtual environment and runs the application

echo ========================================
echo   Voice Revolver AI - Starting...
echo ========================================
echo.

REM Activate virtual environment (venv, not .venv)
call venv\Scripts\activate.bat

REM Run the application
python run.py

REM Keep window open if there's an error
if errorlevel 1 (
    echo.
    echo ========================================
    echo   Application exited with error
    echo ========================================
    pause
)
