"""Input panel for Track Merger workspace - Track list with volume controls."""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
from typing import Optional, Callable, List, Dict
import logging
import threading
import numpy as np

try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False

try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False

logger = logging.getLogger(__name__)

# Maximum number of tracks allowed (prevents UI clutter and memory issues)
MAX_TRACKS = 999

# Waveform visualization settings
WAVEFORM_WIDTH = 200
WAVEFORM_HEIGHT = 65  # Increased for better visibility
WAVEFORM_COLOR = "#4CAF50"
WAVEFORM_BG = "#2d2d2d"


class TrackItem:
    """Represents a single track in the merger."""
    
    def __init__(
        self,
        track_id: int,
        file_path: Path,
        display_name: str,
        volume: float = 1.0
    ):
        """Initialize track item.
        
        Args:
            track_id: Unique identifier for this track
            file_path: Path to the audio file
            display_name: Name to display in the UI
            volume: Volume multiplier (0.0 to 2.0, default 1.0)
        """
        self.track_id = track_id
        self.file_path = file_path
        self.display_name = display_name
        self.volume = volume
        
        # UI elements (set when track row is created)
        self.frame: Optional[ttk.Frame] = None
        self.name_var: Optional[tk.StringVar] = None  # Editable track name
        self.volume_var: Optional[tk.DoubleVar] = None
        self.volume_label: Optional[ttk.Label] = None
        self.play_button: Optional[ttk.Button] = None
        self.waveform_canvas: Optional[tk.Canvas] = None
        self.seek_slider: Optional[ttk.Scale] = None
        self.seek_var: Optional[tk.DoubleVar] = None
        self.time_label: Optional[ttk.Label] = None
        
        # Playback state
        self.is_playing: bool = False
        self.duration_ms: int = 0  # Track duration in milliseconds
        self._seek_update_job: Optional[str] = None


