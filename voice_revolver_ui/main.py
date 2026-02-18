"""
Voice Revolver AI - Desktop UI
PyQt-based desktop application
"""

import sys
import os
from pathlib import Path
from datetime import datetime
import json
import logging

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QFileDialog, QProgressBar,
    QSlider, QComboBox, QGroupBox, QMessageBox, QFrame,
    QStatusBar, QMenuBar, QMenu, QDialog, QDialogButtonBox,
    QTextEdit, QListWidget, QListWidgetItem
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QUrl
from PyQt6.QtGui import QAction, QIcon, QFont
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput


# Setup logging
def setup_logging(app_data_path: Path):
    """Setup application logging"""
    log_dir = app_data_path / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = log_dir / f"app_{datetime.now().strftime('%Y%m%d')}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] %(levelname)s: %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    return logging.getLogger("voice_revolver")


class StartupDialog(QDialog):
    """
    Startup dialog for device selection.
    Auto-detects GPU and lets user choose GPU/CPU.
    """
    
    device_selected = pyqtSignal(str)  # 'cuda' or 'cpu'
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Voice Revolver AI - Setup")
        self.setMinimumSize(500, 350)
        self.setModal(True)
        
        self._has_cuda = False
        self._cuda_device_name = ""
        self.selected_device = "cpu"  # Default to CPU
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize the UI"""
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("Voice Revolver AI")
        title.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Subtitle
        subtitle = QLabel("Choose your processing device")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)
        
        layout.addSpacing(20)
        
        # Hardware info group
        info_group = QGroupBox("System Information")
        info_layout = QVBoxLayout()
        
        self.gpu_label = QLabel("GPU: Detecting...")
        info_layout.addWidget(self.gpu_label)
        
        self.cpu_label = QLabel("CPU: Available")
        info_layout.addWidget(self.cpu_label)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # Device selection
        selection_group = QGroupBox("Select Processing Device")
        selection_layout = QVBoxLayout()
        
        self.btn_gpu = QPushButton("GPU (Recommended)")
        self.btn_gpu.setCheckable(True)
        self.btn_gpu.clicked.connect(lambda: self.select_device("cuda"))
        selection_layout.addWidget(self.btn_gpu)
        
        self.btn_cpu = QPushButton("CPU")
        self.btn_cpu.setCheckable(True)
        self.btn_cpu.clicked.connect(lambda: self.select_device("cpu"))
        selection_layout.addWidget(self.btn_cpu)
        
        self.device_info_label = QLabel("")
        self.device_info_label.setStyleSheet("color: gray; font-size: 10pt;")
        selection_layout.addWidget(self.device_info_label)
        
        selection_group.setLayout(selection_layout)
        layout.addWidget(selection_group)
        
        # Note
        note = QLabel("Note: GPU is much faster but requires NVIDIA GPU with CUDA.")
        note.setStyleSheet("color: gray; font-size: 9pt;")
        layout.addWidget(note)
        
        # Continue button
        self.btn_continue = QPushButton("Continue")
        self.btn_continue.setEnabled(False)
        self.btn_continue.clicked.connect(self.accept)
        layout.addWidget(self.btn_continue)
        
        self.setLayout(layout)
        
        # Delay hardware detection to avoid blocking UI
        QTimer.singleShot(100, self.detect_hardware)
    
    def detect_hardware(self):
        """Detect available hardware"""
        try:
            import torch
            self._has_cuda = torch.cuda.is_available()
            
            if self._has_cuda:
                self._cuda_device_name = torch.cuda.get_device_name(0)
                self.gpu_label.setText(f"GPU: {self._cuda_device_name}")
                self.btn_gpu.setEnabled(True)
                self.btn_gpu.setText("GPU (Recommended)")
                self.select_device("cuda")  # Default to GPU if available
            else:
                self.gpu_label.setText("GPU: Not detected")
                self.btn_gpu.setEnabled(True)  # Keep enabled so user can still try
                self.btn_gpu.setText("GPU (May not work)")
                self.select_device("cpu")
        except (ImportError, OSError, Exception) as e:
            # Torch not available or DLL issues (common on Windows)
            self._has_cuda = False
            self._cuda_device_name = ""
            if isinstance(e, OSError):
                error_msg = "DLL error - may still work"
            elif isinstance(e, ImportError):
                error_msg = "not installed"
            else:
                error_msg = "error"
            self.gpu_label.setText(f"GPU: Detection failed ({error_msg})")
            self.btn_gpu.setEnabled(True)  # Keep enabled so user can still try
            self.btn_gpu.setText("GPU (Detection failed)")
            self.select_device("cpu")
            # Suppress the error - app should continue with CPU
    
    def select_device(self, device: str):
        """Handle device selection"""
        if device == "cuda":
            self.btn_gpu.setChecked(True)
            self.btn_cpu.setChecked(False)
            self.device_info_label.setText("Using GPU for faster processing")
        else:
            self.btn_gpu.setChecked(False)
            self.btn_cpu.setChecked(True)
            self.device_info_label.setText("Using CPU (slower but works on any computer)")
        
        self.selected_device = device
        self.btn_continue.setEnabled(True)


class LoadingDialog(QDialog):
    """
    Loading dialog showing download progress.
    """
    
    finished = pyqtSignal()  # Finished loading
    
    def __init__(self, device: str, parent=None):
        super().__init__(parent)
        self._device = device
        self.setWindowTitle("Voice Revolver AI - Loading")
        self.setMinimumSize(450, 250)
        self.setModal(True)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowTitleHint | Qt.WindowType.CustomizeWindowHint)
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize the UI"""
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("Setting up Voice Revolver AI")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        layout.addSpacing(10)
        
        # Status
        self.status_label = QLabel("Initializing...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        # Detail label
        self.detail_label = QLabel("")
        self.detail_label.setStyleSheet("color: gray; font-size: 9pt;")
        self.detail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.detail_label)
        
        layout.addStretch()
        
        # Device info
        device_text = f"Using device: {'GPU' if self._device == 'cuda' else 'CPU'}"
        self.device_label = QLabel(device_text)
        self.device_label.setStyleSheet("color: gray; font-size: 9pt;")
        layout.addWidget(self.device_label)
        
        self.setLayout(layout)
    
    def update_progress(self, percentage: int, status: str, detail: str = ""):
        """Update progress"""
        self.progress_bar.setValue(percentage)
        self.status_label.setText(status)
        self.detail_label.setText(detail)
    
    def closeEvent(self, event):
        """Handle close"""
        event.ignore()


