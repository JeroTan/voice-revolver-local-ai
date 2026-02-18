"""
Test core voice replacement logic without UI
"""
import sys
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)

def main():
    # Preload heavy imports
    logger.info("Preloading AI libraries...")
    import torch
    from openvoice.api import ToneColorConverter
    from demucs.pretrained import get_model
    import torchaudio
    logger.info("AI libraries loaded successfully")
    
    # Import core components
    from voice_revolver_core.infrastructure.demucs_wrapper import DemucsWrapper
    from voice_revolver_core.infrastructure.openvoice_wrapper import OpenVoiceWrapper
    from voice_revolver_core.infrastructure.audio_mixer import AudioMixer
    from voice_revolver_core.infrastructure.format_converter import FormatConverter
    from voice_revolver_core.domain.file_manager import FileManager
    from voice_revolver_core.domain.progress_tracker import ProgressTracker
    from voice_revolver_core.domain import VoiceConversionParams
    from voice_revolver_core.application.voice_replacement_service import VoiceReplacementService
    
    # Setup paths
    if sys.platform == "win32":
        base = Path.home() / "AppData" / "Local"
    else:
        base = Path.home() / ".local" / "share"
    app_data_path = base / "VoiceRevolverAI"
    app_data_path.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"App data path: {app_data_path}")
    
    # Get model paths
    models_dir = app_data_path / "models"
    openvoice_path = models_dir / "checkpoints_v2"
    
    logger.info(f"OpenVoice path: {openvoice_path}")
    
    if not openvoice_path.exists():
        logger.error("OpenVoice models not found. Run the GUI first to download models.")
        return
    
    # Initialize components
    logger.info("Initializing components...")
    device = "cpu"
    
    demucs = DemucsWrapper(device)
    openvoice = OpenVoiceWrapper(openvoice_path, device)
    mixer = AudioMixer(None)  # Will use system FFmpeg
    converter = FormatConverter(None)
    file_manager = FileManager(app_data_path / "temp")
    progress_tracker = ProgressTracker()
    
    # Create service
    service = VoiceReplacementService(
        demucs,
        openvoice,
        None,  # voice_transformer
        mixer,
        file_manager,
        progress_tracker
    )
    
    logger.info("Components initialized")
    
    # Test files (you'll need to provide these)
    original = Path(r"F:\media\music\Songs\Bad Day.mp3")
    reference = Path(r"F:\media\creatives\video_editing\projects\raw_footage\2026-02-17 19-46-09.mp3")
    
    if not original.exists():
        logger.error(f"Original audio not found: {original}")
        return
    
    if not reference.exists():
        logger.error(f"Reference audio not found: {reference}")
        return
    
    logger.info(f"Original: {original}")
    logger.info(f"Reference: {reference}")
    
    # Progress callback
    def progress_cb(percentage, message):
        logger.info(f"Progress: {percentage}% - {message}")
    
    # Run processing
    logger.info("Starting processing...")
    try:
        result_path, error_code, message = service.process(
            original,
            reference,
            VoiceConversionParams(pitch=0, emotion="Neutral", style_strength=1.0),
            output_format="wav",
            progress_callback=progress_cb
        )
        
        if result_path:
            logger.info(f"SUCCESS! Output: {result_path}")
        else:
            logger.error(f"FAILED: {error_code} - {message}")
            
    except Exception as e:
        logger.error(f"Exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
