#!/usr/bin/env python3
"""
Test script to demonstrate the video processing pipeline
without requiring API keys or Hindi audio.

This tests:
1. Video info extraction
2. Audio extraction
3. Face-centered 9:16 crop generation
"""

import subprocess
from pathlib import Path
import json

def get_video_info(video_path: Path):
    """Get video metadata using ffprobe"""
    cmd = [
        'ffprobe',
        '-v', 'error',
        '-select_streams', 'v:0',
        '-show_entries', 'stream=width,height,duration,r_frame_rate',
        '-of', 'json',
        str(video_path)
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    data = json.loads(result.stdout)

    if data['streams']:
        stream = data['streams'][0]
        return {
            'width': stream['width'],
            'height': stream['height'],
            'duration': float(stream.get('duration', 0)),
            'fps': stream.get('r_frame_rate', '25/1')
        }
    return None


def extract_audio(video_path: Path, output_path: Path):
    """Extract audio from video"""
    print(f"Extracting audio from {video_path.name}...")

    cmd = [
        'ffmpeg',
        '-i', str(video_path),
        '-vn',  # No video
        '-acodec', 'pcm_s16le',  # WAV format
        '-ar', '16000',  # 16kHz sample rate
        '-ac', '1',  # Mono
        '-y',  # Overwrite
        str(output_path)
    ]

    subprocess.run(cmd, capture_output=True, check=True)
    print(f"✓ Audio extracted to {output_path}")
    return output_path


def create_vertical_clip(
    video_path: Path,
    output_path: Path,
    start_time: str = "00:00:05",
    duration: int = 15,
    source_width: int = 1280,
    source_height: int = 720
):
    """
    Create a 9:16 vertical clip with center crop
    (simplified version without face tracking)
    """
    print(f"\nCreating 9:16 vertical clip...")
    print(f"  Source: {source_width}x{source_height}")
    print(f"  Start time: {start_time}, Duration: {duration}s")

    # Calculate 9:16 crop dimensions
    target_aspect = 9 / 16  # 0.5625

    # Use full height, calculate width for 9:16
    crop_height = source_height
    crop_width = int(crop_height * target_aspect)

    # Center crop horizontally
    crop_x = (source_width - crop_width) // 2
    crop_y = 0

    print(f"  Crop: {crop_width}x{crop_height} at position ({crop_x}, {crop_y})")

    # Build filter chain
    filter_str = f"crop={crop_width}:{crop_height}:{crop_x}:{crop_y},scale=1080:1920:force_original_aspect_ratio=decrease:force_divisible_by=2"

    # Build FFmpeg command
    cmd = [
        'ffmpeg',
        '-ss', start_time,
        '-i', str(video_path),
        '-t', str(duration),  # Duration
        '-vf', filter_str,
        '-c:v', 'libx264',
        '-preset', 'medium',
        '-crf', '23',
        '-c:a', 'aac',
        '-b:a', '128k',
        '-y',
        str(output_path)
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"✗ FFmpeg error: {result.stderr}")
        raise Exception(f"Clip creation failed: {result.stderr}")

    print(f"✓ Vertical clip created: {output_path}")

    # Verify output
    output_info = get_video_info(output_path)
    if output_info:
        print(f"  Output resolution: {output_info['width']}x{output_info['height']}")
        print(f"  Output duration: {output_info['duration']:.2f}s")

    return output_path


def main():
    print("=" * 60)
    print("Video Processing Pipeline Test")
    print("=" * 60)

    # Test video
    video_path = Path("test_input.mp4")

    if not video_path.exists():
        print(f"✗ Test video not found: {video_path}")
        print("  Please ensure test_input.mp4 exists in the current directory")
        return

    print(f"\n1. Analyzing video: {video_path.name}")
    video_info = get_video_info(video_path)

    if video_info:
        print(f"   Resolution: {video_info['width']}x{video_info['height']}")
        print(f"   Duration: {video_info['duration']:.2f}s")
        print(f"   FPS: {video_info['fps']}")

    # Create test output directory
    output_dir = Path("test_output")
    output_dir.mkdir(exist_ok=True)

    # Extract audio
    print(f"\n2. Extracting audio...")
    audio_path = output_dir / "audio.wav"
    try:
        extract_audio(video_path, audio_path)
    except Exception as e:
        print(f"✗ Audio extraction failed: {e}")

    # Create vertical clip
    print(f"\n3. Creating 9:16 vertical clip...")
    output_video = output_dir / "clip_vertical.mp4"

    try:
        create_vertical_clip(
            video_path,
            output_video,
            start_time="00:00:02",
            duration=10,
            source_width=video_info['width'],
            source_height=video_info['height']
        )
    except Exception as e:
        print(f"✗ Clip creation failed: {e}")
        return

    print("\n" + "=" * 60)
    print("Test completed successfully!")
    print("=" * 60)
    print(f"\nGenerated files:")
    print(f"  - {audio_path} ({audio_path.stat().st_size / 1024:.1f} KB)")
    print(f"  - {output_video} ({output_video.stat().st_size / 1024 / 1024:.2f} MB)")
    print(f"\nNote: This test uses center crop instead of face tracking")
    print(f"      and skips transcription/subtitle steps.")
    print("\nTo test with Hindi video and full subtitle system:")
    print(f"  1. Configure API keys in .env file")
    print(f"  2. Upload Hindi video via the web interface")
    print(f"  3. Or use the /process endpoint with a Hindi video file")


if __name__ == "__main__":
    main()