class ProcessingWorker(QThread):
    """Worker thread for audio processing"""
    
    progress = pyqtSignal(int, str)  # percentage, message
    finished = pyqtSignal(bool, str)  # success, output_path_or_error
    
    def __init__(self, service, original_path, reference_path, voice_params, output_format):
        super().__init__()
        self._service = service
        self._original_path = original_path
        self._reference_path = reference_path
        self._voice_params = voice_params
        self._output_format = output_format
    
    def run(self):
        """Run the processing"""
        import logging
        logger = logging.getLogger(__name__)
        
        def progress_callback(percentage, message):
            self.progress.emit(percentage, message)
        
        try:
            logger.info("ProcessingWorker: Starting processing...")
            result_path, error_code, message = self._service.process(
                self._original_path,
                self._reference_path,
                self._voice_params,
                self._output_format,
                progress_callback=progress_callback
            )
            
            logger.info(f"ProcessingWorker: Processing complete - result_path={result_path}")
            
            if result_path:
                self.finished.emit(True, str(result_path))
            else:
                self.finished.emit(False, message)
                
        except Exception as e:
            logger.error(f"ProcessingWorker: Exception occurred: {e}")
            import traceback
            traceback.print_exc()
            self.finished.emit(False, str(e))
        finally:
            logger.info("ProcessingWorker: Thread finished")


