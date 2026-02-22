"""
Spectrum Editor Component - Phase 2
Interactive waveform/spectrum visualization with four editing modes:
1. Pitching - Adjust pitch curve over time
2. Reverb - Adjust reverb strength over time
3. Volume - Adjust volume over time
4. Noise Reduction - Adjust noise reduction strength over time
"""

import tkinter as tk
from tkinter import ttk
import numpy as np
from pathlib import Path
from typing import Optional, List, Tuple
import logging

# Import matplotlib for embedding in tkinter
try:
    import matplotlib
    matplotlib.use('TkAgg')  # Use TkAgg backend for tkinter integration
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("Warning: matplotlib not available, spectrum editor disabled")

# Import librosa for audio loading
try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False
    print("Warning: librosa not available, spectrum editor disabled")

# Import scipy for interpolation
try:
    from scipy.interpolate import CubicSpline, interp1d
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    print("Warning: scipy not available, curve interpolation disabled")

# Import pygame for audio playback
try:
    import pygame.mixer as mixer
    # Initialize with larger buffer to prevent audio jitter (8192 samples = ~185ms)
    mixer.init(frequency=44100, size=-16, channels=2, buffer=8192)
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False
    print("Warning: pygame not available, audio playback disabled")

# Import domain models
import sys
from pathlib import Path as PathLib
sys.path.insert(0, str(PathLib(__file__).parent.parent))
from voice_revolver_core.domain.base import (
    PitchCurve, PitchControlPoint,
    ReverbCurve, ReverbControlPoint,
    VolumeCurve, VolumeControlPoint,
    InstrumentalVolumeCurve, InstrumentalVolumeControlPoint,
    NoiseCurve, NoiseControlPoint,
    BlendCurve, BlendControlPoint
)

logger = logging.getLogger(__name__)


