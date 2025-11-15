from fastapi import FastAPI, File, UploadFile, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from pathlib import Path
import shutil
import asyncio
from typing import List, Dict
import json

from config import settings
from modules.video_processor import VideoProcessor
from modules.transcriber import Transcriber
from modules.clip_selector import ClipSelector
from modules.face_tracker import FaceTracker
from utils.helpers import create_job_folder, get_video_info, setup_logger

app = FastAPI(title="Automated Shorts Generator")

# Mount static files
app.mount("/static", StaticFiles(directory=settings.static_dir), name="static")

# Global logger
logger = setup_logger("Main")

# WebSocket connections
active_connections: List[WebSocket] = []


@app.get("/", response_class=HTMLResponse)
async def home():
    """Serve the main web interface"""
    index_path = settings.static_dir / "index.html"
    with open(index_path, 'r') as f:
        return f.read()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time progress updates"""
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        active_connections.remove(websocket)


async def send_progress(step: str, status: str, message: str, progress: int):
    """Send progress update to all connected WebSocket clients"""
    data = {
        "step": step,
        "status": status,
        "message": message,
        "progress": progress
    }

    disconnected = []
    for connection in active_connections:
        try:
            await connection.send_json(data)
        except:
            disconnected.append(connection)

    # Remove disconnected clients
    for conn in disconnected:
        active_connections.remove(conn)


@app.post("/process")
async def process_video(video: UploadFile = File(...)):
    """
    Main endpoint to process video and generate shorts

    Steps:
    1. Upload and validate video
    2. Extract audio
    3. Transcribe with WhisperX
    4. Analyze for viral clips
    5. Track faces
    6. Generate vertical clips
    """
    job_folder = None

    try:
        # Step 1: Upload Video
        await send_progress("upload", "active", "Uploading video...", 5)

        # Create job folder
        job_folder = create_job_folder(settings.outputs_dir)
        job_logger = setup_logger("Job", job_folder / "processing.log")

        # Save uploaded video
        video_path = job_folder / "original_video.mp4"
        with open(video_path, 'wb') as f:
            shutil.copyfileobj(video.file, f)

        job_logger.info(f"Video uploaded: {video.filename}")

        # Validate video
        video_info = get_video_info(video_path)
        job_logger.info(f"Video info: {video_info}")

        await send_progress("upload", "complete", "Video uploaded successfully", 10)

        # Step 2: Extract Audio
        await send_progress("extract", "active", "Extracting audio from video...", 15)

        processor = VideoProcessor(job_folder)
        audio_path = processor.extract_audio(video_path)

        await send_progress("extract", "complete", "Audio extracted", 25)

        # Step 3: Transcribe with WhisperX
        await send_progress("transcribe", "active", "Uploading audio and transcribing with WhisperX (this may take a few minutes)...", 30)

        transcriber = Transcriber(
            api_key=settings.runpod_api_key,
            endpoint=settings.runpod_endpoint,
            job_folder=job_folder
        )
        # Transcriber will automatically upload audio to file.io for public access
        transcript = await transcriber.transcribe(audio_path)

        await send_progress("transcribe", "complete", "Transcription complete", 45)

        # Step 4: Analyze for Viral Clips
        await send_progress("analyze", "active", "Analyzing transcript for viral clips...", 50)

        selector = ClipSelector(
            api_key=settings.openrouter_api_key,
            model=settings.llm_model,
            job_folder=job_folder,
            min_duration=settings.min_clip_duration,
            max_duration=settings.max_clip_duration,
            target_clips=settings.target_clips
        )
        clip_suggestions = await selector.select_clips(transcript)

        if not clip_suggestions:
            raise HTTPException(status_code=500, detail="LLM did not suggest any clips")

        await send_progress("analyze", "complete", f"Found {len(clip_suggestions)} viral clips", 60)

        # Step 5 & 6: Track Faces and Generate Clips
        tracker = FaceTracker(job_folder)
        generated_clips = []

        for i, clip in enumerate(clip_suggestions):
            progress = 60 + int((i / len(clip_suggestions)) * 35)

            # Track faces
            await send_progress(
                "track",
                "active",
                f"Tracking faces in clip {i+1}/{len(clip_suggestions)}...",
                progress
            )

            tracking_data = tracker.track_faces_in_clip(
                video_path,
                clip['start_time'],
                clip['end_time']
            )

            # Generate clip
            await send_progress(
                "generate",
                "active",
                f"Generating clip {i+1}/{len(clip_suggestions)}...",
                progress + 2
            )

            face_center_x = tracking_data.get('face_center_x')
            face_center_y = tracking_data.get('face_center_y')
            output_name = f"clip_{i+1:02d}.mp4"

            clip_path = processor.create_vertical_clip(
                video_path=video_path,
                start_time=clip['start_time'],
                duration=clip.get('duration_seconds', 30),
                face_x=face_center_x,
                face_y=face_center_y,
                source_width=video_info['width'],
                source_height=video_info['height'],
                output_name=output_name
            )

            # Add clip info
            generated_clips.append({
                "title": clip.get('title', f'Clip {i+1}'),
                "url": f"/outputs/{job_folder.name}/{output_name}",
                "virality_score": clip.get('virality_score', 'N/A'),
                "reason": clip.get('reason', ''),
                "hook_type": clip.get('hook_type', ''),
                "start_time": clip['start_time'],
                "end_time": clip['end_time'],
                "duration": clip.get('duration_seconds', 30),
                "first_3_seconds": clip.get('first_3_seconds', '')
            })

        await send_progress("generate", "complete", "All clips generated!", 100)

        # Save results summary
        results_path = job_folder / "results.json"
        with open(results_path, 'w', encoding='utf-8') as f:
            json.dump({
                "job_id": job_folder.name,
                "original_video": str(video_path),
                "clips": generated_clips,
                "video_info": video_info
            }, f, ensure_ascii=False, indent=2)

        job_logger.info("Processing complete!")

        return JSONResponse({
            "success": True,
            "job_id": job_folder.name,
            "clips": generated_clips,
            "message": f"Successfully generated {len(generated_clips)} clips!"
        })

    except Exception as e:
        logger.error(f"Processing error: {str(e)}")
        await send_progress("error", "error", f"Error: {str(e)}", 0)

        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
                "detail": "Processing failed. Check logs for details."
            }
        )


@app.get("/outputs/{job_id}/{filename}")
async def get_clip(job_id: str, filename: str):
    """Serve generated clip files"""
    clip_path = settings.outputs_dir / job_id / filename

    if not clip_path.exists():
        raise HTTPException(status_code=404, detail="Clip not found")

    return FileResponse(clip_path)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "runpod_configured": bool(settings.runpod_api_key),
        "openrouter_configured": bool(settings.openrouter_api_key)
    }


@app.get("/test/step1")
async def test_step1_upload():
    """Test Step 1: Verify upload functionality"""
    return {
        "step": 1,
        "name": "Upload Video",
        "status": "ready",
        "instructions": "Use POST /process with video file to test upload"
    }


@app.get("/test/step2")
async def test_step2_extract():
    """Test Step 2: Extract audio from a test video"""
    # This would need a test video file
    return {
        "step": 2,
        "name": "Extract Audio",
        "status": "ready",
        "instructions": "Upload a video to test audio extraction"
    }


if __name__ == "__main__":
    import uvicorn

    print("=" * 60)
    print("🎬 Automated Shorts Generator")
    print("=" * 60)
    print(f"📁 Upload folder: {settings.uploads_dir}")
    print(f"📁 Output folder: {settings.outputs_dir}")
    print(f"🔧 RunPod configured: {bool(settings.runpod_api_key)}")
    print(f"🔧 OpenRouter configured: {bool(settings.openrouter_api_key)}")
    print("=" * 60)
    print("🌐 Starting server at http://localhost:8000")
    print("📖 API docs at http://localhost:8000/docs")
    print("=" * 60)

    uvicorn.run(app, host="0.0.0.0", port=8000)
