import logging
from datetime import datetime
from pathlib import Path
from typing import Optional


def setup_logger(name: str, log_file: Optional[Path] = None) -> logging.Logger:
    """Set up logger with file and console handlers"""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)

    # File handler (if log_file provided)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(console_format)
        logger.addHandler(file_handler)

    return logger


def create_job_folder(outputs_dir: Path) -> Path:
    """Create a timestamped job folder"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    job_folder = outputs_dir / f"job_{timestamp}"
    job_folder.mkdir(parents=True, exist_ok=True)
    return job_folder


def format_timestamp(seconds: float) -> str:
    """Convert seconds to HH:MM:SS format"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def parse_timestamp(timestamp: str) -> float:
    """Convert HH:MM:SS to seconds"""
    parts = timestamp.split(':')
    if len(parts) == 3:
        hours, minutes, seconds = map(float, parts)
        return hours * 3600 + minutes * 60 + seconds
    elif len(parts) == 2:
        minutes, seconds = map(float, parts)
        return minutes * 60 + seconds
    else:
        return float(parts[0])


def get_video_info(video_path: Path) -> dict:
    """Get basic video information using ffprobe"""
    import subprocess
    import json

    cmd = [
        'ffprobe',
        '-v', 'quiet',
        '-print_format', 'json',
        '-show_format',
        '-show_streams',
        str(video_path)
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"Failed to get video info: {result.stderr}")

    data = json.loads(result.stdout)

    # Find video stream
    video_stream = next(
        (s for s in data['streams'] if s['codec_type'] == 'video'),
        None
    )

    if not video_stream:
        raise Exception("No video stream found")

    return {
        'width': int(video_stream['width']),
        'height': int(video_stream['height']),
        'duration': float(data['format']['duration']),
        'fps': eval(video_stream['r_frame_rate']),
        'codec': video_stream['codec_name']
    }
