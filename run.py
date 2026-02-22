#!/usr/bin/env python3
"""
Voice Revolver AI - Entry Point
Run this to start the application
"""

import sys
import os

# Fix Windows console encoding for emoji/Unicode characters in logs
# This MUST happen before any imports that use logging
if os.name == 'nt':  # Windows only
    # Set environment variable first - this affects all subprocess Python calls
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    
    # Try to set console to UTF-8 mode
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleOutputCP(65001)  # UTF-8 code page
    except:
        pass
    
    # Reconfigure stdout and stderr to use UTF-8 with error replacement
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    else:
        # Python < 3.7 fallback
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    else:
        import io
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    
    # Monkey-patch logging.StreamHandler to prevent it from closing our streams
    import logging
    
    _original_stream_handler_close = logging.StreamHandler.close
    
    def _safe_close(self):
        """Prevent closing stdout/stderr streams"""
        # Only close the stream if it's not stdout or stderr
        if self.stream not in (sys.stdout, sys.stderr):
            _original_stream_handler_close(self)
        else:
            # Just flush without closing
            self.acquire()
            try:
                if self.stream and hasattr(self.stream, 'flush'):
                    self.stream.flush()
            finally:
                self.release()
    
    logging.StreamHandler.close = _safe_close

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    from voice_revolver_ui.main_tk import main
    main()
