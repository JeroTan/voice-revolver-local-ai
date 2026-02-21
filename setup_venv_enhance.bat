@echo off
REM Setup script for venv-enhance (Resemble Enhance virtual environment)
REM This creates an isolated environment for Resemble Enhance to avoid dependency conflicts

echo.
echo ========================================
echo   Voice Revolver AI - venv-enhance Setup
echo ========================================
echo.
echo This will install Resemble Enhance in a separate virtual environment
echo to avoid dependency conflicts with the main application.
echo.
echo Requirements:
echo   - Python 3.10 or higher (Python 3.11 recommended)
echo   - For GPU: NVIDIA GPU with CUDA 11.8 installed
echo.

REM Check if venv-enhance already exists
if exist "venv-enhance\" (
    echo WARNING: venv-enhance folder already exists!
    echo.
    choice /C YN /M "Do you want to DELETE and recreate it"
    if errorlevel 2 goto :skip_delete
    if errorlevel 1 (
        echo Deleting existing venv-enhance...
        rmdir /s /q "venv-enhance"
    )
)

:skip_delete

echo.
echo Step 1: Creating virtual environment...
echo ----------------------------------------
python -m venv venv-enhance
if errorlevel 1 (
    echo ERROR: Failed to create virtual environment
    echo Make sure Python 3.10+ is installed and in PATH
    pause
    exit /b 1
)
echo ✓ Virtual environment created

echo.
echo Step 2: Activating environment...
echo ----------------------------------------
call .\venv-enhance\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment
    pause
    exit /b 1
)
echo ✓ Environment activated

echo.
echo Step 3: Upgrading pip...
echo ----------------------------------------
python -m pip install --upgrade pip
if errorlevel 1 (
    echo WARNING: Failed to upgrade pip (continuing anyway)
)

echo.
echo Step 4: Installing resemble-enhance...
echo ----------------------------------------
echo This may take several minutes...
pip install resemble-enhance --upgrade
if errorlevel 1 (
    echo ERROR: Failed to install resemble-enhance
    echo.
    echo This might be due to:
    echo   1. deepspeed not supporting Windows (try installing without it)
    echo   2. Network issues (check your internet connection)
    echo   3. Python version incompatibility
    pause
    exit /b 1
)
echo ✓ resemble-enhance installed

echo.
echo Step 5: Installing PyTorch with CUDA support (GPU acceleration)...
echo ----------------------------------------
choice /C YN /M "Do you have an NVIDIA GPU with CUDA 11.8 installed"
if errorlevel 2 goto :cpu_only
if errorlevel 1 (
    echo Installing PyTorch with CUDA 11.8...
    pip install torch==2.1.2 torchaudio==2.1.2 --index-url https://download.pytorch.org/whl/cu118 --force-reinstall
    if errorlevel 1 (
        echo WARNING: GPU installation failed, falling back to CPU
        goto :cpu_only
    )
    echo ✓ PyTorch with CUDA installed
    goto :verify
)

:cpu_only
echo Installing PyTorch for CPU only...
pip install torch==2.1.2 torchaudio==2.1.2 --index-url https://download.pytorch.org/whl/cpu --force-reinstall
if errorlevel 1 (
    echo ERROR: Failed to install PyTorch
    pause
    exit /b 1
)
echo ✓ PyTorch (CPU) installed

:verify
echo.
echo Step 6: Verifying installation...
echo ----------------------------------------
python -c "import resemble_enhance; print('✓ resemble_enhance module found')"
if errorlevel 1 (
    echo ERROR: resemble_enhance not importable
    pause
    exit /b 1
)

python -c "import torch; print('✓ PyTorch version:', torch.__version__); print('✓ CUDA available:', torch.cuda.is_available())"
if errorlevel 1 (
    echo WARNING: PyTorch verification failed
)

echo.
echo ========================================
echo   Installation Complete!
echo ========================================
echo.
echo venv-enhance is now set up and ready to use.
echo.
echo The Voice Revolver AI will automatically use this environment
echo when "Improve Vocals" is enabled.
echo.
echo To manually activate this environment:
echo   .\venv-enhance\Scripts\Activate.ps1
echo.
pause
