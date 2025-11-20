#!/usr/bin/env python3
"""
Hindi Subtitle Demo - Without API Keys

This demonstrates the subtitle rendering system using a mock transcript.
Since we don't have API keys, we'll create realistic Hindi text with
word-level timestamps to show how the subtitle system works.
"""

import sys
import json
from pathlib import Path

# Add project modules
sys.path.insert(0, str(Path(__file__).parent))

from modules.video_processor import VideoProcessor
from modules.transliterator import HindiTransliterator
from modules.subtitle_renderer import SubtitleRenderer
from utils.helpers import setup_logger, create_job_folder, get_video_info

def create_mock_hindi_transcript():
    """Create a realistic Hindi transcript with word-level timestamps"""

    # Hindi text from a Bollywood song (Devanagari)
    hindi_sentences = [
        "दिल क्या करे जब किसी से किसी को प्यार हो जाए",
        "कैसे ये आंखों को समझाएं के यार हो जाए",
        "दिल तोड़ के जाना ना प्यार में ऐसा करना ना",
        "यादों के सहारे जीना हमको ये सिखाना ना"
    ]

    # Create segments with words and timestamps
    segments = []
    current_time = 2.0  # Start at 2 seconds

    for sentence_idx, sentence in enumerate(hindi_sentences):
        words_list = sentence.split()
        segment_start = current_time

        # Create word-level timestamps
        words_data = []
        for word in words_list:
            word_duration = len(word) * 0.15 + 0.2  # Approximate duration based on word length
            words_data.append({
                'text': word,
                'start': current_time,
                'end': current_time + word_duration
            })
            current_time += word_duration + 0.1  # Small gap between words

        segment_end = current_time

        segments.append({
            'text': sentence,
            'start': segment_start,
            'end': segment_end,
            'words': words_data
        })

        current_time += 0.5  # Pause between sentences

    return {
        'language': 'hi',
        'segments': segments
    }


