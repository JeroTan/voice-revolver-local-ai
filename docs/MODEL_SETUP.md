# TTS Model Setup Guide

## Quick Start

Voice Revolver uses ChatterBox TTS models which need to be downloaded once from HuggingFace.

### Option 1: Windows Batch File (Easiest)

1. Double-click `setup_models.bat`
2. Follow the prompts to enter your HuggingFace token
3. Wait for models to download (~850MB total)

### Option 2: Manual Setup

```bash
# Activate your Python environment
.venv-1\Scripts\activate.bat  # Windows
source .venv-1/bin/activate    # Linux/Mac

# Run the download script
python download_models.py
```

## Getting a HuggingFace Token

The Turbo model requires a free HuggingFace account token (one-time setup).

1. Go to https://huggingface.co/settings/tokens
2. Click "New token"
3. Give it a name (e.g., "voice-revolver")
4. Select **Read** access
5. Copy the token

### Set the token (choose one):

**Option A**: Environment Variable (Recommended)
```bash
# Windows (PowerShell)
$env:HF_TOKEN="your_token_here"

# Windows (Command Prompt)
set HF_TOKEN=your_token_here

# Linux/Mac
export HF_TOKEN=your_token_here
```

**Option B**: Paste when prompted by `download_models.py`

## What Gets Downloaded

- **Turbo Model** (~350MB): English-only, supports special tokens like `[laugh]`, `[chuckle]`
- **MTL Model** (~500MB): 23+ languages support

## After Setup

Once downloaded, models are cached locally at:
```
./models/chatterbox/
├── turbo/
└── mtl/
```

**No token required after initial download** - models load from local cache!

## Troubleshooting

### "Token is required" error
- Make sure you set `HF_TOKEN` environment variable
- Or provide the token when prompted by `download_models.py`

### Download fails
- Check your internet connection
- Verify your HuggingFace token is valid
- Make sure you have ~1GB free disk space

### Models already downloaded
- If you see "already cached", you're all set!
- The app will load models from local cache automatically

## Manual Model Management

Check model status:
```python
from voice_revolver_core.infrastructure.model_downloader import ModelDownloader

downloader = ModelDownloader()
print("Turbo cached:", downloader.is_turbo_downloaded())
print("MTL cached:", downloader.is_mtl_downloaded())
```

Re-download if needed:
```python
downloader.download_turbo(token="your_token")
downloader.download_mtl(token="your_token")
```
