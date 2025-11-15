import subprocess
from pathlib import Path
from typing import Optional
from utils.helpers import setup_logger


class VideoProcessor:
    """Handles video processing operations using FFmpeg"""

    def __init__(self, job_folder: Path):
        self.job_folder = job_folder
        self.logger = setup_logger(
            "VideoProcessor",
            job_folder / "processing.log"
        )

    def extract_audio(self, video_path: Path) -> Path:
        """Extract audio from video as WAV file"""
        self.logger.info(f"Extracting audio from {video_path.name}")

        audio_path = self.job_folder / "audio.wav"

        cmd = [
            'ffmpeg',
            '-i', str(video_path),
            '-vn',  # No video
            '-acodec', 'pcm_s16le',  # WAV format
            '-ar', '16000',  # 16kHz sample rate (good for speech)
            '-ac', '1',  # Mono
            '-y',  # Overwrite
            str(audio_path)
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            self.logger.error(f"FFmpeg error: {result.stderr}")
            raise Exception(f"Audio extraction failed: {result.stderr}")

        self.logger.info(f"Audio extracted to {audio_path}")
        return audio_path

    def cut_clip(
        self,
        video_path: Path,
        start_time: str,
        end_time: str,
        output_path: Path,
        crop_params: Optional[dict] = None
    ) -> Path:
        """
        Cut a clip from video with optional cropping

        Args:
            video_path: Source video file
            start_time: Start timestamp (HH:MM:SS)
            end_time: End timestamp (HH:MM:SS)
            output_path: Output file path
            crop_params: Dict with 'x', 'y', 'width', 'height' for cropping
        """
        self.logger.info(f"Cutting clip: {start_time} to {end_time}")

        # Build filter chain
        filters = []

        if crop_params:
            # Crop to 9:16 aspect ratio
            crop_filter = (
                f"crop={crop_params['width']}:{crop_params['height']}:"
                f"{crop_params['x']}:{crop_params['y']}"
            )
            filters.append(crop_filter)

            # Scale to 1080x1920 if needed
            scale_filter = "scale=1080:1920:force_original_aspect_ratio=decrease"
            filters.append(scale_filter)

        filter_str = ','.join(filters) if filters else None

        # Build FFmpeg command
        cmd = [
            'ffmpeg',
            '-ss', start_time,  # Start time
            '-i', str(video_path),
            '-to', end_time,  # End time (relative to start)
            '-c:v', 'libx264',  # H.264 codec
            '-preset', 'medium',  # Encoding speed
            '-crf', '23',  # Quality (lower = better)
            '-c:a', 'aac',  # Audio codec
            '-b:a', '128k',  # Audio bitrate
        ]

        if filter_str:
            cmd.extend(['-vf', filter_str])

        cmd.extend(['-y', str(output_path)])

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            self.logger.error(f"FFmpeg error: {result.stderr}")
            raise Exception(f"Clip cutting failed: {result.stderr}")

        self.logger.info(f"Clip saved to {output_path}")
        return output_path

    def create_vertical_clip(
        self,
        video_path: Path,
        start_time: str,
        duration: float,
        crop_x: int,
        crop_y: int,
        output_name: str
    ) -> Path:
        """
        Create a vertical 9:16 clip with face-centered cropping

        Args:
            video_path: Source video
            start_time: Start timestamp
            duration: Clip duration in seconds
            crop_x: X coordinate for crop center
            crop_y: Y coordinate for crop center
            output_name: Output filename
        """
        output_path = self.job_folder / output_name

        # Calculate crop parameters for 9:16
        # Assuming 4K source (3840x2160)
        crop_width = 1080  # Target width
        crop_height = 1920  # Target height

        # Adjust crop position to center on face
        # Make sure we don't go out of bounds
        crop_x = max(0, min(crop_x - crop_width // 2, 3840 - crop_width))
        crop_y = max(0, min(crop_y - crop_height // 2, 2160 - crop_height))

        crop_params = {
            'x': crop_x,
            'y': crop_y,
            'width': crop_width,
            'height': crop_height
        }

        # Calculate end time
        from utils.helpers import parse_timestamp, format_timestamp
        start_seconds = parse_timestamp(start_time)
        end_seconds = start_seconds + duration
        end_time = format_timestamp(end_seconds)

        return self.cut_clip(
            video_path,
            start_time,
            end_time,
            output_path,
            crop_params
        )

    def get_frame_at_time(self, video_path: Path, timestamp: str) -> Path:
        """Extract a single frame at given timestamp for analysis"""
        frame_path = self.job_folder / f"frame_{timestamp.replace(':', '-')}.jpg"

        cmd = [
            'ffmpeg',
            '-ss', timestamp,
            '-i', str(video_path),
            '-vframes', '1',
            '-y',
            str(frame_path)
        ]

        subprocess.run(cmd, capture_output=True, check=True)
        return frame_path

    def composite_subtitles(
        self,
        video_path: Path,
        subtitle_overlay_path: Path,
        output_path: Path
    ) -> Path:
        """
        Composite subtitle overlay onto video

        Args:
            video_path: Base video clip
            subtitle_overlay_path: Transparent subtitle video (ProRes 4444)
            output_path: Output path for final video

        Returns:
            Path to composited video
        """
        self.logger.info("Compositing subtitles onto video...")

        # FFmpeg overlay filter
        cmd = [
            'ffmpeg',
            '-i', str(video_path),
            '-i', str(subtitle_overlay_path),
            '-filter_complex', '[0:v][1:v]overlay=0:0',
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-crf', '23',
            '-c:a', 'copy',
            '-y',
            str(output_path)
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            self.logger.info(f"✓ Subtitles composited: {output_path}")
            return output_path
        except subprocess.CalledProcessError as e:
            self.logger.error(f"FFmpeg compositing failed: {e.stderr}")
            raise Exception(f"Subtitle compositing failed: {e.stderr}")
