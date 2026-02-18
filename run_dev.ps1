# Voice Revolver AI - Development Runner
# This script activates the virtual environment and launches the application

Write-Host "Activating Python 3.11 virtual environment..." -ForegroundColor Green
& .\venv\Scripts\Activate.ps1

Write-Host "Verifying Python version..." -ForegroundColor Green
& .\venv\Scripts\python.exe --version

Write-Host "Launching Voice Revolver AI..." -ForegroundColor Green
& .\venv\Scripts\python.exe run.py
