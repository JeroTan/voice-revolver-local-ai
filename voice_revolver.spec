# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller Specification File for Voice Revolver AI
Builds portable Windows .exe with console window visible for logs
"""

import sys
from pathlib import Path

block_cipher = None

# Get project root
project_root = Path(SPECPATH)

# Collect data files
datas = [
    # RVC module (entire folder - configs, models, training scripts)
    (str(project_root / 'rvc'), 'rvc'),
    
    # Assets (config.json for RVC model extraction)
    (str(project_root / 'assets'), 'assets'),
]

# Add virtual environments if they exist (will be extracted on first run)
venvs_to_bundle = ['venv-rvc', 'venv-mdx', 'venv-enhance']
for venv_name in venvs_to_bundle:
    venv_path = project_root / venv_name
    if venv_path.exists():
        datas.append((str(venv_path), f'bundled_venvs/{venv_name}'))
        print(f"✓ Including {venv_name} in build")
    else:
        print(f"⚠ Skipping {venv_name} (not found)")

# Add icon if it exists
icon_path = project_root / 'icon.ico'
if not icon_path.exists():
    print("⚠ icon.ico not found, using default icon")
    icon_file = None
else:
    icon_file = str(icon_path)

a = Analysis(
    ['run.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[
        # PyTorch core
        'torch',
        'torch.nn',
        'torch.nn.functional',
        'torch.nn.modules',
        'torch.nn.modules.loss',
        'torch.optim',
        'torch.autograd',
        'torch.backends',
        'torch.backends.cudnn',
        'torch.cuda',
        'torch._C',
        
        # TorchAudio
        'torchaudio',
        'torchaudio.transforms',
        'torchaudio.functional',
        'torchaudio.backend',
        
        # Demucs
        'demucs',
        'demucs.pretrained',
        'demucs.separate',
        'demucs.htdemucs',
        'demucs.hdemucs',
        'demucs.demucs',
        'demucs.tasnet',
        
        # ChatterBox VC
        'chatterbox_tts',
        'chatterbox_tts.models',
        'chatterbox_tts.utils',
        
        # OpenVoice (legacy fallback)
        'openvoice',
        'openvoice.api',
        
        # Audio processing
        'pydub',
        'pydub.audio_segment',
        'soundfile',
        'librosa',
        'librosa.feature',
        'librosa.effects',
        'librosa.core',
        'noisereduce',
        'pedalboard',
        'pyloudnorm',
        
        # Scientific computing
        'scipy',
        'scipy.signal',
        'scipy.interpolate',
        'scipy.ndimage',
        'scipy.fft',
        'numpy',
        'numpy.core',
        'numpy.lib',
        
        # Visualization
        'matplotlib',
        'matplotlib.pyplot',
        'matplotlib.backends',
        'matplotlib.backends.backend_tkagg',
        
        # FFmpeg wrapper
        'static_ffmpeg',
        'static_ffmpeg.run',
        
        # Pygame for audio preview
        'pygame',
        'pygame.mixer',
        
        # Transformers (for ChatterBox/OpenVoice)
        'transformers',
        'transformers.models',
        
        # Tkinter components (usually included but just in case)
        'tkinter',
        'tkinter.ttk',
        'tkinter.scrolledtext',
        'tkinter.filedialog',
        'tkinter.messagebox',
        
        # Standard library that might be missed
        'queue',
        'threading',
        'multiprocessing',
        'subprocess',
        'json',
        'pickle',
        'zipfile',
        'tempfile',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['runtime_hook.py'],
    excludes=[
        # Exclude test/development packages
        'pytest',
        'unittest',
        'test',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='VoiceRevolverAI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # UPX often breaks PyTorch DLLs
    console=True,  # ← KEEP CONSOLE VISIBLE FOR LOGS AND DEBUGGING
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_file,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='VoiceRevolverAI',
)