class InputPanel(ttk.Frame):
    """Left panel with track list, volume controls, and action buttons."""
    
    def __init__(
        self,
        parent: ttk.Frame,
        on_merge: Optional[Callable] = None,
        on_export: Optional[Callable] = None,
        **kwargs
    ):
        """Initialize the input panel.
        
        Args:
            parent: Parent widget
            on_merge: Callback when Merge Tracks is clicked
            on_export: Callback when Export is clicked
        """
        super().__init__(parent, padding=10, **kwargs)
        
        self.on_merge = on_merge
        self.on_export = on_export
        
        # Track management
        self.tracks: List[TrackItem] = []
        self.next_track_id = 1
        
        # Playback management
        self.currently_playing_track: Optional[TrackItem] = None
        self._init_audio()
        
        self._setup_ui()
    
    def _init_audio(self):
        """Initialize audio playback system."""
        if PYGAME_AVAILABLE:
            try:
                if not pygame.mixer.get_init():
                    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
                logger.info("Pygame mixer initialized for track preview")
            except Exception as e:
                logger.warning(f"Failed to initialize pygame mixer: {e}")
    
    def _cleanup_audio(self):
        """Cleanup audio resources."""
        self.stop_playback()
    
    def stop_playback(self):
        """Stop any currently playing track."""
        if PYGAME_AVAILABLE and pygame.mixer.get_init():
            pygame.mixer.music.stop()
        
        if self.currently_playing_track:
            track = self.currently_playing_track
            track.is_playing = False
            
            # Cancel seek update job
            if track._seek_update_job:
                self.after_cancel(track._seek_update_job)
                track._seek_update_job = None
            
            # Reset UI
            if track.play_button:
                track.play_button.configure(text="▶")
            if track.seek_var:
                track.seek_var.set(0)
            self._update_time_label(track, 0)
            
            self.currently_playing_track = None
    
    def _setup_ui(self):
        """Set up the UI components."""
        # Configure grid
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)  # Track list expands
        
        # === Title ===
        title_label = ttk.Label(
            self,
            text="Track Merger",
            font=("Segoe UI", 14, "bold")
        )
        title_label.grid(row=0, column=0, sticky=tk.W, pady=(0, 10))
        
        # === Track List Section ===
        tracks_frame = ttk.LabelFrame(self, text="Tracks", padding=5)
        tracks_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        tracks_frame.columnconfigure(0, weight=1)
        tracks_frame.rowconfigure(0, weight=1)
        
        # Scrollable canvas for tracks
        self.tracks_canvas = tk.Canvas(tracks_frame, highlightthickness=0, height=300)
        self.tracks_scrollbar = ttk.Scrollbar(
            tracks_frame,
            orient=tk.VERTICAL,
            command=self.tracks_canvas.yview
        )
        self.tracks_inner_frame = ttk.Frame(self.tracks_canvas)
        
        self.tracks_canvas.configure(yscrollcommand=self.tracks_scrollbar.set)
        
        # Create window in canvas
        self.tracks_window = self.tracks_canvas.create_window(
            (0, 0),
            window=self.tracks_inner_frame,
            anchor=tk.NW
        )
        
        # Grid layout
        self.tracks_canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.tracks_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # Configure inner frame expansion
        self.tracks_inner_frame.columnconfigure(0, weight=1)
        
        # Bind canvas resize
        self.tracks_canvas.bind("<Configure>", self._on_canvas_configure)
        self.tracks_inner_frame.bind("<Configure>", self._on_frame_configure)
        
        # Bind mousewheel scrolling
        self.tracks_canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        
        # Empty state label
        self.empty_label = ttk.Label(
            self.tracks_inner_frame,
            text="No tracks added.\nClick 'Add Track' to begin.",
            foreground="gray",
            justify=tk.CENTER
        )
        self.empty_label.grid(row=0, column=0, pady=50)
        
        # === Add Track Button ===
        self.add_track_btn = ttk.Button(
            self,
            text="Add Track",
            command=self._on_add_track_clicked
        )
        self.add_track_btn.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        
        # === Merge Button ===
        self.merge_btn = ttk.Button(
            self,
            text="Merge Tracks",
            command=self._on_merge_clicked,
            style="Accent.TButton"
        )
        self.merge_btn.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
        
        # === Export Section ===
        export_frame = ttk.LabelFrame(self, text="Export", padding=10)
        export_frame.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        export_frame.columnconfigure(1, weight=1)
        
        # Output format
        ttk.Label(export_frame, text="Format:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.format_var = tk.StringVar(value="wav")
        format_combo = ttk.Combobox(
            export_frame,
            textvariable=self.format_var,
            values=["wav", "mp3", "flac", "ogg"],
            state="readonly",
            width=10
        )
        format_combo.grid(row=0, column=1, sticky=tk.W, pady=(0, 10))
        
        # Use edited checkbox
        self.use_edited_var = tk.BooleanVar(value=False)
        self.use_edited_check = ttk.Checkbutton(
            export_frame,
            text="Use edited audio (with curve edits applied)",
            variable=self.use_edited_var
        )
        self.use_edited_check.grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=(0, 10))
        
        # Export button
        self.export_btn = ttk.Button(
            export_frame,
            text="Export",
            command=self._on_export_clicked,
            state=tk.DISABLED
        )
        self.export_btn.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E))
    
    def _on_canvas_configure(self, event):
        """Handle canvas resize to expand inner frame."""
        self.tracks_canvas.itemconfig(self.tracks_window, width=event.width)
    
    def _on_frame_configure(self, event):
        """Update scroll region when inner frame changes."""
        self.tracks_canvas.configure(scrollregion=self.tracks_canvas.bbox("all"))
    
    def _on_mousewheel(self, event):
        """Handle mousewheel scrolling."""
        self.tracks_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
    
    def _on_add_track_clicked(self):
        """Handle Add Track button click."""
        # Check track limit
        if len(self.tracks) >= MAX_TRACKS:
            messagebox.showwarning(
                "Track Limit Reached",
                f"Maximum number of tracks is {MAX_TRACKS}.\n\n"
                "Please remove some tracks before adding more."
            )
            return
        
        # Open file dialog
        file_path = filedialog.askopenfilename(
            title="Select Audio Track",
            filetypes=[
                ("Audio files", "*.wav *.mp3 *.flac *.ogg *.m4a *.aac"),
                ("WAV files", "*.wav"),
                ("MP3 files", "*.mp3"),
                ("FLAC files", "*.flac"),
                ("OGG files", "*.ogg"),
                ("All files", "*.*")
            ]
        )
        
        if not file_path:
            return  # User cancelled
        
        file_path = Path(file_path)
        
        # Validate file exists
        if not file_path.exists():
            messagebox.showerror("Error", f"File not found:\n{file_path}")
            return
        
        # Add track
        self._add_track(file_path)
    
    def _add_track(self, file_path: Path):
        """Add a track to the list.
        
        Args:
            file_path: Path to the audio file
        """
        # Create track item
        track = TrackItem(
            track_id=self.next_track_id,
            file_path=file_path,
            display_name=file_path.stem,
            volume=1.0
        )
        self.next_track_id += 1
        
        # Hide empty label if this is first track
        if len(self.tracks) == 0:
            self.empty_label.grid_remove()
        
        # Create track row UI
        self._create_track_row(track)
        
        # Add to list
        self.tracks.append(track)
        
        logger.info(f"Added track {track.track_id}: {file_path.name}")
    
    def _create_track_row(self, track: TrackItem):
        """Create UI row for a track.
        
        Layout:
        Row 0: [Editable Track Name]                         [X close btn]
        Row 1: [    Small Waveform Canvas    ] [Vertical Vol Slider] [%]
        Row 2: [▶] [======= Seek Slider =======] [0:00 / 0:00]
        
        Args:
            track: TrackItem to create row for
        """
        row_index = len(self.tracks)
        
        # Track row frame with border
        track_frame = ttk.Frame(self.tracks_inner_frame, padding=8)
        track_frame.grid(row=row_index, column=0, sticky=(tk.W, tk.E), pady=3)
        track_frame.columnconfigure(0, weight=1)
        track.frame = track_frame
        
        # === Row 0: Track Name (editable) + Close Button ===
        header_frame = ttk.Frame(track_frame)
        header_frame.grid(row=0, column=0, sticky=(tk.W, tk.E))
        header_frame.columnconfigure(0, weight=1)
        
        # Editable track name entry
        track.name_var = tk.StringVar(value=track.display_name)
        name_entry = ttk.Entry(
            header_frame,
            textvariable=track.name_var,
            font=("Segoe UI", 10, "bold"),
            width=25
        )
        name_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 10))
        name_entry.bind("<FocusOut>", lambda e, t=track: self._on_name_changed(t))
        name_entry.bind("<Return>", lambda e, t=track: self._on_name_changed(t))
        
        # Close button (X)
        close_btn = ttk.Button(
            header_frame,
            text="✕",
            width=3,
            command=lambda t=track: self._remove_track(t)
        )
        close_btn.grid(row=0, column=1, sticky=tk.E)
        
        # === Row 1: Waveform Canvas + Vertical Volume Slider ===
        middle_frame = ttk.Frame(track_frame)
        middle_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(8, 8))
        middle_frame.columnconfigure(0, weight=1)  # Waveform expands
        
        # Waveform canvas (left, expands)
        waveform_canvas = tk.Canvas(
            middle_frame,
            height=WAVEFORM_HEIGHT,
            bg=WAVEFORM_BG,
            highlightthickness=1,
            highlightbackground="#444444"
        )
        waveform_canvas.grid(row=0, column=0, sticky=(tk.W, tk.E))
        track.waveform_canvas = waveform_canvas
        
        # Vertical volume slider (right of waveform)
        track.volume_var = tk.DoubleVar(value=100.0)
        volume_slider = ttk.Scale(
            middle_frame,
            from_=200,  # Top = 200%
            to=0,       # Bottom = 0%
            orient=tk.VERTICAL,
            variable=track.volume_var,
            command=lambda val, t=track: self._on_volume_changed(t, val),
            length=WAVEFORM_HEIGHT
        )
        volume_slider.grid(row=0, column=1, sticky=(tk.N, tk.S), padx=(8, 2))
        
        # Volume percentage label
        track.volume_label = ttk.Label(middle_frame, text="100%", width=5, font=("Segoe UI", 8))
        track.volume_label.grid(row=0, column=2, sticky=tk.W)
        
        # Generate waveform in background
        self._generate_waveform_async(track)
        
        # === Row 2: Playback Controls (Play + Seek Slider + Time) ===
        playback_frame = ttk.Frame(track_frame)
        playback_frame.grid(row=2, column=0, sticky=(tk.W, tk.E))
        playback_frame.columnconfigure(1, weight=1)  # Seek slider expands
        
        # Play button
        play_btn = ttk.Button(
            playback_frame,
            text="▶",
            width=3,
            command=lambda t=track: self._toggle_play(t)
        )
        play_btn.grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        track.play_button = play_btn
        
        # Seek slider
        track.seek_var = tk.DoubleVar(value=0)
        seek_slider = ttk.Scale(
            playback_frame,
            from_=0,
            to=100,
            orient=tk.HORIZONTAL,
            variable=track.seek_var,
            command=lambda val, t=track: self._on_seek_changed(t, val)
        )
        seek_slider.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        track.seek_slider = seek_slider
        
        # Time label
        track.time_label = ttk.Label(
            playback_frame,
            text="0:00 / 0:00",
            font=("Segoe UI", 8),
            width=12
        )
        track.time_label.grid(row=0, column=2, sticky=tk.E)
        
        # Get track duration in background
        self._load_track_duration_async(track)
        
        # Separator line
        sep = ttk.Separator(track_frame, orient=tk.HORIZONTAL)
        sep.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(8, 0))
    
    def _on_name_changed(self, track: TrackItem):
        """Handle track name edit.
        
        Args:
            track: Track that was renamed
        """
        if track.name_var:
            new_name = track.name_var.get().strip()
            if new_name:
                track.display_name = new_name
                logger.debug(f"Track {track.track_id} renamed to: {new_name}")
            else:
                # Revert to original if empty
                track.name_var.set(track.display_name)
    
    def _toggle_play(self, track: TrackItem):
        """Toggle play/pause for a track.
        
        Args:
            track: Track to play/pause
        """
        if not PYGAME_AVAILABLE:
            messagebox.showwarning(
                "Playback Not Available",
                "pygame is not installed. Install it with:\npip install pygame"
            )
            return
        
        # If this track is already playing, stop it
        if track.is_playing:
            self.stop_playback()
            return
        
        # Stop any other playing track
        self.stop_playback()
        
        # Start playing this track
        try:
            pygame.mixer.music.load(str(track.file_path))
            pygame.mixer.music.set_volume(track.volume)
            pygame.mixer.music.play()
            
            track.is_playing = True
            self.currently_playing_track = track
            if track.play_button:
                track.play_button.configure(text="⏹")
            
            # Start seek position updates
            self._start_seek_updates(track)
            
            logger.info(f"Playing track: {track.file_path.name}")
        except Exception as e:
            logger.error(f"Failed to play track: {e}")
            messagebox.showerror("Playback Error", f"Failed to play track:\n{e}")
    
    def _load_track_duration_async(self, track: TrackItem):
        """Load track duration in background thread.
        
        Args:
            track: Track to get duration for
        """
        def load_duration():
            try:
                if LIBROSA_AVAILABLE:
                    duration = librosa.get_duration(path=str(track.file_path))
                    track.duration_ms = int(duration * 1000)
                    # Update time label on main thread
                    self.after(0, lambda: self._update_time_label(track, 0))
            except Exception as e:
                logger.warning(f"Failed to get duration for {track.file_path.name}: {e}")
        
        thread = threading.Thread(target=load_duration, daemon=True)
        thread.start()
    
    def _on_seek_changed(self, track: TrackItem, value: str):
        """Handle seek slider change.
        
        Args:
            track: Track being seeked
            value: New position (0-100 percentage)
        """
        if not track.is_playing:
            return
        
        try:
            percent = float(value)
            if track.duration_ms > 0 and PYGAME_AVAILABLE:
                position_ms = int((percent / 100) * track.duration_ms)
                # pygame music.set_pos expects seconds
                pygame.mixer.music.set_pos(position_ms / 1000)
                self._update_time_label(track, position_ms)
        except Exception as e:
            logger.warning(f"Seek failed: {e}")
    
    def _start_seek_updates(self, track: TrackItem):
        """Start periodic updates of seek slider position.
        
        Args:
            track: Track being played
        """
        def update():
            if not track.is_playing or not PYGAME_AVAILABLE:
                return
            
            try:
                # Get current position in ms
                pos_ms = pygame.mixer.music.get_pos()
                if pos_ms >= 0 and track.duration_ms > 0:
                    percent = (pos_ms / track.duration_ms) * 100
                    if track.seek_var:
                        track.seek_var.set(min(percent, 100))
                    self._update_time_label(track, pos_ms)
                    
                    # Check if playback ended
                    if not pygame.mixer.music.get_busy():
                        self.stop_playback()
                        return
                
                # Schedule next update
                track._seek_update_job = self.after(200, update)
            except Exception:
                pass
        
        update()
    
    def _update_time_label(self, track: TrackItem, current_ms: int):
        """Update track time label.
        
        Args:
            track: Track to update
            current_ms: Current position in milliseconds
        """
        if track.time_label:
            current_str = self._format_time(current_ms // 1000)
            total_str = self._format_time(track.duration_ms // 1000)
            track.time_label.config(text=f"{current_str} / {total_str}")
    
    def _format_time(self, seconds: int) -> str:
        """Format seconds as mm:ss.
        
        Args:
            seconds: Time in seconds
            
        Returns:
            Formatted string "m:ss"
        """
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes}:{secs:02d}"
    
    def _generate_waveform_async(self, track: TrackItem):
        """Generate waveform visualization in background thread.
        
        Args:
            track: Track to generate waveform for
        """
        def generate():
            try:
                waveform_data = self._load_waveform_data(track.file_path)
                if waveform_data is not None and track.waveform_canvas:
                    # Schedule UI update on main thread
                    self.after(0, lambda: self._draw_waveform(track, waveform_data))
            except Exception as e:
                logger.warning(f"Failed to generate waveform for {track.file_path.name}: {e}")
        
        thread = threading.Thread(target=generate, daemon=True)
        thread.start()
    
    def _load_waveform_data(self, file_path: Path) -> Optional[np.ndarray]:
        """Load audio and generate waveform data.
        
        Args:
            file_path: Path to audio file
            
        Returns:
            Downsampled waveform data or None if failed
        """
        if not LIBROSA_AVAILABLE:
            return None
        
        try:
            # Load audio with lower sample rate for speed
            y, sr = librosa.load(str(file_path), sr=8000, mono=True, duration=60)
            
            # Downsample to target width
            num_samples = len(y)
            samples_per_pixel = max(1, num_samples // WAVEFORM_WIDTH)
            
            # Calculate envelope (max amplitude per pixel)
            envelope = []
            for i in range(0, num_samples, samples_per_pixel):
                chunk = y[i:i + samples_per_pixel]
                if len(chunk) > 0:
                    envelope.append(np.max(np.abs(chunk)))
            
            return np.array(envelope)
        except Exception as e:
            logger.warning(f"Failed to load audio for waveform: {e}")
            return None
    
    def _draw_waveform(self, track: TrackItem, waveform_data: np.ndarray):
        """Draw waveform on canvas.
        
        Args:
            track: Track to draw waveform for
            waveform_data: Envelope data to draw
        """
        canvas = track.waveform_canvas
        if not canvas or not canvas.winfo_exists():
            return
        
        # Clear canvas
        canvas.delete("all")
        
        # Get canvas dimensions
        width = canvas.winfo_width() or WAVEFORM_WIDTH
        height = canvas.winfo_height() or WAVEFORM_HEIGHT
        
        if len(waveform_data) == 0:
            return
        
        # Normalize waveform
        max_val = np.max(waveform_data)
        if max_val > 0:
            waveform_data = waveform_data / max_val
        
        # Draw center line
        center_y = height // 2
        
        # Draw waveform bars
        bar_width = max(1, width / len(waveform_data))
        for i, amplitude in enumerate(waveform_data):
            x = int(i * bar_width)
            bar_height = int(amplitude * (height // 2 - 2))
            
            canvas.create_line(
                x, center_y - bar_height,
                x, center_y + bar_height,
                fill=WAVEFORM_COLOR,
                width=bar_width
            )
    
    def _on_volume_changed(self, track: TrackItem, value: str):
        """Handle volume slider change.
        
        Args:
            track: Track that changed
            value: New volume value (0-200)
        """
        try:
            volume_percent = float(value)
            track.volume = volume_percent / 100.0  # Convert to multiplier
            if track.volume_label:
                track.volume_label.config(text=f"{int(volume_percent)}%")
        except ValueError:
            pass
    
    def _remove_track(self, track: TrackItem):
        """Remove a track from the list.
        
        Args:
            track: Track to remove
        """
        # Stop playback if this track is playing
        if track.is_playing:
            self.stop_playback()
        
        # Remove from list
        if track in self.tracks:
            self.tracks.remove(track)
            
            # Destroy UI
            if track.frame:
                track.frame.destroy()
            
            # Rebuild track numbering
            self._rebuild_track_rows()
            
            logger.info(f"Removed track {track.track_id}: {track.file_path.name}")
        
        # Show empty label if no tracks left
        if len(self.tracks) == 0:
            self.empty_label.grid()
    
    def _rebuild_track_rows(self):
        """Rebuild track row UI after removal."""
        # Re-grid all remaining tracks with correct row indices
        for idx, track in enumerate(self.tracks):
            if track.frame:
                track.frame.grid_configure(row=idx)
    
    def _on_merge_clicked(self):
        """Handle Merge Tracks button click."""
        # Validate at least 2 tracks
        if len(self.tracks) < 2:
            messagebox.showwarning(
                "Not Enough Tracks",
                "Please add at least 2 tracks to merge."
            )
            return
        
        if self.on_merge:
            self.on_merge()
    
    def _on_export_clicked(self):
        """Handle Export button click."""
        if self.on_export:
            self.on_export()
    
    # ===== Public API =====
    
    def get_tracks(self) -> List[Dict]:
        """Get all tracks with their settings.
        
        Returns:
            List of dicts with file_path and volume for each track
        """
        return [
            {
                "file_path": track.file_path,
                "volume": track.volume,
                "name": track.name_var.get() if track.name_var else track.display_name
            }
            for track in self.tracks
        ]
    
    def get_output_format(self) -> str:
        """Get selected output format.
        
        Returns:
            Format string (wav, mp3, flac, ogg)
        """
        return self.format_var.get()
    
    def get_use_edited(self) -> bool:
        """Get whether to use edited audio.
        
        Returns:
            True if user wants curve-edited version
        """
        return self.use_edited_var.get()
    
    def set_processing(self, is_processing: bool):
        """Enable/disable controls during processing.
        
        Args:
            is_processing: True to disable controls
        """
        state = tk.DISABLED if is_processing else tk.NORMAL
        self.add_track_btn.config(state=state)
        self.merge_btn.config(state=state)
        
        # Disable remove buttons on tracks
        for track in self.tracks:
            if track.frame:
                for child in track.frame.winfo_children():
                    if isinstance(child, ttk.Button):
                        child.config(state=state)
    
    def enable_export(self, enabled: bool):
        """Enable or disable the export button.
        
        Args:
            enabled: True to enable
        """
        self.export_btn.config(state=tk.NORMAL if enabled else tk.DISABLED)
    
    def clear_tracks(self):
        """Remove all tracks."""
        for track in self.tracks.copy():
            self._remove_track(track)
