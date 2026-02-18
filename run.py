#!/usr/bin/env python3
"""
Voice Revolver AI - Entry Point
Run this to start the application
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from voice_revolver_ui.main import main

if __name__ == "__main__":
    main()
