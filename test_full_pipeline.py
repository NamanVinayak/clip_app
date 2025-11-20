
import asyncio
import shutil
from pathlib import Path
import json
import sys

# Add project root to path
sys.path.append('/Users/naman/Downloads/clip_app')

from config import settings
from modules.video_processor import VideoProcessor
from modules.transcriber import Transcriber
from modules.clip_selector import ClipSelector
from modules.face_tracker import FaceTracker
from modules.transliterator import HindiTransliterator
from modules.subtitle_renderer import SubtitleRenderer
from utils.helpers import create_job_folder, get_video_info, setup_logger, parse_timestamp

async def run_pipeline(video_path_str: str):
    video_path = Path(video_path_str)
    if not video_path.exists():
        print(f"Error: Video not found at {video_path}")
        return

    print(f"Starting full pipeline test on: {video_path.name}")
    
    # Create job folder
    job_folder = create_job_folder(settings.outputs_dir)
    logger = setup_logger("PipelineTest", job_folder / "processing.log")
    print(f"Job folder: {job_folder}")

    try:
        # 1. Copy video
        print("1. Copying video...")
        work_video_path = job_folder / "original_video.mp4"
        shutil.copy2(video_path, work_video_path)
        
        video_info = get_video_info(work_video_path)
        print(f"   Video info: {video_info}")

        # 2. Extract Audio
        print("2. Extracting audio...")
        processor = VideoProcessor(job_folder)
        audio_path = processor.extract_audio(work_video_path)
        print(f"   Audio extracted: {audio_path.name}")

        # 3. Transcribe
        print("3. Transcribing (WhisperX)...")
        transcriber = Transcriber(
            api_key=settings.runpod_api_key,
            endpoint=settings.runpod_endpoint,
            job_folder=job_folder
        )
        transcript = await transcriber.transcribe(audio_path, language='hi')
        print("   Transcription complete")

        # 4. Analyze for Clips
        print("4. Selecting viral clips (LLM)...")
        selector = ClipSelector(
            api_key=settings.openrouter_api_key,
            model=settings.llm_model,
            job_folder=job_folder,
            min_duration=settings.min_clip_duration,
            max_duration=settings.max_clip_duration,
            target_clips=settings.target_clips
        )
        clip_suggestions = await selector.select_clips(transcript)
        print(f"   Found {len(clip_suggestions)} clips")

        # 5. Track Faces and Generate Clips
        print("5. Tracking faces and generating clips...")
        tracker = FaceTracker(job_folder)
        generated_clips = []

        for i, clip in enumerate(clip_suggestions):
            print(f"   Processing clip {i+1}/{len(clip_suggestions)}...")
            
            # Track faces
            tracking_data = tracker.track_faces_in_clip(
                work_video_path,
                clip['start_time'],
                clip['end_time']
            )

            # Generate vertical clip
            output_name = f"clip_{i+1:02d}.mp4"
            processor.create_vertical_clip(
                video_path=work_video_path,
                start_time=clip['start_time'],
                duration=clip.get('duration_seconds', 30),
                face_x=tracking_data.get('face_center_x'),
                face_y=tracking_data.get('face_center_y'),
                source_width=video_info['width'],
                source_height=video_info['height'],
                output_name=output_name
            )
            
            generated_clips.append({
                "path": job_folder / output_name,
                "info": clip
            })

        # 6. Add Subtitles
        print("6. Adding subtitles...")
        transliterator = HindiTransliterator(job_folder)
        subtitle_renderer = SubtitleRenderer(job_folder)
        
        # Transliterate (even if English, it handles it)
        romanized_transcript = transliterator.transliterate_transcript(transcript)

        for i, clip_data in enumerate(generated_clips):
            print(f"   Rendering subtitles for clip {i+1}...")
            clip_info = clip_data['info']
            
            clip_start = parse_timestamp(clip_info['start_time'])
            clip_end = parse_timestamp(clip_info['end_time'])
            clip_duration = clip_end - clip_start

            # Extract words
            clip_words = []
            for segment in romanized_transcript.get('segments', []):
                if 'words' in segment:
                    for word in segment['words']:
                        word_start = word.get('start', 0)
                        word_end = word.get('end', 0)
                        
                        if word_end > clip_start and word_start < clip_end:
                            clip_words.append({
                                'text_roman': word.get('text_roman', word.get('text', '')),
                                'start': max(0, word_start - clip_start),
                                'end': min(clip_duration, word_end - clip_start)
                            })

            if not clip_words:
                print(f"   Warning: No words found for clip {i+1}")
                continue

            # Render
            subtitle_overlay = subtitle_renderer.render_subtitles_for_clip(
                romanized_words=clip_words,
                clip_duration=clip_duration,
                style_name="simple_caption",
                resolution=(1080, 1920),
                fps=30
            )

            # Composite
            final_output = job_folder / f"clip_{i+1:02d}_final.mp4"
            processor.composite_subtitles(
                clip_data['path'],
                subtitle_overlay,
                final_output
            )
            print(f"   ✓ Created {final_output.name}")

        print("\nPipeline complete!")
        print(f"Output folder: {job_folder}")

    except Exception as e:
        print(f"\nError running pipeline: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        asyncio.run(run_pipeline(sys.argv[1]))
    else:
        print("Please provide video path")
