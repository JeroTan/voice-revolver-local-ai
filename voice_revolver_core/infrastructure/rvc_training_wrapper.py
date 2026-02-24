"""
RVC Training Wrapper - Infrastructure Layer
Orchestrates the RVC training pipeline using subprocess calls to venv-rvc
"""

import os
import subprocess
import sys
import re
import shutil
import zipfile
import logging
import time
from pathlib import Path
from typing import Optional, Tuple, List, Callable
from datetime import datetime

from .venv_utils import get_venv_python

try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False

logger = logging.getLogger(__name__)


class RVCTrainingWrapper:
    """
    Infrastructure wrapper for RVC training.
    Orchestrates the 4-step training pipeline:
    1. Preprocess - Clean, split, normalize audio
    2. Extract - Extract F0 (pitch) and HuBERT features
    3. Train - Train the model
    4. Index - Build FAISS index for retrieval
    """
    
    def __init__(
        self,
        model_name: str,
        app_data_path: Path,
        device: str = "cuda"
    ):
        """Initialize training wrapper.
        
        Args:
            model_name: Name for the model
            app_data_path: Path to app data directory
            device: Compute device (cuda/cpu)
        """
        self.model_name = model_name
        self.app_data_path = app_data_path
        self.device = device
        
        # Paths
        self.project_root = Path(__file__).parent.parent.parent
        self.temp_dir = app_data_path / "temp" / "audio_training" / model_name
        self.input_dir = self.temp_dir / "input_audio"
        # Use temp directory for RVC logs/training artifacts (not project root)
        self.logs_dir = self.temp_dir / "logs"
        
        # RVC Python executable (works in both dev and .exe modes)
        self.rvc_python = get_venv_python('venv-rvc')
        
        # Training state
        self.process: Optional[subprocess.Popen] = None
        self.start_time: Optional[float] = None
    
    def _check_environment(self) -> Tuple[bool, Optional[str]]:
        """Check if RVC environment is available."""
        try:
            # Verify venv exists and is accessible
            if not self.rvc_python.exists():
                return False, f"RVC Python executable not found: {self.rvc_python}"
            return True, None
        except Exception as e:
            return False, str(e)
    
    def _prepare_input_audio(
        self,
        audio_files: List[Path],
        sample_rate: int,
        progress_callback: Callable[[float, str], None]
    ) -> Tuple[bool, Optional[str]]:
        """Convert and normalize input audio files.
        
        Args:
            audio_files: List of audio file paths
            sample_rate: Target sample rate
            progress_callback: Progress callback (0.0-1.0, message)
            
        Returns:
            (success, error_message)
        """
        if not PYDUB_AVAILABLE:
            return False, "pydub not available for audio conversion"
        
        try:
            # Create input directory
            self.input_dir.mkdir(parents=True, exist_ok=True)
            
            total_files = len(audio_files)
            for idx, file_path in enumerate(audio_files):
                progress = 0.01 + (idx / total_files) * 0.04  # 1% to 5%
                progress_callback(progress, f"Converting {file_path.name}...")
                
                try:
                    # Load audio
                    audio = AudioSegment.from_file(str(file_path))
                    
                    # Convert to mono and target sample rate
                    audio = audio.set_channels(1)
                    audio = audio.set_frame_rate(sample_rate)
                    
                    # Normalize volume
                    # Target -20 dBFS with headroom
                    target_dbfs = -20
                    change_in_dbfs = target_dbfs - audio.dBFS
                    audio = audio.apply_gain(change_in_dbfs)
                    
                    # Export as WAV
                    output_path = self.input_dir / f"{file_path.stem}.wav"
                    audio.export(str(output_path), format="wav")
                    
                    logger.info(f"Converted: {file_path.name} -> {output_path.name}")
                    
                except Exception as e:
                    logger.warning(f"Failed to convert {file_path.name}: {e}")
                    # Continue with other files
            
            # Check if we have any files
            wav_files = list(self.input_dir.glob("*.wav"))
            if not wav_files:
                return False, "No audio files could be converted"
            
            logger.info(f"Prepared {len(wav_files)} audio files for training")
            return True, None
            
        except Exception as e:
            logger.exception("Error preparing input audio")
            return False, str(e)
    
    def _run_preprocess(
        self,
        sample_rate: int,
        progress_callback: Callable[[float, str], None],
        cancel_check: Callable[[], bool]
    ) -> Tuple[bool, Optional[str]]:
        """Run RVC preprocessing step.
        
        Args:
            sample_rate: Target sample rate
            progress_callback: Progress callback
            cancel_check: Function to check if cancelled
            
        Returns:
            (success, error_message)
        """
        progress_callback(0.05, "Preprocessing audio...")
        
        preprocess_script = self.project_root / "rvc" / "train" / "preprocess" / "preprocess.py"
        
        if not preprocess_script.exists():
            return False, f"Preprocess script not found: {preprocess_script}"
        
        cmd = [
            str(self.rvc_python),
            str(preprocess_script),
            str(self.logs_dir),          # experiment_dir
            str(self.input_dir),          # input_root
            str(sample_rate),             # sample_rate
            "None",                       # num_processes (auto)
            "Automatic",                  # cut_preprocess
            "True",                       # process_effects
            "True",                       # noise_reduction
            "0.7",                        # reduction_strength
            "4.0",                        # chunk_len
            "0.3",                        # overlap_len
            "pre"                         # normalization_mode
        ]
        
        logger.info(f"Running preprocess: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=1800,  # 30 minute timeout
                cwd=str(self.project_root)
            )
            
            if cancel_check():
                return False, "Cancelled"
            
            if result.returncode != 0:
                logger.error(f"Preprocess stderr: {result.stderr}")
                return False, f"Preprocessing failed: {result.stderr[:500]}"
            
            logger.info(f"Preprocess output: {result.stdout[:500]}")
            progress_callback(0.25, "Preprocessing complete")
            return True, None
            
        except subprocess.TimeoutExpired:
            return False, "Preprocessing timed out (>30 minutes)"
        except Exception as e:
            logger.exception("Preprocess error")
            return False, str(e)
    
    def _run_extract(
        self,
        sample_rate: int,
        progress_callback: Callable[[float, str], None],
        cancel_check: Callable[[], bool]
    ) -> Tuple[bool, Optional[str]]:
        """Run RVC feature extraction step.
        
        Args:
            sample_rate: Sample rate
            progress_callback: Progress callback
            cancel_check: Function to check if cancelled
            
        Returns:
            (success, error_message)
        """
        progress_callback(0.25, "Extracting features...")
        
        extract_script = self.project_root / "rvc" / "train" / "extract" / "extract.py"
        
        if not extract_script.exists():
            return False, f"Extract script not found: {extract_script}"
        
        # Determine GPU setting
        gpus = "0" if self.device == "cuda" else "-"
        
        # Use CPU count for parallel processing
        num_processes = os.cpu_count() or 4
        
        cmd = [
            str(self.rvc_python),
            str(extract_script),
            str(self.logs_dir),           # exp_dir
            "rmvpe",                      # f0_method (best quality)
            str(num_processes),           # num_processes
            gpus,                         # gpus
            str(sample_rate),             # sample_rate
            "contentvec",                 # embedder_model
            "None",                       # embedder_model_custom (use "None" not empty to preserve arg position)
            "0"                           # include_mutes (disabled - mute files not bundled)
        ]
        
        logger.info(f"Running extract: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=3600,  # 1 hour timeout
                cwd=str(self.project_root)
            )
            
            if cancel_check():
                return False, "Cancelled"
            
            if result.returncode != 0:
                logger.error(f"Extract stderr: {result.stderr}")
                return False, f"Feature extraction failed: {result.stderr[:500]}"
            
            logger.info(f"Extract output: {result.stdout[:500]}")
            progress_callback(0.50, "Feature extraction complete")
            return True, None
            
        except subprocess.TimeoutExpired:
            return False, "Feature extraction timed out (>1 hour)"
        except Exception as e:
            logger.exception("Extract error")
            return False, str(e)
    
    def _run_train(
        self,
        params: dict,
        progress_callback: Callable[[float, str], None],
        cancel_check: Callable[[], bool]
    ) -> Tuple[bool, Optional[str]]:
        """Run RVC training step.
        
        Args:
            params: Training parameters (epochs, batch_size, sample_rate, save_every)
            progress_callback: Progress callback
            cancel_check: Function to check if cancelled
            
        Returns:
            (success, error_message)
        """
        progress_callback(0.50, "Starting training...")
        
        train_script = self.project_root / "rvc" / "train" / "train.py"
        
        if not train_script.exists():
            return False, f"Train script not found: {train_script}"
        
        # Find pretrained models
        sample_rate = params["sample_rate"]
        # Sample rate in filenames uses shorthand: 40000 -> 40k
        sr_short = f"{sample_rate // 1000}k"  # e.g., "40k", "48k", "32k"
        pretrain_dir = self.project_root / "rvc" / "models" / "pretraineds" / "hifi-gan"
        pretrain_g = pretrain_dir / f"f0G{sr_short}.pth"
        pretrain_d = pretrain_dir / f"f0D{sr_short}.pth"
        
        # Use "None" string if pretrains don't exist (will train from scratch - not recommended)
        pretrain_g_str = str(pretrain_g) if pretrain_g.exists() else "None"
        pretrain_d_str = str(pretrain_d) if pretrain_d.exists() else "None"
        
        if not pretrain_g.exists():
            logger.warning(f"Pretrained G not found: {pretrain_g}. Training from scratch.")
        if not pretrain_d.exists():
            logger.warning(f"Pretrained D not found: {pretrain_d}. Training from scratch.")
        
        # GPU setting
        gpus = "0" if self.device == "cuda" else "-"
        
        cmd = [
            str(self.rvc_python),
            str(train_script),
            str(self.logs_dir),                 # experiment_dir (full path)
            str(params["save_every"]),          # save_every_epoch
            str(params["epochs"]),              # total_epoch
            pretrain_g_str,                     # pretrainG
            pretrain_d_str,                     # pretrainD
            gpus,                               # gpus
            str(params["batch_size"]),          # batch_size
            str(sample_rate),                   # sample_rate
            "False",                            # save_only_latest
            "True",                             # save_every_weights
            "False",                            # cache_data_in_gpu
            "True",                             # overtraining_detector
            "50",                               # overtraining_threshold
            "False",                            # cleanup
            "HiFi-GAN",                         # vocoder
            "False"                             # checkpointing
        ]
        
        logger.info(f"Running train: {' '.join(cmd)}")
        self.start_time = time.time()
        
        try:
            # Use Popen for live progress tracking
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='replace',
                cwd=str(self.project_root)
            )
            
            total_epochs = params["epochs"]
            current_epoch = 0
            output_lines = []  # Capture output for error messages
            
            for line in self.process.stdout:
                if cancel_check():
                    self.process.terminate()
                    return False, "Cancelled"
                
                line = line.strip()
                if line:
                    logger.debug(f"Train: {line}")
                    output_lines.append(line)
                    # Keep only last 50 lines
                    if len(output_lines) > 50:
                        output_lines.pop(0)
                
                # Parse epoch progress
                # Look for patterns like "Epoch 150/400" or "epoch: 150"
                epoch_match = re.search(r'[Ee]poch[:\s]+(\d+)[/\s]+(\d+)?', line)
                if epoch_match:
                    current_epoch = int(epoch_match.group(1))
                    if epoch_match.group(2):
                        total_epochs = int(epoch_match.group(2))
                    
                    # Progress: 50% to 90% during training
                    train_progress = current_epoch / total_epochs
                    overall_progress = 0.50 + (train_progress * 0.40)
                    
                    # Calculate ETA
                    elapsed = time.time() - self.start_time
                    if current_epoch > 0:
                        eta_seconds = (elapsed / current_epoch) * (total_epochs - current_epoch)
                        eta_str = self._format_time(eta_seconds)
                    else:
                        eta_str = "Calculating..."
                    
                    progress_callback(
                        overall_progress,
                        f"Training: Epoch {current_epoch}/{total_epochs} (ETA: {eta_str})"
                    )
                
                # Parse loss
                loss_match = re.search(r'[Ll]oss[:\s]+([0-9.]+)', line)
                if loss_match:
                    logger.debug(f"Loss: {loss_match.group(1)}")
            
            # Wait for process to complete
            return_code = self.process.wait()
            
            if return_code != 0:
                # Include last few output lines in error
                error_context = "\n".join(output_lines[-10:]) if output_lines else "No output"
                logger.error(f"Training stderr/stdout:\n{error_context}")
                return False, f"Training failed with return code {return_code}:\n{error_context}"
            
            progress_callback(0.90, "Training complete")
            return True, None
            
        except Exception as e:
            logger.exception("Training error")
            return False, str(e)
        finally:
            self.process = None
    
    def _run_index(
        self,
        progress_callback: Callable[[float, str], None],
        cancel_check: Callable[[], bool]
    ) -> Tuple[bool, Optional[str]]:
        """Run RVC index building step.
        
        Args:
            progress_callback: Progress callback
            cancel_check: Function to check if cancelled
            
        Returns:
            (success, error_message)
        """
        progress_callback(0.90, "Building index...")
        
        index_script = self.project_root / "rvc" / "train" / "process" / "extract_index.py"
        
        if not index_script.exists():
            return False, f"Index script not found: {index_script}"
        
        cmd = [
            str(self.rvc_python),
            str(index_script),
            str(self.logs_dir),           # exp_dir
            "Auto"                        # index_algorithm
        ]
        
        logger.info(f"Running index: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=1800,  # 30 minute timeout
                cwd=str(self.project_root)
            )
            
            if cancel_check():
                return False, "Cancelled"
            
            if result.returncode != 0:
                logger.error(f"Index stderr: {result.stderr}")
                return False, f"Index building failed: {result.stderr[:500]}"
            
            logger.info(f"Index output: {result.stdout[:500]}")
            progress_callback(0.95, "Index built")
            return True, None
            
        except subprocess.TimeoutExpired:
            return False, "Index building timed out (>30 minutes)"
        except Exception as e:
            logger.exception("Index error")
            return False, str(e)
    
    def _export_model(
        self,
        progress_callback: Callable[[float, str], None]
    ) -> Tuple[Optional[Path], Optional[str]]:
        """Export final model as zip file.
        
        Args:
            progress_callback: Progress callback
            
        Returns:
            (output_zip_path, error_message)
        """
        progress_callback(0.95, "Exporting model...")
        
        try:
            # Find the latest model file
            # Pattern: {model_name}_{epoch}e_{step}s.pth
            model_files = list(self.logs_dir.glob(f"{self.model_name}_*e_*s.pth"))
            
            if not model_files:
                # Fallback: look for G_*.pth files
                model_files = list(self.logs_dir.glob("G_*.pth"))
            
            if not model_files:
                return None, "No model files found after training"
            
            # Get the latest by epoch number
            def get_epoch(p):
                match = re.search(r'_(\d+)e_', p.name)
                if match:
                    return int(match.group(1))
                match = re.search(r'G_(\d+)\.pth', p.name)
                if match:
                    return int(match.group(1))
                return 0
            
            latest_model = max(model_files, key=get_epoch)
            logger.info(f"Selected model: {latest_model.name}")
            
            # Find index file
            index_files = list(self.logs_dir.glob("*.index"))
            index_file = index_files[0] if index_files else None
            
            if not index_file:
                logger.warning("No index file found")
            
            # Create output zip
            output_dir = self.temp_dir / "output"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_zip = output_dir / f"{self.model_name}_{timestamp}.zip"
            
            with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
                # Add model file
                zf.write(latest_model, f"{self.model_name}.pth")
                
                # Add index file if exists
                if index_file:
                    zf.write(index_file, f"{self.model_name}.index")
            
            logger.info(f"Model exported to: {output_zip}")
            progress_callback(1.0, "Export complete!")
            
            return output_zip, None
            
        except Exception as e:
            logger.exception("Export error")
            return None, str(e)
    
    def _format_time(self, seconds: float) -> str:
        """Format seconds as human-readable time."""
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            mins = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{mins}m {secs}s"
        else:
            hours = int(seconds // 3600)
            mins = int((seconds % 3600) // 60)
            return f"{hours}h {mins}m"
    
    def train(
        self,
        audio_files: List[Path],
        params: dict,
        progress_callback: Callable[[float, str], None],
        cancel_check: Callable[[], bool]
    ) -> Tuple[Optional[Path], Optional[str]]:
        """Run the full training pipeline.
        
        Args:
            audio_files: List of audio file paths
            params: Training parameters (epochs, batch_size, sample_rate, save_every)
            progress_callback: Progress callback (0.0-1.0, message)
            cancel_check: Function that returns True if training should be cancelled
            
        Returns:
            (output_zip_path, error_message)
        """
        logger.info(f"Starting RVC training for model: {self.model_name}")
        logger.info(f"Audio files: {len(audio_files)}")
        logger.info(f"Parameters: {params}")
        
        # Check environment
        ok, error = self._check_environment()
        if not ok:
            return None, error
        
        # Create directories
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Step 0: Prepare input audio
            progress_callback(0.01, "Preparing audio files...")
            ok, error = self._prepare_input_audio(audio_files, params["sample_rate"], progress_callback)
            if not ok:
                return None, error
            
            if cancel_check():
                return None, "Cancelled"
            
            # Step 1: Preprocess
            ok, error = self._run_preprocess(params["sample_rate"], progress_callback, cancel_check)
            if not ok:
                return None, error
            
            if cancel_check():
                return None, "Cancelled"
            
            # Step 2: Extract features
            ok, error = self._run_extract(params["sample_rate"], progress_callback, cancel_check)
            if not ok:
                return None, error
            
            if cancel_check():
                return None, "Cancelled"
            
            # Step 3: Train
            ok, error = self._run_train(params, progress_callback, cancel_check)
            if not ok:
                return None, error
            
            if cancel_check():
                return None, "Cancelled"
            
            # Step 4: Build index
            ok, error = self._run_index(progress_callback, cancel_check)
            if not ok:
                return None, error
            
            # Step 5: Export
            output_zip, error = self._export_model(progress_callback)
            if error:
                return None, error
            
            logger.info(f"Training complete! Output: {output_zip}")
            return output_zip, None
            
        except Exception as e:
            logger.exception("Training pipeline error")
            return None, str(e)
    
    def cancel(self):
        """Cancel training by terminating subprocess."""
        if self.process:
            logger.info("Terminating training process...")
            self.process.terminate()
            self.process = None
