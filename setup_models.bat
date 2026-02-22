@echo off
echo ============================================================
echo ChatterBox TTS Model Setup
echo ============================================================
echo.
echo This will download TTS models to your local cache.
echo You'll need a free HuggingFace token (one-time setup).
echo.
pause

call .venv-1\Scripts\activate.bat
python download_models.py

echo.
pause