class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self, device: str):
        super().__init__()
        
        self._device = device
        
        # Initialize paths
        self.app_data_path = self._get_app_data_path()
        self.app_data_path.mkdir(parents=True, exist_ok=True)
        
        # Setup logging
        self.logger = setup_logging(self.app_data_path)
        self.logger.info(f"Starting Voice Revolver AI with device: {device}")
        
        # Core components
        self.progress_tracker = None
        self.compute_controller = None
        self.model_manager = None
        self.file_manager = None
        self.project_service = None
        self.voice_replacement_service = None
        self.ffmpeg_checker = None
        
        # Processing worker
        self.worker = None
        
        # State
        self.current_project = None
        self.original_audio_path: Path = None
        self.reference_voice_path: Path = None
        self.processed_output_path: Path = None
        self.is_processing = False
        
        # Setup UI
        self.init_ui()
        
        # Initialize core after UI
        QTimer.singleShot(100, self.initialize_core)
    
    def _get_app_data_path(self) -> Path:
        """Get application data directory"""
        if sys.platform == "win32":
            base = Path(os.environ.get('LOCALAPPDATA', Path.home()))
        elif sys.platform == "darwin":
            base = Path.home() / "Library" / "Application Support"
        else:
            base = Path.home() / ".local" / "share"
        
        return base / "VoiceRevolverAI"
    
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Voice Revolver AI")
        self.setMinimumSize(800, 600)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        
        # Menu bar
        self._create_menu_bar()
        
        # File selection group
        files_group = self._create_files_group()
        main_layout.addWidget(files_group)
        
        # Settings group
        settings_group = self._create_settings_group()
        main_layout.addWidget(settings_group)
        
        # Progress group
        progress_group = self._create_progress_group()
        main_layout.addWidget(progress_group)
        
        # Preview group
        preview_group = self._create_preview_group()
        main_layout.addWidget(preview_group)
        
        # Action buttons
        action_layout = self._create_action_buttons()
        main_layout.addLayout(action_layout)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
        
        self.logger.info("UI initialized")
    
    def _create_menu_bar(self):
        """Create menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        new_action = QAction("New Project", self)
        new_action.triggered.connect(self.new_project)
        file_menu.addAction(new_action)
        
        open_action = QAction("Open Project", self)
        open_action.triggered.connect(self.open_project)
        file_menu.addAction(open_action)
        
        save_action = QAction("Save Project", self)
        save_action.triggered.connect(self.save_project)
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Settings menu
        settings_menu = menubar.addMenu("Settings")
        
        device_action = QAction("Compute Device", self)
        device_action.triggered.connect(self.show_device_settings)
        settings_menu.addAction(device_action)
        
        # Help menu
        help_menu = menubar.addMenu("Help")
        
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def _create_files_group(self) -> QGroupBox:
        """Create file selection group"""
        group = QGroupBox("Files")
        layout = QVBoxLayout()
        
        # Original audio
        orig_layout = QHBoxLayout()
        orig_layout.addWidget(QLabel("Original Song:"))
        self.original_file_label = QLabel("No file selected")
        self.original_file_label.setStyleSheet("color: gray;")
        orig_layout.addWidget(self.original_file_label, 1)
        self.btn_original = QPushButton("Browse")
        self.btn_original.clicked.connect(self.browse_original_file)
        orig_layout.addWidget(self.btn_original)
        layout.addLayout(orig_layout)
        
        # Reference voice
        ref_layout = QHBoxLayout()
        ref_layout.addWidget(QLabel("Reference Voice:"))
        self.reference_file_label = QLabel("No file selected")
        self.reference_file_label.setStyleSheet("color: gray;")
        ref_layout.addWidget(self.reference_file_label, 1)
        self.btn_reference = QPushButton("Browse")
        self.btn_reference.clicked.connect(self.browse_reference_file)
        ref_layout.addWidget(self.btn_reference)
        layout.addLayout(ref_layout)
        
        group.setLayout(layout)
        return group
    
    def _create_settings_group(self) -> QGroupBox:
        """Create settings group"""
        group = QGroupBox("Settings")
        layout = QVBoxLayout()
        
        # Output format
        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel("Output Format:"))
        self.format_combo = QComboBox()
        self.format_combo.addItems(["MP3", "WAV", "FLAC"])
        format_layout.addWidget(self.format_combo)
        format_layout.addStretch()
        layout.addLayout(format_layout)
        
        # Pitch
        pitch_layout = QHBoxLayout()
        pitch_layout.addWidget(QLabel("Pitch:"))
        self.pitch_slider = QSlider(Qt.Orientation.Horizontal)
        self.pitch_slider.setMinimum(-12)
        self.pitch_slider.setMaximum(12)
        self.pitch_slider.setValue(0)
        self.pitch_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.pitch_slider.setTickInterval(3)
        self.pitch_label = QLabel("0")
        pitch_layout.addWidget(self.pitch_slider)
        pitch_layout.addWidget(self.pitch_label)
        self.pitch_slider.valueChanged.connect(
            lambda v: self.pitch_label.setText(str(v))
        )
        layout.addLayout(pitch_layout)
        
        # Emotion
        emotion_layout = QHBoxLayout()
        emotion_layout.addWidget(QLabel("Emotion:"))
        self.emotion_combo = QComboBox()
        self.emotion_combo.addItems([
            "neutral", "happy", "sad", "angry", 
            "surprised", "fearful"
        ])
        emotion_layout.addWidget(self.emotion_combo)
        emotion_layout.addStretch()
        layout.addLayout(emotion_layout)
        
        group.setLayout(layout)
        return group
    
    def _create_progress_group(self) -> QGroupBox:
        """Create progress display group"""
        group = QGroupBox("Progress")
        layout = QVBoxLayout()
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        self.progress_label = QLabel("")
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.progress_label)
        
        group.setLayout(layout)
        return group
    
    def _create_preview_group(self) -> QGroupBox:
        """Create audio preview group"""
        group = QGroupBox("Preview")
        layout = QVBoxLayout()
        
        # Preview controls
        preview_controls = QHBoxLayout()
        
        self.btn_preview_play = QPushButton("Play")
        self.btn_preview_play.setEnabled(False)
        self.btn_preview_play.clicked.connect(self.toggle_preview)
        preview_controls.addWidget(self.btn_preview_play)
        
        self.btn_preview_stop = QPushButton("Stop")
        self.btn_preview_stop.setEnabled(False)
        self.btn_preview_stop.clicked.connect(self.stop_preview)
        preview_controls.addWidget(self.btn_preview_stop)
        
        # Time display
        self.time_label = QLabel("00:00 / 00:00")
        preview_controls.addWidget(self.time_label)
        
        preview_controls.addStretch()
        
        layout.addLayout(preview_controls)
        
        # Seek slider
        self.seek_slider = QSlider(Qt.Orientation.Horizontal)
        self.seek_slider.setEnabled(False)
        self.seek_slider.sliderMoved.connect(self.seek_preview)
        layout.addWidget(self.seek_slider)
        
        group.setLayout(layout)
        return group
    
    def _create_action_buttons(self) -> QHBoxLayout:
        """Create action buttons"""
        layout = QHBoxLayout()
        
        self.btn_process = QPushButton("Process")
        self.btn_process.setEnabled(False)
        self.btn_process.clicked.connect(self.start_processing)
        layout.addWidget(self.btn_process)
        
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self.cancel_processing)
        layout.addWidget(self.btn_cancel)
        
        self.btn_export = QPushButton("Export")
        self.btn_export.setEnabled(False)
        self.btn_export.clicked.connect(self.export_file)
        layout.addWidget(self.btn_export)
        
        layout.addStretch()
        
        return layout
    
    def initialize_core(self):
        """Initialize core components"""
        self.logger.info("Initializing core components...")
        
        try:
            # Import core components - lazy import to avoid PyTorch DLL issues
            from voice_revolver_core.domain import (
                ProgressTracker, FileManager, VoiceConversionParams
            )
            from voice_revolver_core.application import ProjectService
            from voice_revolver_core.infrastructure.compute_controller import ComputeController
            from voice_revolver_core.infrastructure.model_manager import ModelManager
            from voice_revolver_core.infrastructure.ffmpeg_checker import FFmpegChecker
            
            # Initialize components
            self.progress_tracker = ProgressTracker()
            self.file_manager = FileManager(self.app_data_path)
            self.compute_controller = ComputeController()
            self.model_manager = ModelManager(self.app_data_path / "models")
            self.ffmpeg_checker = FFmpegChecker(self.app_data_path)
            self.project_service = ProjectService()
            
            # Set device
            self.compute_controller.set_device(self._device)
            
            self.logger.info("Core components initialized")
            self.status_bar.showMessage("Core initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize core: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(
                self, "Initialization Error",
                f"Failed to initialize: {e}"
            )
    
    def browse_original_file(self):
        """Browse for original audio file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Original Song",
            "", 
            "Audio Files (*.mp3 *.wav *.flac *.ogg *.m4a)"
        )
        
        if file_path:
            self.original_audio_path = Path(file_path)
            self.original_file_label.setText(self.original_audio_path.name)
            self.original_file_label.setStyleSheet("color: black;")
            self._check_can_process()
            self.logger.info(f"Selected original: {file_path}")
    
    def browse_reference_file(self):
        """Browse for reference voice file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Reference Voice",
            "",
            "Audio Files (*.mp3 *.wav *.flac *.ogg *.m4a)"
        )
        
        if file_path:
            self.reference_voice_path = Path(file_path)
            self.reference_file_label.setText(self.reference_voice_path.name)
            self.reference_file_label.setStyleSheet("color: black;")
            self._check_can_process()
            self.logger.info(f"Selected reference: {file_path}")
    
    def _check_can_process(self):
        """Check if we can start processing"""
        can_process = (
            self.original_audio_path is not None and
            self.reference_voice_path is not None and
            not self.is_processing
        )
        self.btn_process.setEnabled(can_process)
    
    def start_processing(self):
        """Start vocal replacement processing"""
        if not self.original_audio_path or not self.reference_voice_path:
            return
        
        self.is_processing = True
        self.btn_process.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.btn_export.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_label.setText("Starting...")
        
        self.logger.info("Starting processing...")
        self.status_bar.showMessage("Processing...")
        
        # Lazy import wrappers
        try:
            from voice_revolver_core.infrastructure.demucs_wrapper import DemucsWrapper
            from voice_revolver_core.infrastructure.openvoice_wrapper import OpenVoiceWrapper
            from voice_revolver_core.infrastructure.audio_mixer import AudioMixer
            from voice_revolver_core.infrastructure.format_converter import FormatConverter
            from voice_revolver_core.application.voice_replacement_service import VoiceReplacementService
            from voice_revolver_core.domain import VoiceConversionParams
            
            # Initialize infrastructure wrappers
            device = self._device
            
            self.demucs_wrapper = DemucsWrapper(device)
            self.openvoice_wrapper = OpenVoiceWrapper(
                self.model_manager.openvoice_path,
                device
            )
            self.audio_mixer = AudioMixer(self.ffmpeg_checker.get_ffmpeg_dir())
            self.format_converter = FormatConverter(self.ffmpeg_checker.get_ffmpeg_dir())
            
            # Initialize voice replacement service
            self.voice_replacement_service = VoiceReplacementService(
                self.demucs_wrapper,
                self.openvoice_wrapper,
                None,  # voice_transformer
                self.audio_mixer,
                self.file_manager,
                self.progress_tracker
            )
            
            # Get voice params
            voice_params = VoiceConversionParams(
                pitch=self.pitch_slider.value(),
                emotion=self.emotion_combo.currentText(),
                style_strength=1.0
            )
            
            output_format = self.format_combo.currentText().lower()
            
            # Create and start worker
            self.worker = ProcessingWorker(
                self.voice_replacement_service,
                self.original_audio_path,
                self.reference_voice_path,
                voice_params,
                output_format
            )
            
            self.worker.progress.connect(self.on_processing_progress)
            self.worker.finished.connect(self.on_processing_finished)
            self.worker.start()
            
        except Exception as e:
            self.logger.error(f"Failed to start processing: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Failed to start: {e}")
            self.is_processing = False
            self.btn_process.setEnabled(True)
            self.btn_cancel.setEnabled(False)
    
    def on_processing_progress(self, percentage: int, message: str):
        """Handle processing progress"""
        self.progress_bar.setValue(percentage)
        self.progress_label.setText(message)
    
    def on_processing_finished(self, success: bool, result: str):
        """Handle processing finished"""
        self.is_processing = False
        self.btn_process.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        
        if success:
            self.processed_output_path = Path(result)
            self.btn_export.setEnabled(True)
            self.status_bar.showMessage("Processing complete")
            self.progress_label.setText("Complete!")
            
            # Enable preview
            self.btn_preview_play.setEnabled(True)
            self._setup_preview_player()
            
            QMessageBox.information(self, "Success", "Processing complete!")
        else:
            self.progress_label.setText("Failed")
            self.status_bar.showMessage("Processing failed")
            QMessageBox.critical(self, "Error", f"Processing failed: {result}")
    
    def _setup_preview_player(self):
        """Setup preview player with processed audio"""
        if self.processed_output_path and self.processed_output_path.exists():
            if not hasattr(self, 'media_player'):
                self.media_player = QMediaPlayer()
                self.audio_output = QAudioOutput()
                self.media_player.setAudioOutput(self.audio_output)
                
                self.media_player.positionChanged.connect(self.on_preview_position_changed)
                self.media_player.durationChanged.connect(self.on_preview_duration_changed)
            
            self.media_player.setSource(QUrl.fromLocalFile(str(self.processed_output_path)))
            self.btn_preview_play.setText("Play")
    
    def on_preview_position_changed(self, position: int):
        """Handle preview position change"""
        self.seek_slider.setValue(position)
        self._update_time_label()
    
    def on_preview_duration_changed(self, duration: int):
        """Handle preview duration change"""
        self.seek_slider.setMaximum(duration)
        self._update_time_label()
    
    def _update_time_label(self):
        """Update time label"""
        if hasattr(self, 'media_player'):
            position = self.media_player.position()
            duration = self.media_player.duration()
            
            pos_str = self._format_time(position)
            dur_str = self._format_time(duration)
            self.time_label.setText(f"{pos_str} / {dur_str}")
    
    def _format_time(self, ms: int) -> str:
        """Format milliseconds to mm:ss"""
        seconds = ms // 1000
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes:02d}:{seconds:02d}"
    
    def toggle_preview(self):
        """Toggle preview play/pause"""
        if not hasattr(self, 'media_player'):
            return
        
        if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.media_player.pause()
            self.btn_preview_play.setText("Play")
        else:
            self.media_player.play()
            self.btn_preview_play.setText("Pause")
    
    def stop_preview(self):
        """Stop preview"""
        if hasattr(self, 'media_player'):
            self.media_player.stop()
            self.btn_preview_play.setText("Play")
    
    def seek_preview(self, position: int):
        """Seek preview"""
        if hasattr(self, 'media_player'):
            self.media_player.setPosition(position)
    
    def cancel_processing(self):
        """Cancel processing"""
        if self.worker and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait()
        
        self.is_processing = False
        self.btn_process.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.progress_label.setText("Cancelled")
        self.status_bar.showMessage("Cancelled")
        self.logger.info("Processing cancelled")
    
    def export_file(self):
        """Export processed file"""
        file_path, selected_filter = QFileDialog.getSaveFileName(
            self, "Export Audio",
            "",
            "MP3 (*.mp3);;WAV (*.wav);;FLAC (*.flac)"
        )
        
        if file_path:
            export_path = Path(file_path)
            
            # Convert format if needed
            import asyncio
            
            async def convert_and_export():
                return await self.format_converter.convert(
                    self.processed_output_path,
                    export_path,
                    progress_callback=None
                )
            
            try:
                loop = asyncio.get_event_loop()
                result, error = loop.run_until_complete(convert_and_export())
                
                if result:
                    self.logger.info(f"Exported to: {file_path}")
                    self.status_bar.showMessage(f"Exported to {export_path.name}")
                    QMessageBox.information(self, "Export", "File exported successfully!")
                else:
                    QMessageBox.critical(self, "Export Error", f"Failed: {error}")
                    
            except Exception as e:
                QMessageBox.critical(self, "Export Error", str(e))
    
    def new_project(self):
        """Create new project"""
        self.original_audio_path = None
        self.reference_voice_path = None
        self.processed_output_path = None
        self.original_file_label.setText("No file selected")
        self.original_file_label.setStyleSheet("color: gray;")
        self.reference_file_label.setText("No file selected")
        self.reference_file_label.setStyleSheet("color: gray;")
        self._check_can_process()
        self.current_project = None
        self.logger.info("New project created")
    
    def open_project(self):
        """Open existing project"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Project",
            "",
            "Voice Revolver Project (*.vra)"
        )
        
        if file_path:
            try:
                project_data = self.project_service.load_project(Path(file_path))
                
                # Load project data
                if project_data.original_file:
                    self.original_audio_path = Path(project_data.original_file)
                    self.original_file_label.setText(self.original_audio_path.name)
                    self.original_file_label.setStyleSheet("color: black;")
                
                if project_data.reference_file:
                    self.reference_voice_path = Path(project_data.reference_file)
                    self.reference_file_label.setText(self.reference_voice_path.name)
                    self.reference_file_label.setStyleSheet("color: black;")
                
                # Load settings
                if project_data.voice_params:
                    self.pitch_slider.setValue(project_data.voice_params.pitch)
                    self.emotion_combo.setCurrentText(project_data.voice_params.emotion)
                
                self.format_combo.setCurrentText(project_data.output_format.upper())
                
                self.current_project = Path(file_path)
                self._check_can_process()
                self.logger.info(f"Opened project: {file_path}")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to open project: {e}")
    
    def save_project(self):
        """Save current project"""
        if self.current_project is None:
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Save Project",
                "",
                "Voice Revolver Project (*.vra)"
            )
        else:
            file_path = str(self.current_project)
        
        if file_path:
            try:
                from voice_revolver_core.domain import VoiceConversionParams, ProjectData
                
                project_data = ProjectData(
                    original_file=str(self.original_audio_path) if self.original_audio_path else None,
                    reference_file=str(self.reference_voice_path) if self.reference_voice_path else None,
                    voice_params=VoiceConversionParams(
                        pitch=self.pitch_slider.value(),
                        emotion=self.emotion_combo.currentText(),
                        style_strength=1.0
                    ),
                    output_format=self.format_combo.currentText().lower(),
                    processing_state="not_started"
                )
                
                self.project_service.save_project(project_data, Path(file_path))
                self.current_project = Path(file_path)
                self.logger.info(f"Saved project: {file_path}")
                QMessageBox.information(self, "Save", "Project saved successfully!")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save project: {e}")
    
    def show_device_settings(self):
        """Show device settings dialog"""
        info = self.compute_controller.get_device_info()
        
        msg = f"Current Device: {info.get('current_device', 'unknown')}\n"
        msg += f"Has CUDA: {info.get('has_cuda', False)}\n"
        msg += f"Suggested: {info.get('suggested_device', 'unknown')}"
        
        if 'cuda_device_name' in info:
            msg += f"\nGPU: {info['cuda_device_name']}"
        
        QMessageBox.information(self, "Compute Device", msg)
    
    def show_about(self):
        """Show about dialog"""
        QMessageBox.about(
            self, "About Voice Revolver AI",
            "Voice Revolver AI v1.0\n\n"
            "A local-first desktop application for vocal replacement.\n\n"
            "Uses Demucs and OpenVoice AI models."
        )
    
    def closeEvent(self, event):
        """Handle window close"""
        # Cancel any running processing
        if self.is_processing:
            self.cancel_processing()
        
        # Cleanup temp files
        if self.file_manager:
            count = self.file_manager.cleanup_temp_files()
            self.logger.info(f"Cleaned up {count} temp files")
        
        # Stop preview player
        if hasattr(self, 'media_player'):
            self.media_player.stop()
        
        self.logger.info("Application closed")
        event.accept()