class SpectrumEditor(ttk.Frame):
    """
    Interactive spectrum/waveform editor with three modes:
    - Pitching: Click/drag to adjust pitch automation curve
    - Reverb: Click/drag to adjust reverb strength
    - Volume: Click/drag to adjust volume automation
    
    All three curves are stored independently and applied cumulatively.
    """
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        
        # Check dependencies
        if not MATPLOTLIB_AVAILABLE or not LIBROSA_AVAILABLE:
            self._create_disabled_view()
            return
        
        # Audio data
        self.vocal_path: Optional[Path] = None
        self.audio_data: Optional[np.ndarray] = None
        self.sample_rate: Optional[int] = None
        self.duration: float = 0.0
        
        # Enhanced vocals support (Phase 2.7)
        self.enhanced_vocal_path: Optional[Path] = None
        self.enhanced_audio_data: Optional[np.ndarray] = None
        self.has_enhancement = False  # Flag for blend mode availability
        
        # Instrumental audio for instrumental volume mode
        self.instrumental_path: Optional[Path] = None
        self.instrumental_audio_data: Optional[np.ndarray] = None
        self.has_instrumental = False  # Flag for instrumental volume mode availability
        
        # Six independent editing curves (Phase 2.7 adds blend, now adding instrumental_volume)
        self.pitch_curve = PitchCurve()
        self.reverb_curve = ReverbCurve()
        self.volume_curve = VolumeCurve()
        self.instrumental_volume_curve = InstrumentalVolumeCurve()
        self.noise_curve = NoiseCurve()
        self.blend_curve = BlendCurve()  # Phase 2.7: Blend original vs enhanced vocals
        
        # Current editing mode
        self.current_mode = "pitching"
        
        # Interaction mode (add/move/remove control points)
        self.interaction_mode = "add"  # Default to add mode
        
        # Interactive editing state
        self.dragging_point: Optional[Tuple[str, int]] = None  # (curve_type, point_index)
        self.hovered_point: Optional[Tuple[str, int]] = None
        
        # Hover label for displaying values
        self.hover_label = None
        
        # Audio playback state
        self.is_playing = False
        self.playback_position = 0.0
        self.update_timer = None
        self.playback_line = None  # Vertical line showing playback position on plot
        self.programmatic_slider_update = False  # Flag to prevent marker updates during auto-updates
        
        # Zoom factor for spectrum visualization (1.0 = default, 0.5 = zoomed out, 2.0 = zoomed in)
        self.zoom_factor = 1.0
        
        # Callback for applying changes
        self.apply_changes_callback = None
        
        # Create UI
        self._create_widgets()
    
    def _create_disabled_view(self):
        """Show disabled message when dependencies missing"""
        msg_label = ttk.Label(
            self,
            text="Spectrum Editor Unavailable\n\nInstall matplotlib and scipy:\npip install matplotlib scipy",
            justify=tk.CENTER,
            foreground="gray"
        )
        msg_label.pack(expand=True, fill=tk.BOTH, padx=20, pady=20)
    
    def _create_widgets(self):
        """Create matplotlib canvas and mode selector"""
        
        # Main container with canvas on left and tools on right
        main_container = ttk.Frame(self)
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # Canvas frame (left side)
        canvas_frame = ttk.Frame(main_container)
        canvas_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Create matplotlib figure (single plot) - reduced height for better track overview
        self.fig = Figure(figsize=(10, 4), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_xlabel("Time (seconds)")
        self.ax.grid(True, alpha=0.3)
        
        # Embed matplotlib canvas
        self.canvas = FigureCanvasTkAgg(self.fig, master=canvas_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Tool buttons frame (right side - vertical)
        tool_frame = ttk.Frame(main_container, width=65)
        tool_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=10, pady=20)
        tool_frame.pack_propagate(False)  # Maintain width
        
        # Tool buttons label
        tool_label = ttk.Label(tool_frame, text="Tools", font=("Segoe UI", 8, "bold"))
        tool_label.pack(pady=(0, 5))
        
        # Store tool buttons for highlighting
        self.tool_buttons = {}
        
        # Add button
        add_btn = tk.Button(
            tool_frame,
            text="➕\nAdd",
            font=("Segoe UI", 8),
            width=6,
            height=2,
            relief=tk.RAISED,
            bd=2,
            command=lambda: self._set_interaction_mode("add")
        )
        add_btn.pack(pady=3)
        self.tool_buttons["add"] = add_btn
        
        # Move button
        move_btn = tk.Button(
            tool_frame,
            text="✋\nMove",
            font=("Segoe UI", 8),
            width=6,
            height=2,
            relief=tk.RAISED,
            bd=2,
            command=lambda: self._set_interaction_mode("move")
        )
        move_btn.pack(pady=3)
        self.tool_buttons["move"] = move_btn
        
        # Remove button
        remove_btn = tk.Button(
            tool_frame,
            text="❌\nRemove",
            font=("Segoe UI", 8),
            width=6,
            height=2,
            relief=tk.RAISED,
            bd=2,
            command=lambda: self._set_interaction_mode("remove")
        )
        remove_btn.pack(pady=3)
        self.tool_buttons["remove"] = remove_btn
        
        # Reset Mode button
        self.reset_btn = tk.Button(
            tool_frame,
            text="🗑\nReset",
            font=("Segoe UI", 8),
            width=6,
            height=2,
            relief=tk.RAISED,
            bd=2,
            command=self._reset_current_mode
        )
        self.reset_btn.pack(pady=3)
        
        # Volume control (vertical slider below tools)
        ttk.Separator(tool_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
        
        volume_label = ttk.Label(tool_frame, text="Volume", font=("Segoe UI", 8, "bold"))
        volume_label.pack(pady=(5, 3))
        
        self.volume_var = tk.DoubleVar(value=0.7)  # Default 70%
        self.volume_slider = ttk.Scale(
            tool_frame,
            from_=1,   # Top = 100%
            to=0,      # Bottom = 0%
            variable=self.volume_var,
            orient=tk.VERTICAL,
            length=80,
            command=self._on_volume_change
        )
        self.volume_slider.pack(pady=5)
        
        self.volume_label = ttk.Label(tool_frame, text="70%", font=("Segoe UI", 8))
        self.volume_label.pack(pady=(0, 5))
        
        # Set initial button highlighting
        self._update_tool_button_states()
        
        # Audio playback controls (middle - below canvas, above mode selector)
        playback_frame = ttk.Frame(self)
        playback_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=5)
        
        # Playback buttons
        button_frame = ttk.Frame(playback_frame)
        button_frame.pack(side=tk.TOP, pady=5)
        
        self.play_pause_btn = ttk.Button(button_frame, text="▶ Play", command=self._toggle_play_pause, width=12, state='disabled')
        self.play_pause_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = ttk.Button(button_frame, text="⏹ Stop", command=self._stop_audio, width=10, state='disabled')
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        self.apply_btn = ttk.Button(button_frame, text="🔄 Apply Changes", command=self._on_apply_changes, width=15, state='disabled')
        self.apply_btn.pack(side=tk.LEFT, padx=5)
        
        # Time slider and label
        slider_frame = ttk.Frame(playback_frame)
        slider_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)
        
        self.time_label = ttk.Label(slider_frame, text="0:00 / 0:00", width=12)
        self.time_label.pack(side=tk.LEFT, padx=5)
        
        self.time_slider = ttk.Scale(
            slider_frame,
            from_=0,
            to=100,
            orient=tk.HORIZONTAL,
            command=self._on_slider_change
        )
        self.time_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Mode selector frame (bottom)
        mode_frame = ttk.Frame(self)
        mode_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=10)
        
        # Align radio buttons to the left (justify-start)
        button_container = ttk.Frame(mode_frame)
        button_container.pack(side=tk.LEFT, padx=10)
        
        self.mode_var = tk.StringVar(value="pitching")
        
        # Store radio buttons for enable/disable
        self.pitch_radio = ttk.Radiobutton(
            button_container,
            text="Pitching",
            value="pitching",
            variable=self.mode_var,
            command=self._switch_mode
        )
        self.pitch_radio.pack(side=tk.LEFT, padx=20)
        
        self.reverb_radio = ttk.Radiobutton(
            button_container,
            text="Reverb",
            value="reverb",
            variable=self.mode_var,
            command=self._switch_mode
        )
        self.reverb_radio.pack(side=tk.LEFT, padx=20)
        
        self.volume_radio = ttk.Radiobutton(
            button_container,
            text="Volume",
            value="volume",
            variable=self.mode_var,
            command=self._switch_mode
        )
        self.volume_radio.pack(side=tk.LEFT, padx=20)
        
        self.instrumental_volume_radio = ttk.Radiobutton(
            button_container,
            text="Instrumental Vol",
            value="instrumental_volume",
            variable=self.mode_var,
            command=self._switch_mode
        )
        self.instrumental_volume_radio.pack(side=tk.LEFT, padx=20)
        self.instrumental_volume_radio.pack_forget()  # Hidden initially until instrumental loaded
        
        self.noise_radio = ttk.Radiobutton(
            button_container,
            text="Noise Reduction",
            value="noise",
            variable=self.mode_var,
            command=self._switch_mode
        )
        self.noise_radio.pack(side=tk.LEFT, padx=20)
        
        # Blend mode (Phase 2.7 - only shown if has_enhancement)
        self.blend_radio = ttk.Radiobutton(
            button_container,
            text="Blend (Enhanced)",
            value="blend",
            variable=self.mode_var,
            command=self._switch_mode
        )
        self.blend_radio.pack(side=tk.LEFT, padx=20)
        self.blend_radio.pack_forget()  # Hidden initially until enhanced vocals loaded
        
        # Zoom control (right side of mode_frame, same row as mode buttons)
        zoom_control_frame = ttk.Frame(mode_frame)
        zoom_control_frame.pack(side=tk.RIGHT, padx=10)
        
        ttk.Label(zoom_control_frame, text="Zoom:", font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(0, 5))
        
        self.zoom_var = tk.DoubleVar(value=1.0)
        self.zoom_slider = ttk.Scale(
            zoom_control_frame,
            from_=0.5,
            to=2.0,
            variable=self.zoom_var,
            orient=tk.HORIZONTAL,
            length=200,
            command=self._on_zoom_change
        )
        self.zoom_slider.pack(side=tk.LEFT, padx=5)
        
        self.zoom_label = ttk.Label(zoom_control_frame, text="100%", font=("Segoe UI", 9), width=5)
        self.zoom_label.pack(side=tk.LEFT)
        
        # Connect matplotlib events for interactive editing
        self.canvas.mpl_connect('button_press_event', self._on_click)
        self.canvas.mpl_connect('motion_notify_event', self._on_drag)
        self.canvas.mpl_connect('button_release_event', self._on_release)
        self.canvas.mpl_connect('motion_notify_event', self._on_hover)
    
    def load_vocals(self, vocal_path: Path, initial_pitch_shift: float = 0, enhanced_vocal_path: Optional[Path] = None, instrumental_path: Optional[Path] = None):
        """Load separated vocals and display spectrum
        
        Args:
            vocal_path: Path to original vocal audio file
            initial_pitch_shift: Initial pitch shift in semitones (from gender alignment)
            enhanced_vocal_path: Optional path to enhanced vocal audio file (Phase 2.7)
            instrumental_path: Optional path to instrumental audio file (for instrumental volume mode)
        """
        try:
            logger.info(f"Loading vocals for spectrum editor: {vocal_path}")
            
            self.vocal_path = vocal_path
            
            # Load original audio with librosa
            self.audio_data, self.sample_rate = librosa.load(str(vocal_path), sr=None, mono=True)
            self.duration = len(self.audio_data) / self.sample_rate
            
            logger.info(f"Loaded audio: {self.duration:.2f}s at {self.sample_rate}Hz")
            
            # Load enhanced vocals if provided (Phase 2.7)
            self.enhanced_vocal_path = None
            self.enhanced_audio_data = None
            self.has_enhancement = False
            
            if enhanced_vocal_path and enhanced_vocal_path.exists():
                try:
                    logger.info(f"Loading enhanced vocals: {enhanced_vocal_path}")
                    self.enhanced_audio_data, enhanced_sr = librosa.load(str(enhanced_vocal_path), sr=None, mono=True)
                    
                    # Verify sample rates match
                    if enhanced_sr != self.sample_rate:
                        logger.warning(f"Sample rate mismatch: {self.sample_rate}Hz vs {enhanced_sr}Hz, resampling enhanced...")
                        self.enhanced_audio_data = librosa.resample(
                            self.enhanced_audio_data, 
                            orig_sr=enhanced_sr, 
                            target_sr=self.sample_rate
                        )
                    
                    # Ensure same length (pad or trim)
                    if len(self.enhanced_audio_data) < len(self.audio_data):
                        # Pad with zeros
                        padding = len(self.audio_data) - len(self.enhanced_audio_data)
                        self.enhanced_audio_data = np.pad(self.enhanced_audio_data, (0, padding))
                    elif len(self.enhanced_audio_data) > len(self.audio_data):
                        # Trim to match
                        self.enhanced_audio_data = self.enhanced_audio_data[:len(self.audio_data)]
                    
                    self.enhanced_vocal_path = enhanced_vocal_path
                    self.has_enhancement = True
                    logger.info(f"Enhanced vocals loaded ({len(self.enhanced_audio_data)} samples)")
                    
                except Exception as e:
                    logger.error(f"Failed to load enhanced vocals: {e}")
                    self.has_enhancement = False
            
            # Load instrumental audio if provided (for instrumental volume mode)
            self.instrumental_path = None
            self.instrumental_audio_data = None
            self.has_instrumental = False
            
            if instrumental_path and instrumental_path.exists():
                try:
                    logger.info(f"Loading instrumental audio: {instrumental_path}")
                    self.instrumental_audio_data, inst_sr = librosa.load(str(instrumental_path), sr=None, mono=True)
                    
                    # Verify sample rates match
                    if inst_sr != self.sample_rate:
                        logger.warning(f"Sample rate mismatch: {self.sample_rate}Hz vs {inst_sr}Hz, resampling instrumental...")
                        self.instrumental_audio_data = librosa.resample(
                            self.instrumental_audio_data, 
                            orig_sr=inst_sr, 
                            target_sr=self.sample_rate
                        )
                    
                    # Ensure same length (pad or trim)
                    if len(self.instrumental_audio_data) < len(self.audio_data):
                        # Pad with zeros
                        padding = len(self.audio_data) - len(self.instrumental_audio_data)
                        self.instrumental_audio_data = np.pad(self.instrumental_audio_data, (0, padding))
                    elif len(self.instrumental_audio_data) > len(self.audio_data):
                        # Trim to match
                        self.instrumental_audio_data = self.instrumental_audio_data[:len(self.audio_data)]
                    
                    self.instrumental_path = instrumental_path
                    self.has_instrumental = True
                    logger.info(f"Instrumental audio loaded ({len(self.instrumental_audio_data)} samples)")
                    
                except Exception as e:
                    logger.error(f"Failed to load instrumental audio: {e}")
                    self.has_instrumental = False
            
            # Initialize curves with optional pre-populated values
            self.pitch_curve = PitchCurve()
            self.reverb_curve = ReverbCurve()
            self.volume_curve = VolumeCurve()
            self.instrumental_volume_curve = InstrumentalVolumeCurve()
            self.noise_curve = NoiseCurve()
            self.blend_curve = BlendCurve()
            
            # Import control point classes
            from voice_revolver_core.domain.base import PitchControlPoint
            
            # Add initial control points if settings provided
            if initial_pitch_shift != 0:
                # Add 3 points: start, middle, end with same shift value
                self.pitch_curve.control_points.append(PitchControlPoint(0, initial_pitch_shift))
                self.pitch_curve.control_points.append(PitchControlPoint(self.duration / 2, initial_pitch_shift))
                self.pitch_curve.control_points.append(PitchControlPoint(self.duration, initial_pitch_shift))
                logger.info(f"Pre-populated pitch curve with {initial_pitch_shift:.1f} semitones")
            
            # Draw initial view
            self._redraw_spectrum()
            
            # Show/hide blend mode button based on enhancement availability (Phase 2.7)
            if self.has_enhancement:
                self.blend_radio.pack(side=tk.LEFT, padx=20)
                logger.info("Blend mode available (enhanced vocals loaded)")
            else:
                self.blend_radio.pack_forget()
            
            # Show/hide instrumental volume button based on instrumental availability
            if self.has_instrumental:
                self.instrumental_volume_radio.pack(side=tk.LEFT, padx=20)
                logger.info("Instrumental Volume mode available (instrumental audio loaded)")
            else:
                self.instrumental_volume_radio.pack_forget()
            
            # Enable playback controls
            if PYGAME_AVAILABLE:
                self.play_pause_btn.config(state='normal')
                self.apply_btn.config(state='normal')
                self.time_slider.config(to=self.duration)
                self._update_time_label()
            
        except Exception as e:
            logger.error(f"Failed to load vocals: {e}")
            self._show_error(f"Failed to load audio:\n{str(e)}")
    
    def reload_audio_only(self, vocal_path: Path):
        """Reload audio file without resetting curves (for preview updates)"""
        try:
            logger.info(f"Reloading audio (preserving curves): {vocal_path}")
            
            self.vocal_path = vocal_path
            
            # Reload audio with librosa
            self.audio_data, self.sample_rate = librosa.load(str(vocal_path), sr=None, mono=True)
            self.duration = len(self.audio_data) / self.sample_rate
            
            logger.info(f"Reloaded audio: {self.duration:.2f}s (curves preserved)")
            
            # Redraw with existing curves
            self._redraw_spectrum()
            
            # Update slider range
            if PYGAME_AVAILABLE:
                self.time_slider.config(to=self.duration)
                self._update_time_label()
            
        except Exception as e:
            logger.error(f"Failed to reload audio: {e}")
            self._show_error(f"Failed to reload audio:\n{str(e)}")
    
    def reload_instrumental_only(self, instrumental_path: Path):
        """Reload instrumental audio file without resetting curves (for preview updates)"""
        try:
            logger.info(f"Reloading instrumental (preserving curves): {instrumental_path}")
            
            self.instrumental_path = instrumental_path
            
            # Reload instrumental audio with librosa
            self.instrumental_audio_data, inst_sr = librosa.load(str(instrumental_path), sr=None, mono=True)
            
            # Verify sample rates match
            if inst_sr != self.sample_rate:
                logger.warning(f"Sample rate mismatch: {self.sample_rate}Hz vs {inst_sr}Hz, resampling instrumental...")
                self.instrumental_audio_data = librosa.resample(
                    self.instrumental_audio_data, 
                    orig_sr=inst_sr, 
                    target_sr=self.sample_rate
                )
            
            # Ensure same length (pad or trim)
            if len(self.instrumental_audio_data) < len(self.audio_data):
                # Pad with zeros
                padding = len(self.audio_data) - len(self.instrumental_audio_data)
                self.instrumental_audio_data = np.pad(self.instrumental_audio_data, (0, padding))
            elif len(self.instrumental_audio_data) > len(self.audio_data):
                # Trim to match
                self.instrumental_audio_data = self.instrumental_audio_data[:len(self.audio_data)]
            
            self.has_instrumental = True
            logger.info(f"Reloaded instrumental audio: {len(self.instrumental_audio_data)} samples (curves preserved)")
            
            # Redraw if in instrumental volume mode
            if self.current_mode == "instrumental_volume":
                self._redraw_spectrum()
            
        except Exception as e:
            logger.error(f"Failed to reload instrumental: {e}")
            self._show_error(f"Failed to reload instrumental:\n{str(e)}")
    
    def release_audio_file(self):
        """Release audio file handles (stop playback and unload mixer)"""
        try:
            # Stop playback
            if self.is_playing:
                self._stop_audio()
            
            # Unload pygame mixer to release file handle
            if PYGAME_AVAILABLE:
                try:
                    mixer.music.unload()
                    logger.info("Released audio file handle")
                except:
                    pass  # Ignore if nothing was loaded
        except Exception as e:
            logger.error(f"Error releasing audio file: {e}")
    
    def _switch_mode(self):
        """Switch editing mode and redraw visualization"""
        old_mode = self.current_mode
        self.current_mode = self.mode_var.get()
        logger.info(f"Switched to {self.current_mode} mode")
        
        # If switching to/from instrumental_volume mode while playing, restart with correct audio
        if PYGAME_AVAILABLE and self.is_playing:
            mode_changed_audio = (
                (old_mode == "instrumental_volume" and self.current_mode != "instrumental_volume") or
                (old_mode != "instrumental_volume" and self.current_mode == "instrumental_volume")
            )
            if mode_changed_audio:
                # Stop and restart with correct audio file
                was_playing_position = self.playback_position
                mixer.music.stop()
                
                # Determine which audio file to play
                audio_file = self.vocal_path
                if self.current_mode == "instrumental_volume" and self.has_instrumental and self.instrumental_path:
                    audio_file = self.instrumental_path
                
                # Reload and play from same position
                if audio_file:
                    mixer.music.load(str(audio_file))
                    mixer.music.play(start=was_playing_position)
                    # Apply volume from slider
                    mixer.music.set_volume(self.volume_var.get())
                    logger.info(f"Switched playback to {audio_file.name}")
        
        if self.audio_data is not None:
            self._redraw_spectrum()
    
    def _set_interaction_mode(self, mode: str):
        """Set interaction mode (add/move/remove) and update button highlighting"""
        self.interaction_mode = mode
        self._update_tool_button_states()
        logger.info(f"Interaction mode: {mode}")
    
    def _update_tool_button_states(self):
        """Update tool button visual states to highlight selected mode"""
        for mode, button in self.tool_buttons.items():
            if mode == self.interaction_mode:
                # Highlight selected button
                button.config(
                    relief=tk.SUNKEN,
                    bg="#4A90E2",  # Blue background
                    fg="white",
                    bd=3
                )
            else:
                # Normal state
                button.config(
                    relief=tk.RAISED,
                    bg="SystemButtonFace",  # Default button color
                    fg="black",
                    bd=2
                )
    
    def _redraw_spectrum(self):
        """Redraw entire spectrum based on current mode"""
        if self.audio_data is None:
            return
        
        self.ax.clear()
        
        # For blend mode, show dual waveforms instead of single background
        if self.current_mode == "blend" and self.has_enhancement:
            self._draw_blend_view()
        else:
            # Always plot waveform as semi-transparent background (other modes)
            self._plot_waveform_background()
            
            # Overlay mode-specific visualization
            if self.current_mode == "pitching":
                self._draw_pitch_view()
            elif self.current_mode == "reverb":
                self._draw_reverb_view()
            elif self.current_mode == "volume":
                self._draw_volume_view()
            elif self.current_mode == "instrumental_volume":
                self._draw_instrumental_volume_view()
            elif self.current_mode == "noise":
                self._draw_noise_view()
        
        self.ax.set_xlim(0, self.duration)
        self.ax.set_xlabel("Time (seconds)")
        self.ax.grid(True, alpha=0.3)
        
        # Draw playback position marker
        self._draw_playback_marker()
        
        self.canvas.draw()
    
    def _draw_playback_marker(self):
        """Draw vertical line showing current playback position"""
        if self.audio_data is None:
            return
        
        # Draw vertical line at current playback position
        if self.playback_line is not None:
            try:
                self.playback_line.remove()
            except:
                pass
        
        # Only draw if position is within bounds
        if 0 <= self.playback_position <= self.duration:
            self.playback_line = self.ax.axvline(
                self.playback_position,
                color='red',
                linewidth=2,
                linestyle='--',
                alpha=0.7,
                label='Playback Position'
            )
    
    def _plot_waveform_background(self):
        """Plot waveform as semi-transparent background (always visible)"""
        # Downsample for performance
        hop_length = max(1, len(self.audio_data) // 2000)
        times = np.arange(0, len(self.audio_data), hop_length) / self.sample_rate
        samples = self.audio_data[::hop_length]
        
        self.ax.fill_between(times, samples, alpha=0.2, color='lightblue', label='Waveform')
    
    def _draw_pitch_view(self):
        """Draw pitch curve editing view"""
        self.ax.set_ylabel("Pitch Shift (semitones)")
        self.ax.set_title("Pitch Automation (Click to add points, drag to adjust)")
        ylim = 12 * self.zoom_factor
        self.ax.set_ylim(-ylim, ylim)
        
        # Draw zero line
        self.ax.axhline(0, color='gray', linestyle='--', linewidth=1, alpha=0.5)
        
        # Plot existing control points and curve
        if len(self.pitch_curve.control_points) > 0:
            times = [pt.time for pt in self.pitch_curve.control_points]
            shifts = [pt.shift_semitones for pt in self.pitch_curve.control_points]
            
            # Plot control points
            self.ax.scatter(times, shifts, color='red', s=100, zorder=5, label='Control Points')
            
            # Draw straight lines between points (Praat does the actual interpolation)
            if len(times) >= 2:
                self.ax.plot(times, shifts, color='red', linewidth=2, label='Pitch Curve', marker='o', markersize=8)
    
    def _draw_reverb_view(self):
        """Draw reverb strength editing view"""
        self.ax.set_ylabel("Reverb Wet Mix (%)")
        self.ax.set_title("Reverb Strength (Click to add points)")
        ylim = 100 * self.zoom_factor
        self.ax.set_ylim(0, ylim)
        
        # Plot existing control points and curve
        if len(self.reverb_curve.control_points) > 0:
            times = [pt.time for pt in self.reverb_curve.control_points]
            wet_percents = [pt.wet_percent for pt in self.reverb_curve.control_points]
            
            # Plot control points
            self.ax.scatter(times, wet_percents, color='purple', s=100, zorder=5, label='Control Points')
            
            # Draw straight lines between points (like other modes)
            if len(times) >= 2:
                self.ax.plot(times, wet_percents, color='purple', linewidth=2, label='Reverb Curve', marker='o', markersize=8)
    
    def _draw_volume_view(self):
        """Draw volume automation editing view"""
        self.ax.set_ylabel("Volume Adjustment (dB)")
        self.ax.set_title("Volume Automation (Click to add points)")
        ylim = 50 * self.zoom_factor
        self.ax.set_ylim(-ylim, ylim)
        
        # Draw zero line (unity gain)
        self.ax.axhline(0, color='gray', linestyle='--', linewidth=1, alpha=0.5, label='0dB (Unity)')
        
        # Plot existing control points and curve
        if len(self.volume_curve.control_points) > 0:
            times = [pt.time for pt in self.volume_curve.control_points]
            gains = [pt.gain_db for pt in self.volume_curve.control_points]
            
            # Plot control points
            self.ax.scatter(times, gains, color='green', s=100, zorder=5, label='Control Points')
            
            # Draw straight lines between points (actual processing handles interpolation)
            if len(times) >= 2:
                self.ax.plot(times, gains, color='green', linewidth=2, label='Volume Curve', marker='o', markersize=8)
    
    def _draw_instrumental_volume_view(self):
        """Draw instrumental volume automation editing view"""
        self.ax.set_ylabel("Instrumental Volume (dB)")
        self.ax.set_title("Instrumental Volume Automation (Click to add points)")
        ylim = 50 * self.zoom_factor
        self.ax.set_ylim(-ylim, ylim)
        
        # Draw zero line (unity gain)
        self.ax.axhline(0, color='gray', linestyle='--', linewidth=1, alpha=0.5, label='0dB (Unity)')
        
        # Plot existing control points and curve
        if len(self.instrumental_volume_curve.control_points) > 0:
            times = [pt.time for pt in self.instrumental_volume_curve.control_points]
            gains = [pt.gain_db for pt in self.instrumental_volume_curve.control_points]
            
            # Plot control points
            self.ax.scatter(times, gains, color='orange', s=100, zorder=5, label='Control Points')
            
            # Draw straight lines between points
            if len(times) >= 2:
                self.ax.plot(times, gains, color='orange', linewidth=2, label='Instrumental Volume Curve', marker='o', markersize=8)
    
    def _draw_noise_view(self):
        """Draw noise reduction editing view"""
        self.ax.set_ylabel("Noise Reduction (%)")
        self.ax.set_title("Noise Reduction Strength (Click to add points)")
        ylim = 100 * self.zoom_factor
        self.ax.set_ylim(0, ylim)
        
        # Plot existing control points and curve
        if len(self.noise_curve.control_points) > 0:
            times = [pt.time for pt in self.noise_curve.control_points]
            reductions = [pt.reduction_percent for pt in self.noise_curve.control_points]
            
            # Plot control points
            self.ax.scatter(times, reductions, color='orange', s=100, zorder=5, label='Control Points')
            
            # Draw straight lines between points (like pitch and volume modes)
            if len(times) >= 2:
                self.ax.plot(times, reductions, color='orange', linewidth=2, label='Noise Reduction Curve', marker='o', markersize=8)
    
    def _draw_blend_view(self):
        """Draw blend mode with dual waveforms (original + enhanced, Phase 2.7)"""
        if not self.has_enhancement or self.enhanced_audio_data is None:
            # Fallback: no enhanced audio, show error message
            self.ax.text(0.5, 0.5, "Enhanced vocals not available\nCheck 'Improve Vocals' during separation", 
                        ha='center', va='center', transform=self.ax.transAxes,
                        fontsize=12, color='red')
            return
        
        self.ax.set_ylabel("Blend Mix (%)")
        self.ax.set_title("Blend Mode: Original (blue) vs Enhanced (green) - Click to adjust blend curve")
        ylim = 100 * self.zoom_factor
        self.ax.set_ylim(0, ylim)
        
        # Downsample for performance
        hop_length = max(1, len(self.audio_data) // 2000)
        
        # Sample both waveforms - ensure they have the same length
        original_samples = self.audio_data[::hop_length]
        enhanced_samples = self.enhanced_audio_data[::hop_length]
        
        # Ensure both arrays have the same length (trim to shorter one)
        min_length = min(len(original_samples), len(enhanced_samples))
        original_samples = original_samples[:min_length]
        enhanced_samples = enhanced_samples[:min_length]
        
        # Create time axis matching the sample length
        times = np.arange(min_length) * hop_length / self.sample_rate
        
        # Normalize to 0-100 (map [-1, 1] audio range to [0, 100] percentage)
        original_norm = ((original_samples + 1) / 2) * 100
        enhanced_norm = ((enhanced_samples + 1) / 2) * 100
        
        # Plot original waveform (light blue, semi-transparent)
        self.ax.fill_between(times, original_norm, alpha=0.3, color='lightblue', label='Original Vocals')
        
        # Plot enhanced waveform (light green, semi-transparent, overlaid)
        self.ax.fill_between(times, enhanced_norm, alpha=0.3, color='lightgreen', label='Enhanced Vocals')
        
        # Draw 50% reference line
        self.ax.axhline(50, color='gray', linestyle='--', linewidth=1, alpha=0.5, label='50% Mix')
        
        # Plot blend curve control points
        if len(self.blend_curve.control_points) > 0:
            times = [pt.time for pt in self.blend_curve.control_points]
            enhanced_percents = [pt.enhanced_percent for pt in self.blend_curve.control_points]
            
            # Plot control points (yellow for high visibility)
            self.ax.scatter(times, enhanced_percents, color='gold', s=100, zorder=5, 
                          edgecolors='black', linewidths=2, label='Blend Points')
            
            # Draw blend curve line
            if len(times) >= 2:
                self.ax.plot(times, enhanced_percents, color='gold', linewidth=3, 
                           label='Blend Curve (0%=Original, 100%=Enhanced)', 
                           marker='o', markersize=10, markeredgecolor='black', markeredgewidth=2)
        
        # Add legend for clarity
        self.ax.legend(loc='upper right', fontsize=8)
    
    def _on_click(self, event):
        """Handle mouse click - add, move, or remove control point based on mode"""
        if event.inaxes != self.ax or event.xdata is None or event.ydata is None:
            return
        
        if event.button != 1:  # Only handle left click
            return
        
        time = event.xdata
        value = event.ydata
        
        # Check if clicking near existing point
        existing_point = self._find_nearby_point(time, value)
        
        if self.interaction_mode == "add":
            # Add mode: add point if not clicking on existing one
            if not existing_point:
                self._add_control_point(time, value)
        
        elif self.interaction_mode == "move":
            # Move mode: start dragging if clicking on existing point
            if existing_point:
                self.dragging_point = existing_point
        
        elif self.interaction_mode == "remove":
            # Remove mode: delete point if clicking on existing one
            if existing_point:
                self._remove_control_point(existing_point)
                self._redraw_spectrum()
    
    def _on_drag(self, event):
        """Handle mouse drag - move control point"""
        if self.dragging_point is None or event.xdata is None or event.ydata is None:
            return
        
        curve_type, point_index = self.dragging_point
        
        # Constrain to valid time range
        new_time = max(0, min(self.duration, event.xdata))
        new_value = event.ydata
        
        # Update control point
        if curve_type == "pitch":
            new_value = max(-12, min(12, new_value))
            self.pitch_curve.control_points[point_index].time = new_time
            self.pitch_curve.control_points[point_index].shift_semitones = new_value
        elif curve_type == "reverb":
            new_value = max(0, min(100, new_value))
            self.reverb_curve.control_points[point_index].time = new_time
            self.reverb_curve.control_points[point_index].wet_percent = new_value
        elif curve_type == "volume":
            new_value = max(-50, min(50, new_value))
            self.volume_curve.control_points[point_index].time = new_time
            self.volume_curve.control_points[point_index].gain_db = new_value
        elif curve_type == "instrumental_volume":
            new_value = max(-50, min(50, new_value))
            self.instrumental_volume_curve.control_points[point_index].time = new_time
            self.instrumental_volume_curve.control_points[point_index].gain_db = new_value
        elif curve_type == "noise":
            new_value = max(0, min(100, new_value))
            self.noise_curve.control_points[point_index].time = new_time
            self.noise_curve.control_points[point_index].reduction_percent = new_value
        elif curve_type == "blend":
            new_value = max(0, min(100, new_value))
            self.blend_curve.control_points[point_index].time = new_time
            self.blend_curve.control_points[point_index].enhanced_percent = new_value
        
        # Redraw
        self._redraw_spectrum()
    
    def _on_release(self, event):
        """Handle mouse release - stop dragging"""
        if self.dragging_point:
            # Sort control points by time after drag
            curve_type, _ = self.dragging_point
            if curve_type == "pitch":
                self.pitch_curve.control_points.sort(key=lambda pt: pt.time)
            elif curve_type == "reverb":
                self.reverb_curve.control_points.sort(key=lambda pt: pt.time)
            elif curve_type == "volume":
                self.volume_curve.control_points.sort(key=lambda pt: pt.time)
            elif curve_type == "instrumental_volume":
                self.instrumental_volume_curve.control_points.sort(key=lambda pt: pt.time)
            elif curve_type == "noise":
                self.noise_curve.control_points.sort(key=lambda pt: pt.time)
            elif curve_type == "blend":
                self.blend_curve.control_points.sort(key=lambda pt: pt.time)
            
            self.dragging_point = None
            self._redraw_spectrum()
    
    def _on_hover(self, event):
        """Handle mouse hover - display current value in bottom right corner"""
        # Only show label if audio is loaded and mouse is within axes
        if self.audio_data is None or event.inaxes != self.ax:
            # Hide label when not hovering over plot
            if self.hover_label is not None:
                self.hover_label.set_visible(False)
                self.canvas.draw_idle()
            return
        
        # Get mouse position
        ydata = event.ydata
        if ydata is None:
            return
        
        # Format label text based on current mode
        if self.current_mode == "pitching":
            # Clamp to pitch range
            pitch = max(-12, min(12, ydata))
            label_text = f"Pitch: {pitch:+.1f} semitones"
        elif self.current_mode == "reverb":
            # Clamp to reverb range
            reverb = max(0, min(100, ydata))
            label_text = f"Reverb: {reverb:.0f}%"
        elif self.current_mode == "volume":
            # Clamp to volume range
            volume = max(-50, min(50, ydata))
            label_text = f"Volume: {volume:+.1f} dB"
        elif self.current_mode == "instrumental_volume":
            # Clamp to instrumental volume range
            inst_vol = max(-50, min(50, ydata))
            label_text = f"Instrumental: {inst_vol:+.1f} dB"
        elif self.current_mode == "noise":
            # Clamp to noise reduction range
            noise = max(0, min(100, ydata))
            label_text = f"Noise Reduction: {noise:.0f}%"
        elif self.current_mode == "blend":
            # Clamp to blend range
            blend = max(0, min(100, ydata))
            label_text = f"Enhanced: {blend:.0f}%"
        else:
            return
        
        # Create or update hover label
        if self.hover_label is None:
            # Create label in bottom right corner (in axes coordinates)
            self.hover_label = self.ax.text(
                0.98, 0.02,  # Bottom right (98% right, 2% up from bottom)
                label_text,
                transform=self.ax.transAxes,  # Use axes coordinates (0-1)
                fontsize=10,
                bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow', alpha=0.8),
                verticalalignment='bottom',
                horizontalalignment='right',
                zorder=10  # Draw on top
            )
        else:
            # Update existing label
            self.hover_label.set_text(label_text)
            self.hover_label.set_visible(True)
        
        # Redraw canvas efficiently
        self.canvas.draw_idle()
    
    def _find_nearby_point(self, time: float, value: float) -> Optional[Tuple[str, int]]:
        """Find control point near click position"""
        threshold_time = self.duration * 0.02  # 2% of duration
        threshold_value = 2.0  # 2 units in Y-axis
        
        # Check current mode's curve
        if self.current_mode == "pitching":
            for i, pt in enumerate(self.pitch_curve.control_points):
                if abs(pt.time - time) < threshold_time and abs(pt.shift_semitones - value) < threshold_value:
                    return ("pitch", i)
        elif self.current_mode == "reverb":
            threshold_value = 10.0  # 10% for reverb
            for i, pt in enumerate(self.reverb_curve.control_points):
                if abs(pt.time - time) < threshold_time and abs(pt.wet_percent - value) < threshold_value:
                    return ("reverb", i)
        elif self.current_mode == "volume":
            for i, pt in enumerate(self.volume_curve.control_points):
                if abs(pt.time - time) < threshold_time and abs(pt.gain_db - value) < threshold_value:
                    return ("volume", i)
        elif self.current_mode == "instrumental_volume":
            for i, pt in enumerate(self.instrumental_volume_curve.control_points):
                if abs(pt.time - time) < threshold_time and abs(pt.gain_db - value) < threshold_value:
                    return ("instrumental_volume", i)
        elif self.current_mode == "noise":
            threshold_value = 10.0  # 10% for noise reduction
            for i, pt in enumerate(self.noise_curve.control_points):
                if abs(pt.time - time) < threshold_time and abs(pt.reduction_percent - value) < threshold_value:
                    return ("noise", i)
        elif self.current_mode == "blend":
            threshold_value = 10.0  # 10% for blend
            for i, pt in enumerate(self.blend_curve.control_points):
                if abs(pt.time - time) < threshold_time and abs(pt.enhanced_percent - value) < threshold_value:
                    return ("blend", i)
        
        return None
    
    def _add_control_point(self, time: float, value: float):
        """Add new control point at specified position"""
        if self.current_mode == "pitching":
            value = max(-12, min(12, value))
            self.pitch_curve.control_points.append(PitchControlPoint(time, value))
            self.pitch_curve.control_points.sort(key=lambda pt: pt.time)
        elif self.current_mode == "reverb":
            value = max(0, min(100, value))
            self.reverb_curve.control_points.append(ReverbControlPoint(time, value))
            self.reverb_curve.control_points.sort(key=lambda pt: pt.time)
        elif self.current_mode == "volume":
            value = max(-50, min(50, value))
            self.volume_curve.control_points.append(VolumeControlPoint(time, value))
            self.volume_curve.control_points.sort(key=lambda pt: pt.time)
        elif self.current_mode == "instrumental_volume":
            value = max(-50, min(50, value))
            self.instrumental_volume_curve.control_points.append(InstrumentalVolumeControlPoint(time, value))
            self.instrumental_volume_curve.control_points.sort(key=lambda pt: pt.time)
        elif self.current_mode == "noise":
            value = max(0, min(100, value))
            self.noise_curve.control_points.append(NoiseControlPoint(time, value))
            self.noise_curve.control_points.sort(key=lambda pt: pt.time)
        elif self.current_mode == "blend":
            value = max(0, min(100, value))
            self.blend_curve.control_points.append(BlendControlPoint(time, value))
            self.blend_curve.control_points.sort(key=lambda pt: pt.time)
        
        logger.info(f"Added {self.current_mode} control point at {time:.2f}s, value={value:.2f}")
        self._redraw_spectrum()
    
    def _remove_control_point(self, point_ref: Tuple[str, int]):
        """Remove existing control point"""
        curve_type, point_index = point_ref
        
        if curve_type == "pitch" and point_index < len(self.pitch_curve.control_points):
            removed = self.pitch_curve.control_points.pop(point_index)
            logger.info(f"Removed pitch control point at {removed.time:.2f}s")
        elif curve_type == "reverb" and point_index < len(self.reverb_curve.control_points):
            removed = self.reverb_curve.control_points.pop(point_index)
            logger.info(f"Removed reverb control point at {removed.time:.2f}s")
        elif curve_type == "volume" and point_index < len(self.volume_curve.control_points):
            removed = self.volume_curve.control_points.pop(point_index)
            logger.info(f"Removed volume control point at {removed.time:.2f}s")
        elif curve_type == "instrumental_volume" and point_index < len(self.instrumental_volume_curve.control_points):
            removed = self.instrumental_volume_curve.control_points.pop(point_index)
            logger.info(f"Removed instrumental volume control point at {removed.time:.2f}s")
        elif curve_type == "noise" and point_index < len(self.noise_curve.control_points):
            removed = self.noise_curve.control_points.pop(point_index)
            logger.info(f"Removed noise control point at {removed.time:.2f}s")
        elif curve_type == "blend" and point_index < len(self.blend_curve.control_points):
            removed = self.blend_curve.control_points.pop(point_index)
            logger.info(f"Removed blend control point at {removed.time:.2f}s")
    
    def get_all_curves(self) -> dict:
        """Return all editing curves for processing (includes blend and instrumental_volume)"""
        return {
            'pitch': self.pitch_curve,
            'reverb': self.reverb_curve,
            'volume': self.volume_curve,
            'instrumental_volume': self.instrumental_volume_curve,
            'noise': self.noise_curve,
            'blend': self.blend_curve
        }
    
    def reset_current_curve(self):
        """Reset only the currently active curve"""
        if self.current_mode == "pitching":
            self.pitch_curve = PitchCurve()
        elif self.current_mode == "reverb":
            self.reverb_curve = ReverbCurve()
        elif self.current_mode == "volume":
            self.volume_curve = VolumeCurve()
        elif self.current_mode == "instrumental_volume":
            self.instrumental_volume_curve = InstrumentalVolumeCurve()
        elif self.current_mode == "noise":
            self.noise_curve = NoiseCurve()
        elif self.current_mode == "blend":
            self.blend_curve = BlendCurve()
        
        logger.info(f"Reset {self.current_mode} curve")
        self._redraw_spectrum()
    
    def reset_all_curves(self):
        """Reset all curves to defaults (includes blend and instrumental_volume)"""
        self.pitch_curve = PitchCurve()
        self.reverb_curve = ReverbCurve()
        self.volume_curve = VolumeCurve()
        self.instrumental_volume_curve = InstrumentalVolumeCurve()
        self.noise_curve = NoiseCurve()
        self.blend_curve = BlendCurve()
        
        logger.info("Reset all curves")
        self._redraw_spectrum()
    
    def set_apply_changes_callback(self, callback):
        """Set callback function to be called when Apply Changes is clicked"""
        self.apply_changes_callback = callback
    
    def _on_apply_changes(self):
        """Handle Apply Changes button click"""
        if self.apply_changes_callback:
            # Stop playback before applying changes
            if self.is_playing:
                self._stop_audio()
            
            # Call the callback (will be handled by main_tk.py)
            self.apply_changes_callback()
        else:
            logger.warning("No apply changes callback set")
    
    def _reset_current_mode(self):
        """Clear all control points for the current mode"""
        if self.current_mode == "pitching":
            self.pitch_curve.control_points.clear()
            logger.info("Reset pitch curve")
        elif self.current_mode == "reverb":
            self.reverb_curve.control_points.clear()
            logger.info("Reset reverb curve")
        elif self.current_mode == "volume":
            self.volume_curve.control_points.clear()
            logger.info("Reset volume curve")
        elif self.current_mode == "instrumental_volume":
            self.instrumental_volume_curve.control_points.clear()
            logger.info("Reset instrumental volume curve")
        elif self.current_mode == "noise":
            self.noise_curve.control_points.clear()
            logger.info("Reset noise curve")
        elif self.current_mode == "blend":
            self.blend_curve.control_points.clear()
            logger.info("Reset blend curve")
        
        # Redraw spectrum
        self._redraw_spectrum()
    
    def _on_volume_change(self, value):
        """Handle volume slider changes"""
        try:
            volume = float(value)
            # Update volume label
            self.volume_label.config(text=f"{int(volume * 100)}%")
            # Apply to playback
            if PYGAME_AVAILABLE:
                mixer.music.set_volume(volume)
        except Exception as e:
            logger.error(f"Volume change error: {e}")
    
    def _on_zoom_change(self, value):
        """Handle zoom slider changes"""
        try:
            self.zoom_factor = float(value)
            # Update zoom label to show percentage
            self.zoom_label.config(text=f"{int(self.zoom_factor * 100)}%")
            # Redraw spectrum with new zoom factor
            self._redraw_spectrum()
        except Exception as e:
            logger.error(f"Zoom change error: {e}")
    
    def set_enabled(self, enabled: bool):
        """Enable or disable the spectrum editor"""
        state = 'normal' if enabled else 'disabled'
        
        # Disable/enable radio buttons
        if hasattr(self, 'pitch_radio'):
            self.pitch_radio.config(state=state)
        if hasattr(self, 'reverb_radio'):
            self.reverb_radio.config(state=state)
        if hasattr(self, 'volume_radio'):
            self.volume_radio.config(state=state)
        if hasattr(self, 'noise_radio'):
            self.noise_radio.config(state=state)
        
        # Disable/enable playback buttons
        if hasattr(self, 'play_pause_btn'):
            # Only enable play if audio is loaded
            if enabled and self.vocal_path:
                self.play_pause_btn.config(state='normal')
                self.apply_btn.config(state='normal')
            else:
                self.play_pause_btn.config(state='disabled')
                self.apply_btn.config(state='disabled')
                self._stop_audio()  # Stop playback if disabling
        
        # Disable/enable canvas interaction
        if hasattr(self, 'canvas'):
            canvas_widget = self.canvas.get_tk_widget()
            if enabled:
                canvas_widget.config(cursor='crosshair')
            else:
                canvas_widget.config(cursor='arrow')
    
    def _toggle_play_pause(self):
        """Toggle between play and pause"""
        if self.is_playing:
            self._pause_audio()
        else:
            self._play_audio()
    
    def _play_audio(self):
        """Play audio from current position"""
        if not PYGAME_AVAILABLE:
            return
        
        # Determine which audio file to play based on current mode
        audio_file = self.vocal_path
        if self.current_mode == "instrumental_volume" and self.has_instrumental and self.instrumental_path:
            audio_file = self.instrumental_path
        
        if not audio_file:
            return
        
        try:
            if not self.is_playing:
                # Load and play from current position
                mixer.music.load(str(audio_file))
                mixer.music.play(start=self.playback_position)
                # Apply volume from slider
                mixer.music.set_volume(self.volume_var.get())
                self.is_playing = True
                
                # Update button states
                self.play_pause_btn.config(text="⏸ Pause")
                self.stop_btn.config(state='normal')
                
                # Start position update timer
                self._update_playback_position()
                
                logger.info(f"Playing audio from {self.playback_position:.2f}s")
        except Exception as e:
            logger.error(f"Failed to play audio: {e}")
    
    def _pause_audio(self):
        """Pause audio playback"""
        if not PYGAME_AVAILABLE or not self.is_playing:
            return
        
        try:
            mixer.music.pause()
            self.is_playing = False
            
            # Update button states
            self.play_pause_btn.config(text="▶ Play")
            
            # Cancel update timer
            if self.update_timer:
                self.after_cancel(self.update_timer)
                self.update_timer = None
            
            # Update playback marker now that playback is paused
            self._update_playback_marker()
            
            logger.info("Audio paused")
        except Exception as e:
            logger.error(f"Failed to pause audio: {e}")
    
    def _stop_audio(self):
        """Stop audio playback"""
        if not PYGAME_AVAILABLE:
            return
        
        try:
            mixer.music.stop()
            self.is_playing = False
            self.playback_position = 0.0
            
            # Update button states
            self.play_pause_btn.config(text="▶ Play")
            self.stop_btn.config(state='disabled')
            
            # Cancel update timer
            if self.update_timer:
                self.after_cancel(self.update_timer)
                self.update_timer = None
            
            # Reset slider and playback marker
            self.time_slider.set(0)
            self._update_time_label()
            self._update_playback_marker()
            
            logger.info("Audio stopped")
        except Exception as e:
            logger.error(f"Failed to stop audio: {e}")
    
    def _on_slider_change(self, value):
        """Handle slider position change (seeking)"""
        if not PYGAME_AVAILABLE or not self.vocal_path:
            return
        
        # Ignore programmatic slider updates (from playback loop)
        if self.programmatic_slider_update:
            return
        
        try:
            position = float(value)
            
            # User is manually seeking with slider
            if not self.is_playing:
                # Update marker when paused
                self.playback_position = position
                self._update_time_label()
                self._update_playback_marker()
            else:
                # Seek during playback - restart from new position
                self.playback_position = position
                mixer.music.stop()
                # Use appropriate audio file based on current mode
                audio_file = self.vocal_path
                if self.current_mode == "instrumental_volume" and self.has_instrumental and self.instrumental_path:
                    audio_file = self.instrumental_path
                mixer.music.load(str(audio_file))
                mixer.music.play(start=self.playback_position)
                # Apply volume from slider
                mixer.music.set_volume(self.volume_var.get())
                self._update_time_label()
                # Don't update marker during playback - causes jitter
        except Exception as e:
            logger.error(f"Failed to seek audio: {e}")
    
    def _update_playback_position(self):
        """Update playback position and slider (called periodically during playback)"""
        if not self.is_playing:
            return
        
        try:
            # Increment position (200ms intervals for less CPU usage)
            self.playback_position += 0.2
            
            # Check if playback finished
            if self.playback_position >= self.duration:
                self._stop_audio()
                return
            
            # Update slider and label only (no matplotlib updates during playback)
            # Use flag to prevent slider callback from triggering marker update
            self.programmatic_slider_update = True
            self.time_slider.set(self.playback_position)
            self.programmatic_slider_update = False
            
            self._update_time_label()
            
            # Schedule next update (200ms for smoother audio)
            self.update_timer = self.after(200, self._update_playback_position)
        except Exception as e:
            logger.error(f"Failed to update playback position: {e}")
            self._stop_audio()
    
    def _update_playback_marker(self):
        """Update playback position marker on plot efficiently (without full redraw)"""
        if self.audio_data is None:
            return
        
        try:
            # Remove old line
            if self.playback_line is not None:
                try:
                    self.playback_line.remove()
                except:
                    pass
            
            # Draw new line at current position
            if 0 <= self.playback_position <= self.duration:
                self.playback_line = self.ax.axvline(
                    self.playback_position,
                    color='red',
                    linewidth=2,
                    linestyle='--',
                    alpha=0.7
                )
                
                # Efficient redraw (only update canvas, don't redraw everything)
                self.canvas.draw_idle()
        except Exception as e:
            logger.error(f"Failed to update playback marker: {e}")
    
    def _update_time_label(self):
        """Update time label to show current/total time"""
        current_min = int(self.playback_position // 60)
        current_sec = int(self.playback_position % 60)
        total_min = int(self.duration // 60)
        total_sec = int(self.duration % 60)
        
        self.time_label.config(text=f"{current_min}:{current_sec:02d} / {total_min}:{total_sec:02d}")
    
    def _show_error(self, message: str):
        """Display error message on canvas"""
        self.ax.clear()
        self.ax.text(
            0.5, 0.5, message,
            horizontalalignment='center',
            verticalalignment='center',
            transform=self.ax.transAxes,
            fontsize=12,
            color='red'
        )
        self.canvas.draw()
