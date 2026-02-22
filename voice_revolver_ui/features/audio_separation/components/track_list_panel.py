"""
Track List Panel Component - Audio Separation Workspace
Scrollable list of track editors
"""

import tkinter as tk
from tkinter import ttk
from pathlib import Path
from typing import List, Optional
import logging

from voice_revolver_ui.features.audio_separation.components.track_editor import TrackEditor
from voice_revolver_core.domain.base import AudioStems

logger = logging.getLogger(__name__)


class TrackListPanel(ttk.Frame):
    """
    Scrollable panel containing multiple track editors.
    
    Features:
    - Vertical scrolling for multiple tracks
    - Dynamic track creation based on stems
    - Centralized curve collection
    """
    
    def __init__(self, parent, **kwargs):
        """
        Initialize track list panel.
        
        Args:
            parent: Parent tkinter widget
            **kwargs: Additional configuration for the Frame
        """
        super().__init__(parent, **kwargs)
        
        self.track_editors: List[TrackEditor] = []
        
        # UI setup
        self._setup_ui()
        
    def _setup_ui(self):
        """Create and layout child widgets."""
        # Create canvas with scrollbar
        self.canvas = tk.Canvas(self, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.canvas.yview)
        
        # Container frame inside canvas for track editors
        self.tracks_container = ttk.Frame(self.canvas)
        
        # Configure canvas scrolling
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        # Create window in canvas
        self.canvas_window = self.canvas.create_window(
            (0, 0),
            window=self.tracks_container,
            anchor=tk.NW
        )
        
        # Pack scrollbar and canvas
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Bind canvas resize events
        self.tracks_container.bind('<Configure>', self._on_frame_configure)
        self.canvas.bind('<Configure>', self._on_canvas_configure)
        
        # Bind mousewheel scrolling
        self.canvas.bind_all('<MouseWheel>', self._on_mousewheel)
        
    def _on_frame_configure(self, event=None):
        """Update canvas scroll region when frame size changes."""
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))
    
    def _on_canvas_configure(self, event):
        """Update tracks container width when canvas resizes."""
        canvas_width = event.width
        self.canvas.itemconfig(self.canvas_window, width=canvas_width)
    
    def _on_mousewheel(self, event):
        """Handle mousewheel scrolling."""
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
    
    def load_tracks(self, stems: AudioStems, improve_vocals: bool = False):
        """
        Load audio stems as separate tracks (DYNAMIC - renders only what separator produced).
        
        Args:
            stems: AudioStems object with separated audio files
            improve_vocals: Whether vocals were enhanced
        """
        # Clear existing tracks
        self.clear_tracks()
        
        # DYNAMIC track list - only load stems that actually exist
        # Different separators produce different numbers of stems:
        # - Demucs: 4 stems (vocals, drums, bass, other)
        # - MDX: 2 stems (vocals, other/instrumental)
        track_number = 1
        
        # Build dynamic stem map from AudioStems fields
        stem_map = []
        if stems.vocals:
            stem_map.append(('vocals', stems.vocals))
        if stems.drums:
            stem_map.append(('drums', stems.drums))
        if stems.bass:
            stem_map.append(('bass', stems.bass))
        if stems.other:
            stem_map.append(('other', stems.other))
        
        for stem_name, stem_path in stem_map:
            if stem_path.exists():
                # Create track editor
                track_editor = TrackEditor(
                    self.tracks_container,
                    track_number=track_number,
                    track_name=stem_name
                )
                track_editor.pack(fill=tk.BOTH, expand=True, pady=5)
                
                # Load audio (pass enhanced vocals if available for blend mode)
                # Only pass enhanced vocals if: 1) this is vocals track, 2) improve_vocals was checked, 3) enhanced file exists
                enhanced_vocal_path = None
                if stem_name == 'vocals' and improve_vocals and stems.vocals_enhanced:
                    enhanced_vocal_path = stems.vocals_enhanced
                    logger.info(f"Vocals track will have blend mode (enhanced: {stems.vocals_enhanced.name})")
                
                track_editor.load_audio(stem_path, enhanced_vocal_path=enhanced_vocal_path)
                
                # Enable export
                track_editor.enable_export()
                
                # Store reference
                self.track_editors.append(track_editor)
                
                track_number += 1
                logger.info(f"Track {track_number - 1} loaded: {stem_name}")
        
        if not self.track_editors:
            logger.warning("No tracks loaded (all stems missing)")
        else:
            logger.info(f"Loaded {len(self.track_editors)} tracks successfully")
    
    def clear_tracks(self):
        """Remove all track editors."""
        for track_editor in self.track_editors:
            track_editor.destroy()
        
        self.track_editors.clear()
        logger.info("All tracks cleared")
    
    def get_all_curves(self) -> dict:
        """
        Get curves from all tracks.
        
        Returns:
            Dictionary mapping track names to their curves
        """
        all_curves = {}
        
        for track_editor in self.track_editors:
            track_name = track_editor.track_name
            curves = track_editor.get_curves()
            all_curves[track_name] = curves
        
        return all_curves