class LoadingWorker(QThread):
    """Worker thread for loading dependencies"""
    
    progress = pyqtSignal(int, str, str)  # percentage, status, detail
    finished = pyqtSignal(bool, str)  # success, message
    
    def __init__(self, device: str, app_data_path: Path):
        super().__init__()
        self._device = device
        self._app_data_path = app_data_path
    
    def run(self):
        """Run loading process"""
        import asyncio
        
        def progress_callback(percentage: int, status: str, detail: str = ""):
            self.progress.emit(percentage, status, detail)
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Step 1: Ensure FFmpeg
            progress_callback(0, "Checking FFmpeg...", "Looking for FFmpeg installation")
            
            from voice_revolver_core.infrastructure.ffmpeg_checker import FFmpegChecker
            ffmpeg_checker = FFmpegChecker(self._app_data_path)
            
            loop.run_until_complete(ffmpeg_checker.ensure_available())
            
            progress_callback(20, "FFmpeg ready", "Using FFmpeg for audio processing")
            
            # Step 2: Check models
            progress_callback(30, "Checking AI models...", "Looking for cached models")
            
            from voice_revolver_core.infrastructure.model_manager import ModelManager
            model_manager = ModelManager(self._app_data_path / "models")
            
            cache_status = model_manager.check_cache()
            
            if not all(cache_status.values()):
                progress_callback(40, "Downloading OpenVoice models...", "This may take a few minutes")
                
                # Download models
                loop.run_until_complete(
                    model_manager.download_all_models(
                        lambda model, prog: progress_callback(
                            40 + int(prog * 50),
                            f"Downloading {model}...",
                            f"Progress: {int(prog * 100)}%"
                        )
                    )
                )
            
            progress_callback(90, "Loading complete!", "All dependencies ready")
            
            self.finished.emit(True, "Success")
            
        except Exception as e:
            self.finished.emit(False, str(e))
        finally:
            loop.close()


