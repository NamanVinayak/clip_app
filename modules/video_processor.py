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

        audio_path = self.job_folder / "audio.mp3"

        cmd = [
            'ffmpeg',
            '-err_detect', 'ignore_err', # Ignore decoding errors
            '-i', str(video_path),
            '-vn',  # No video
            '-map', '0:1', # Explicitly select stream 1 (audio)
            '-acodec', 'libmp3lame',  # MP3 format
            '-ab', '64k',  # 64k bitrate (sufficient for speech, small size)
            '-ar', '16000',  # 16kHz sample rate
            '-ac', '1',  # Mono (sufficient for speech)
            '-y',  # Overwrite
            str(audio_path)
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            self.logger.warning(f"FFmpeg reported errors: {result.stderr[:200]}...")
            if not audio_path.exists() or audio_path.stat().st_size < 1000:
                 raise Exception(f"Audio extraction failed: {result.stderr}")
            self.logger.warning("Proceeding with partially extracted audio...")

        self.logger.info(f"Audio extracted to {audio_path}")
        return audio_path

    def cut_clip(
        self,
        video_path: Path,
        start_time: str,
        duration: float,
        output_path: Path,
        crop_params: Optional[dict] = None
    ) -> Path:
        """
        Cut a clip from video with optional cropping

        Args:
            video_path: Source video file
            start_time: Start timestamp (HH:MM:SS)
            duration: Duration of the clip in seconds
            output_path: Output file path
            crop_params: Dict with 'x', 'y', 'width', 'height' for cropping
        """
        self.logger.info(f"Cutting clip: {start_time} for {duration} seconds")

        # Build filter chain
        filters = []

        if crop_params:
            # Crop to 9:16 aspect ratio
            crop_filter = (
                f"crop={crop_params['width']}:{crop_params['height']}:"
                f"{crop_params['x']}:{crop_params['y']}"
            )
            filters.append(crop_filter)

            # Scale to ~1080x1920 if needed, forcing even dimensions for H.264
            scale_filter = (
                "scale=1080:1920:"
                "force_original_aspect_ratio=decrease:"
                "force_divisible_by=2"
            )
            filters.append(scale_filter)

        filter_str = ','.join(filters) if filters else None

        # Build FFmpeg command
        cmd = [
            'ffmpeg',
            '-ss', start_time,  # Start time
            '-i', str(video_path),
            '-t', str(duration),  # Duration of the clip
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
        face_x: int,
        face_y: int,
        source_width: int,
        source_height: int,
        output_name: str
    ) -> Path:
        """
        Create a vertical 9:16 clip with face-centered cropping.

        Args:
            video_path: Source video
            start_time: Start timestamp
            duration: Clip duration in seconds
            face_x: X coordinate of face center in source frame
            face_y: Y coordinate of face center in source frame
            source_width: Width of source video in pixels
            source_height: Height of source video in pixels
            output_name: Output filename
        """
        output_path = self.job_folder / output_name

        # Guard against missing metadata
        if source_width <= 0 or source_height <= 0:
            self.logger.warning(
                "Invalid source dimensions, falling back to 4K defaults (3840x2160)"
            )
            source_width = 3840
            source_height = 2160

        # Target vertical aspect ratio (width / height)
        target_aspect = 9 / 16

        # Compute the largest possible 9:16 crop that fits in the source frame
        # and is centered around the face.
        crop_height = source_height
        crop_width = int(crop_height * target_aspect)

        if crop_width > source_width:
            # Source is narrower / more vertical than 16:9.
            crop_width = source_width
            crop_height = int(crop_width / target_aspect)

        # Center the crop window on the face position
        half_w = crop_width // 2
        half_h = crop_height // 2

        crop_x = int(face_x - half_w)
        crop_y = int(face_y - half_h)

        # Clamp to valid range so we don't go outside frame bounds
        crop_x = max(0, min(crop_x, source_width - crop_width))
        crop_y = max(0, min(crop_y, source_height - crop_height))

        self.logger.info("Vertical crop parameters:")
        self.logger.info(
            f"  - Source size: {source_width}x{source_height}, target aspect 9:16"
        )
        self.logger.info(
            f"  - Face center: ({face_x}, {face_y}) -> crop window x={crop_x}, y={crop_y}, "
            f"w={crop_width}, h={crop_height}"
        )

        crop_params = {
            'x': crop_x,
            'y': crop_y,
            'width': crop_width,
            'height': crop_height
        }

        return self.cut_clip(
            video_path,
            start_time,
            duration,
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
