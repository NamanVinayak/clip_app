#!/usr/bin/env python3
"""
Full Hindi Video Processing Pipeline Test

This script tests the complete subtitle system:
1. Video upload and validation
2. Audio extraction
3. WhisperX Hindi transcription (via RunPod)
4. Hindi → Roman transliteration
5. LLM clip selection
6. Face tracking and 9:16 crop
7. Subtitle rendering and compositing

Usage:
    python3 test_hindi_full_pipeline.py <hindi_video.mp4>

Requirements:
    - .env file with RUNPOD_API_KEY and OPENROUTER_API_KEY
    - Hindi audio in the input video
    - 16:9 aspect ratio recommended
"""

import sys
import asyncio
from pathlib import Path
import json

# Add project modules to path
sys.path.insert(0, str(Path(__file__).parent))

from config import Settings
from modules.video_processor import VideoProcessor
from modules.transcriber import Transcriber
from modules.transliterator import HindiTransliterator
from modules.clip_selector import ClipSelector
from modules.face_tracker import FaceTracker
from modules.subtitle_renderer import SubtitleRenderer
from utils.helpers import setup_logger, create_job_folder, get_video_info


async def test_full_pipeline(video_path: Path):
    """Test the complete Hindi video processing pipeline"""

    print("=" * 70)
    print("HINDI VIDEO PROCESSING PIPELINE TEST")
    print("=" * 70)

    # Load settings
    settings = Settings()

    # Verify API keys are configured
    if not settings.runpod_api_key or not settings.openrouter_api_key:
        print("\n❌ ERROR: API keys not configured!")
        print("   Please set RUNPOD_API_KEY and OPENROUTER_API_KEY in .env file")
        return

    # Create job folder
    job_folder = create_job_folder(settings.outputs_dir)
    logger = setup_logger("TestPipeline", job_folder / "processing.log")

    print(f"\n📁 Job folder: {job_folder.name}")
    print(f"📹 Input video: {video_path.name}")

    # Step 1: Validate video
    print("\n" + "─" * 70)
    print("STEP 1: Video Validation")
    print("─" * 70)

    if not video_path.exists():
        print(f"❌ Video not found: {video_path}")
        return

    video_info = get_video_info(video_path)
    print(f"✓ Resolution: {video_info['width']}x{video_info['height']}")
    print(f"✓ Duration: {video_info['duration']:.2f}s ({video_info['duration']/60:.1f} minutes)")
    print(f"✓ FPS: {video_info.get('fps', 'Unknown')}")

    # Copy to job folder
    original_video_path = job_folder / "original_video.mp4"
    import shutil
    shutil.copy2(video_path, original_video_path)
    print(f"✓ Copied to job folder")

    # Step 2: Extract audio
    print("\n" + "─" * 70)
    print("STEP 2: Audio Extraction")
    print("─" * 70)

    processor = VideoProcessor(job_folder)
    audio_path = processor.extract_audio(original_video_path)
    print(f"✓ Audio extracted: {audio_path.name}")
    print(f"  Size: {audio_path.stat().st_size / 1024:.1f} KB")

    # Step 3: Transcribe with WhisperX
    print("\n" + "─" * 70)
    print("STEP 3: WhisperX Transcription (Hindi)")
    print("─" * 70)
    print("⏳ Calling RunPod WhisperX endpoint...")
    print("   This may take 2-5 minutes depending on audio length...")

    transcriber = Transcriber(
        runpod_api_key=settings.runpod_api_key,
        runpod_endpoint=settings.runpod_endpoint,
        job_folder=job_folder
    )

    transcript_data = await transcriber.transcribe(audio_path, language="hi")
    print(f"✓ Transcription complete!")
    print(f"  Segments: {len(transcript_data.get('segments', []))}")
    print(f"  Language detected: {transcript_data.get('language', 'Unknown')}")

    # Save word-level timestamps
    words_path = transcriber.save_word_timestamps(transcript_data)
    print(f"✓ Word timestamps saved: {words_path.name}")

    # Show sample transcript
    if transcript_data.get('segments'):
        print(f"\n  Sample transcript (first 3 segments):")
        for i, seg in enumerate(transcript_data['segments'][:3]):
            print(f"    [{seg['start']:.1f}s - {seg['end']:.1f}s] {seg['text']}")

    # Step 4: Transliterate to Roman script
    print("\n" + "─" * 70)
    print("STEP 4: Hindi → Roman Transliteration")
    print("─" * 70)

    transliterator = HindiTransliterator(job_folder)
    romanized_transcript = transliterator.transliterate_transcript(transcript_data)
    print(f"✓ Transliteration complete!")

    # Show sample romanized text
    if romanized_transcript.get('segments'):
        print(f"\n  Sample romanized text (first 3 segments):")
        for i, seg in enumerate(romanized_transcript['segments'][:3]):
            print(f"    Hindi:  {seg['text']}")
            print(f"    Roman:  {seg.get('text_roman', 'N/A')}")
            print()

    # Step 5: LLM Clip Selection
    print("\n" + "─" * 70)
    print("STEP 5: LLM Viral Clip Selection")
    print("─" * 70)
    print("⏳ Analyzing transcript with LLM...")

    selector = ClipSelector(
        api_key=settings.openrouter_api_key,
        model=settings.llm_model,
        job_folder=job_folder
    )

    clips = await selector.select_clips(
        transcript_data=transcript_data,
        video_duration=video_info['duration'],
        target_count=settings.target_clips
    )
    print(f"✓ Clip selection complete!")
    print(f"  Selected clips: {len(clips)}")

    if clips:
        print(f"\n  Suggested clips:")
        for i, clip in enumerate(clips, 1):
            print(f"    {i}. {clip['start_time']} - {clip['end_time']} ({clip.get('hook', 'N/A')[:50]}...)")

    # Step 6: Generate clips with subtitles
    print("\n" + "─" * 70)
    print("STEP 6: Generate 9:16 Clips with Subtitles")
    print("─" * 70)

    face_tracker = FaceTracker(job_folder)
    subtitle_renderer = SubtitleRenderer(job_folder)

    generated_clips = []

    for i, clip_info in enumerate(clips[:2], 1):  # Process first 2 clips for testing
        print(f"\n  Processing clip {i}/{min(2, len(clips))}...")

        # Track faces
        print(f"    🔍 Tracking faces...")
        crop_result = face_tracker.track_faces_in_clip(
            original_video_path,
            clip_info['start_time'],
            clip_info['end_time']
        )

        # Create base clip
        clip_path = job_folder / f"clip_{i:02d}_no_subs.mp4"
        print(f"    ✂️  Cutting and cropping...")
        processor.create_vertical_clip(
            original_video_path,
            clip_path,
            clip_info['start_time'],
            clip_info['end_time'],
            crop_result['x'],
            crop_result['y'],
            crop_result['width'],
            crop_result['height'],
            source_width=video_info['width'],
            source_height=video_info['height']
        )

        # Extract words for this clip
        from utils.helpers import parse_timestamp
        clip_start = parse_timestamp(clip_info['start_time'])
        clip_end = parse_timestamp(clip_info['end_time'])
        clip_duration = clip_end - clip_start

        clip_words = []
        for segment in romanized_transcript.get('segments', []):
            if 'words' in segment:
                for word in segment['words']:
                    word_start = word['start']
                    word_end = word['end']

                    if word_end > clip_start and word_start < clip_end:
                        clip_words.append({
                            'text_roman': word.get('text_roman', word.get('text', '')),
                            'start': max(0, word_start - clip_start),
                            'end': min(clip_duration, word_end - clip_start)
                        })

        print(f"    📝 Rendering subtitles ({len(clip_words)} words)...")

        # Render subtitles
        subtitle_overlay = subtitle_renderer.render_subtitles_for_clip(
            romanized_words=clip_words,
            clip_duration=clip_duration,
            style_name=settings.subtitle_style,
            resolution=(1080, 1920),
            fps=settings.subtitle_fps
        )

        # Composite subtitles
        final_clip_path = job_folder / f"clip_{i:02d}.mp4"
        print(f"    🎬 Compositing subtitles...")
        processor.composite_subtitles(clip_path, subtitle_overlay, final_clip_path)

        generated_clips.append({
            'index': i,
            'path': final_clip_path,
            'start_time': clip_info['start_time'],
            'end_time': clip_info['end_time'],
            'hook': clip_info.get('hook', 'N/A')
        })

        print(f"    ✓ Clip complete: {final_clip_path.name}")

    # Step 7: Summary
    print("\n" + "=" * 70)
    print("TEST COMPLETE!")
    print("=" * 70)

    # Save results
    results = {
        'job_id': job_folder.name,
        'input_video': str(video_path),
        'video_info': video_info,
        'transcript_segments': len(transcript_data.get('segments', [])),
        'selected_clips': len(clips),
        'generated_clips': len(generated_clips),
        'clips': [
            {
                'filename': clip['path'].name,
                'start_time': clip['start_time'],
                'end_time': clip['end_time'],
                'hook': clip['hook']
            }
            for clip in generated_clips
        ]
    }

    results_path = job_folder / "test_results.json"
    with open(results_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n📊 Results saved: {results_path}")
    print(f"\n📁 Output folder: {job_folder}")
    print(f"\n✓ Generated {len(generated_clips)} clips with Hindi subtitles:")
    for clip in generated_clips:
        clip_size = clip['path'].stat().st_size / 1024 / 1024
        print(f"   • {clip['path'].name} ({clip_size:.2f} MB)")
        print(f"     {clip['start_time']} - {clip['end_time']}")
        print(f"     Hook: {clip['hook'][:60]}...")
        print()


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 test_hindi_full_pipeline.py <hindi_video.mp4>")
        print("\nExample:")
        print("  python3 test_hindi_full_pipeline.py my_hindi_video.mp4")
        print("\nMake sure your .env file has:")
        print("  RUNPOD_API_KEY=...")
        print("  RUNPOD_ENDPOINT=...")
        print("  OPENROUTER_API_KEY=...")
        sys.exit(1)

    video_path = Path(sys.argv[1])

    # Run the async test
    asyncio.run(test_full_pipeline(video_path))


if __name__ == "__main__":
    main()