def main():
    """Application entry point"""
    # On Windows, add torch DLL directory to search path before anything else
    if sys.platform == "win32" and hasattr(os, 'add_dll_directory'):
        try:
            import site
            site_packages = site.getsitepackages()[0]
            torch_lib = Path(site_packages) / "torch" / "lib"
            if torch_lib.exists():
                os.add_dll_directory(str(torch_lib))
        except Exception:
            pass
    
    app = QApplication(sys.argv)
    app.setApplicationName("Voice Revolver AI")
    app.setOrganizationName("VoiceRevolver")
    
    # Preload torch to avoid DLL loading issues later
    # Must happen early before other components initialize
    torch_preloaded = False
    try:
        import torch
        # Force DLL loading now
        _ = torch.tensor([1.0])
        torch_preloaded = True
        print(f"✓ PyTorch {torch.__version__} preloaded successfully")
    except (ImportError, OSError) as e:
        # If torch fails to load, we can still run but processing will fail
        # This is fine - user will see error when they try to process
        print(f"✗ PyTorch preload failed: {e}")
        pass
    
    # Preload heavy AI imports to avoid crashes in worker threads
    try:
        print("⏳ Preloading AI libraries...")
        from openvoice.api import ToneColorConverter
        from demucs.pretrained import get_model
        import torchaudio
        print("✓ AI libraries preloaded successfully")
    except Exception as e:
        print(f"⚠ Warning: AI library preload failed: {e}")
        # Non-fatal, continue anyway
        pass
    
    # Get app data path
    if sys.platform == "win32":
        base = Path(os.environ.get('LOCALAPPDATA', Path.home()))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path.home() / ".local" / "share"
    app_data_path = base / "VoiceRevolverAI"
    app_data_path.mkdir(parents=True, exist_ok=True)
    
    # Setup logging
    logger = setup_logging(app_data_path)
    
    # Show startup dialog for device selection
    startup = StartupDialog()
    if startup.exec() != QDialog.DialogCode.Accepted:
        sys.exit(0)
    
    device = startup.selected_device
    logger.info(f"User selected device: {device}")
    
    # Show loading dialog to download models
    loading_dialog = LoadingDialog(device)
    loading_worker = LoadingWorker(device, app_data_path)
    
    def on_loading_finished(success, message):
        if not success:
            QMessageBox.critical(None, "Error", f"Failed to load dependencies:\n{message}")
            sys.exit(1)
        loading_dialog.accept()
        # Show main window after loading completes
        window = MainWindow(device)
        window.show()
    
    def on_loading_progress(percentage, status, detail):
        loading_dialog.update_progress(percentage, status, detail)
    
    loading_worker.progress.connect(on_loading_progress)
    loading_worker.finished.connect(on_loading_finished)
    loading_worker.start()
    
    loading_dialog.exec()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
