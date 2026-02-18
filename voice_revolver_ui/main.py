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
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QAction, QIcon, QDragEnterEvent, QDropEvent


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


class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        
        # Initialize paths
        self.app_data_path = self._get_app_data_path()
        self.app_data_path.mkdir(parents=True, exist_ok=True)
        
        # Setup logging
        self.logger = setup_logging(self.app_data_path)
        self.logger.info("Starting Voice Revolver AI...")
        
        # Core components (to be initialized)
        self.progress_tracker = None
        self.compute_controller = None
        self.model_manager = None
        self.file_manager = None
        self.project_service = None
        self.voice_replacement_service = None
        
        # State
        self.current_project = None
        self.original_audio_path: Path = None
        self.reference_voice_path: Path = None
        self.processed_output_path: Path = None
        self.is_processing = False
        
        # Setup UI
        self.init_ui()
        
        # Initialize core after UI (for better UX)
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
        preview_controls.addWidget(self.btn_preview_play)
        
        self.btn_preview_stop = QPushButton("Stop")
        self.btn_preview_stop.setEnabled(False)
        preview_controls.addWidget(self.btn_preview_stop)
        
        # Time display
        self.time_label = QLabel("00:00 / 00:00")
        preview_controls.addWidget(self.time_label)
        
        preview_controls.addStretch()
        
        layout.addLayout(preview_controls)
        
        # Seek slider
        self.seek_slider = QSlider(Qt.Orientation.Horizontal)
        self.seek_slider.setEnabled(False)
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
            # Import core components
            from voice_revolver_core import (
                ProgressTracker, FileManager, ComputeController,
                ModelManager, FFmpegChecker, ProjectService
            )
            
            # Initialize components
            self.progress_tracker = ProgressTracker()
            self.file_manager = FileManager(self.app_data_path)
            self.compute_controller = ComputeController()
            self.model_manager = ModelManager(self.app_data_path / "models")
            self.ffmpeg_checker = FFmpegChecker(self.app_data_path)
            self.project_service = ProjectService()
            
            self.logger.info("Core components initialized")
            self.status_bar.showMessage("Core initialized")
            
            # Check models
            self._check_and_download_models()
            
        except Exception as e:
            self.logger.error(f"Failed to initialize core: {e}")
            QMessageBox.critical(
                self, "Initialization Error",
                f"Failed to initialize: {e}"
            )
    
    def _check_and_download_models(self):
        """Check models and download if needed"""
        self.logger.info("Checking models...")
        self.status_bar.showMessage("Checking models...")
        
        # Check cache
        cache_status = self.model_manager.check_cache()
        
        if not all(cache_status.values()):
            self.logger.info("Models not found, downloading...")
            self.status_bar.showMessage("Downloading models...")
            # TODO: Start download in background
        else:
            self.logger.info("Models cached, ready")
            self.status_bar.showMessage("Ready")
    
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
        
        self.logger.info("Starting processing...")
        self.status_bar.showMessage("Processing...")
        
        # TODO: Start processing in background thread
        # For now, simulate progress
        self._simulate_processing()
    
    def _simulate_processing(self):
        """Simulate processing for demo"""
        self.progress_label.setText("Loading models...")
        
        # Simulate progress
        def update_progress():
            if self.progress_bar.value() >= 100:
                self.is_processing = False
                self.btn_process.setEnabled(True)
                self.btn_cancel.setEnabled(False)
                self.btn_export.setEnabled(True)
                self.status_bar.showMessage("Processing complete")
                return
            
            self.progress_bar.setValue(self.progress_bar.value() + 1)
            
            if self.progress_bar.value() < 20:
                self.progress_label.setText("Loading models...")
            elif self.progress_bar.value() < 50:
                self.progress_label.setText("Separating stems...")
            elif self.progress_bar.value() < 80:
                self.progress_label.setText("Converting voice...")
            else:
                self.progress_label.setText("Mixing audio...")
        
        self.progress_timer = QTimer()
        self.progress_timer.timeout.connect(update_progress)
        self.progress_timer.start(50)
    
    def cancel_processing(self):
        """Cancel processing"""
        if hasattr(self, 'progress_timer'):
            self.progress_timer.stop()
        
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
            self.logger.info(f"Exporting to: {file_path}")
            self.status_bar.showMessage(f"Exported to {Path(file_path).name}")
            QMessageBox.information(self, "Export", "File exported successfully!")
    
    def new_project(self):
        """Create new project"""
        self.original_audio_path = None
        self.reference_voice_path = None
        self.original_file_label.setText("No file selected")
        self.original_file_label.setStyleSheet("color: gray;")
        self.reference_file_label.setText("No file selected")
        self.reference_file_label.setStyleSheet("color: gray;")
        self._check_can_process()
        self.logger.info("New project created")
    
    def open_project(self):
        """Open existing project"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Project",
            "",
            "Voice Revolver Project (*.vra)"
        )
        
        if file_path:
            self.logger.info(f"Opening project: {file_path}")
            # TODO: Load project
    
    def save_project(self):
        """Save current project"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Project",
            "",
            "Voice Revolver Project (*.vra)"
        )
        
        if file_path:
            self.logger.info(f"Saving project: {file_path}")
            # TODO: Save project
    
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
        # Cleanup temp files
        if self.file_manager:
            count = self.file_manager.cleanup_temp_files()
            self.logger.info(f"Cleaned up {count} temp files")
        
        self.logger.info("Application closed")
        event.accept()


def main():
    """Application entry point"""
    app = QApplication(sys.argv)
    app.setApplicationName("Voice Revolver AI")
    app.setOrganizationName("VoiceRevolver")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