def main():
    print("=" * 70)
    print("HINDI SUBTITLE DEMO (Mock Transcript)")
    print("=" * 70)
    print("\nThis demo shows the subtitle system working WITHOUT API keys")
    print("by using a realistic mock Hindi transcript.\n")

    # Setup
    if len(sys.argv) > 1:
        video_path = Path(sys.argv[1])
    else:
        video_path = Path("hindi_song_video.mp4")

    if not video_path.exists():
        print(f"❌ Video not found: {video_path}")
        if len(sys.argv) > 1:
            print("   Please check the path provided.")
        else:
            print("   Please run this after downloading the Hindi video")
        return

    # Create job folder
    job_folder = Path("outputs") / "demo_hindi_subtitles"
    job_folder.mkdir(parents=True, exist_ok=True)

    logger = setup_logger("DemoSubtitles", job_folder / "demo.log")

    print(f"📁 Output folder: {job_folder}")
    print(f"📹 Input video: {video_path.name}")

    # Get video info
    video_info = get_video_info(video_path)
    print(f"\n📊 Video Info:")
    print(f"   Resolution: {video_info['width']}x{video_info['height']}")
    print(f"   Duration: {video_info['duration']:.2f}s ({video_info['duration']/60:.1f} minutes)")

    # Step 1: Extract audio
    print("\n" + "─" * 70)
    print("STEP 1: Audio Extraction")
    print("─" * 70)

    processor = VideoProcessor(job_folder)
    audio_path = processor.extract_audio(video_path)
    print(f"✓ Audio extracted: {audio_path.name} ({audio_path.stat().st_size / 1024:.1f} KB)")

    # Step 2: Create mock transcript
    print("\n" + "─" * 70)
    print("STEP 2: Mock Hindi Transcript")
    print("─" * 70)
    print("Creating realistic Hindi lyrics with word-level timestamps...")

    transcript_data = create_mock_hindi_transcript()

    # Save transcript
    transcript_path = job_folder / "mock_transcript.json"
    with open(transcript_path, 'w', encoding='utf-8') as f:
        json.dump(transcript_data, f, indent=2, ensure_ascii=False)

    print(f"✓ Mock transcript created: {len(transcript_data['segments'])} segments")
    print(f"\n  Sample text (Devanagari):")
    for i, seg in enumerate(transcript_data['segments'][:2], 1):
        print(f"    {i}. {seg['text']}")

    # Step 3: Transliterate to Roman script
    print("\n" + "─" * 70)
    print("STEP 3: Hindi → Roman Transliteration")
    print("─" * 70)

    transliterator = HindiTransliterator(job_folder)
    romanized_transcript = transliterator.transliterate_transcript(transcript_data)

    # Save romanized transcript
    romanized_path = job_folder / "romanized_transcript.json"
    with open(romanized_path, 'w', encoding='utf-8') as f:
        json.dump(romanized_transcript, f, indent=2, ensure_ascii=False)

    print(f"✓ Transliteration complete!")
    print(f"\n  Romanized text (English letters):")
    for i, seg in enumerate(romanized_transcript['segments'][:2], 1):
        print(f"    {i}. {seg.get('text_roman', 'N/A')}")

    # Step 4: Create short clip with subtitles
    print("\n" + "─" * 70)
    print("STEP 4: Generate 9:16 Clip with Subtitles")
    print("─" * 70)

    # Create a 15-second clip
    clip_start_time = "00:00:02"
    clip_end_time = "00:00:17"
    clip_duration = 15.0

    print(f"Creating clip from {clip_start_time} to {clip_end_time}...")

    # Calculate center crop for 9:16
    source_width = video_info['width']
    source_height = video_info['height']

    # For 9:16 aspect ratio
    target_aspect = 9 / 16  # 0.5625
    crop_height = source_height
    crop_width = int(crop_height * target_aspect)
    crop_x = (source_width - crop_width) // 2
    crop_y = 0

    print(f"   Crop: {crop_width}x{crop_height} at ({crop_x}, {crop_y})")

    # Create base clip (without subtitles)
    print(f"   ✂️  Cutting and cropping video...")

    # Use center position for face
    face_x = source_width // 2
    face_y = source_height // 2

    processor.create_vertical_clip(
        video_path,
        clip_start_time,
        clip_duration,
        face_x,
        face_y,
        source_width,
        source_height,
        "clip_no_subtitles.mp4"
    )

    base_clip_path = job_folder / "clip_no_subtitles.mp4"

    print(f"   ✓ Base clip created")

    # Extract words for this time range
    clip_words = []
    for segment in romanized_transcript['segments']:
        if 'words' in segment:
            for word in segment['words']:
                if word['start'] >= 0 and word['start'] < clip_duration:
                    clip_words.append({
                        'text_roman': word.get('text_roman', word['text']),
                        'start': word['start'],
                        'end': min(word['end'], clip_duration)
                    })

    print(f"   📝 Rendering subtitles for {len(clip_words)} words...")

    # Render subtitles
    subtitle_renderer = SubtitleRenderer(job_folder)
    subtitle_overlay = subtitle_renderer.render_subtitles_for_clip(
        romanized_words=clip_words,
        clip_duration=clip_duration,
        style_name="simple_caption",  # Use simple caption style
        resolution=(1080, 1920),
        fps=30
    )

    print(f"   ✓ Subtitle overlay rendered")

    # Composite subtitles onto video
    final_clip_path = job_folder / "clip_with_subtitles.mp4"
    print(f"   🎬 Compositing subtitles...")

    processor.composite_subtitles(base_clip_path, subtitle_overlay, final_clip_path)

    print(f"   ✓ Final clip created!")

    # Summary
    print("\n" + "=" * 70)
    print("DEMO COMPLETE!")
    print("=" * 70)

    final_size = final_clip_path.stat().st_size / 1024 / 1024

    print(f"\n✅ Generated Hindi subtitle demo video:")
    print(f"   📁 {final_clip_path}")
    print(f"   📐 Resolution: 1080x1920 (9:16 vertical)")
    print(f"   ⏱️  Duration: 15 seconds")
    print(f"   💾 Size: {final_size:.2f} MB")
    print(f"\n📝 Subtitle features demonstrated:")
    print(f"   ✓ Hindi Devanagari → Roman transliteration")
    print(f"   ✓ Word-by-word timing synchronization")
    print(f"   ✓ Professional subtitle styling (simple_caption)")
    print(f"   ✓ Safe zone positioning (bottom 30%)")
    print(f"   ✓ 9:16 vertical format for Reels/Shorts")

    print(f"\n📂 All files saved in: {job_folder}/")
    print(f"   • mock_transcript.json (Hindi Devanagari)")
    print(f"   • romanized_transcript.json (Roman script)")
    print(f"   • clip_with_subtitles.mp4 (Final output)")

    print(f"\n💡 This demonstrates the subtitle system WITHOUT needing:")
    print(f"   • RunPod API (WhisperX transcription)")
    print(f"   • OpenRouter API (LLM clip selection)")
    print(f"\n   The actual pipeline would use WhisperX for real transcription.")
    print(f"   This mock transcript proves the rendering system works!")


if __name__ == "__main__":
    main()
