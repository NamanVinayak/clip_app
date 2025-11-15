# CLAUDE.md - AI Assistant Guide

**Repository**: Automated Shorts Generator
**Purpose**: Transform long-form Hindi videos into viral-ready vertical clips using AI
**Target Platform**: MacBook M4 Pro (Apple Silicon optimized)
**Last Updated**: 2025-11-15

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture & Design](#architecture--design)
3. [Codebase Structure](#codebase-structure)
4. [Key Technologies](#key-technologies)
5. [Development Workflows](#development-workflows)
6. [Code Conventions](#code-conventions)
7. [External Dependencies](#external-dependencies)
8. [Common Tasks](#common-tasks)
9. [Testing Strategy](#testing-strategy)
10. [Troubleshooting Guide](#troubleshooting-guide)

---

## Project Overview

### What This Application Does

This is a FastAPI-based web application that automatically converts long-form Hindi videos into short vertical clips optimized for Instagram Reels and YouTube Shorts. The pipeline:

1. **Uploads** 16:9 format videos (MP4, MOV, AVI)
2. **Extracts** audio using FFmpeg
3. **Transcribes** Hindi speech using WhisperX on RunPod
4. **Analyzes** transcript with LLM (Qwen 32B via OpenRouter) to identify viral-worthy clips
5. **Tracks** faces using YOLOv8 with Apple Silicon GPU acceleration
6. **Generates** 9:16 vertical clips with face-centered cropping

### Design Philosophy

- **No-code user experience**: Drag-and-drop web interface
- **Modular architecture**: Separate concerns (transcription, analysis, processing)
- **Real-time feedback**: WebSocket-based progress tracking
- **Optimized for M4 Pro**: Leverages Metal Performance Shaders (MPS) for GPU acceleration
- **Production-ready**: Comprehensive logging, error handling, structured output

---

## Architecture & Design

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Web UI (HTML/CSS/JS)                 │
│              - Drag-and-drop upload                      │
│              - WebSocket progress updates                │
│              - Clip preview/download                     │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│               FastAPI Server (main.py)                   │
│              - REST API endpoints                        │
│              - WebSocket management                      │
│              - Request orchestration                     │
└─────┬──────┬──────┬──────┬──────┬──────────────────────┘
      │      │      │      │      │
      │      │      │      │      │
      ▼      ▼      ▼      ▼      ▼
   ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐
   │Video│ │Trans│ │Clip│ │Face│ │Utils│
   │Proc │ │crib │ │Sel │ │Track│ │     │
   └────┘ └────┘ └────┘ └────┘ └────┘
      │      │      │      │
      ▼      ▼      ▼      ▼
   ┌────────────────────────────┐
   │   External Dependencies     │
   │  - FFmpeg (video)           │
   │  - RunPod (WhisperX)        │
   │  - OpenRouter (LLM)         │
   │  - YOLOv8 (face detection)  │
   └────────────────────────────┘
```

### Processing Pipeline

```
POST /process
    ↓
1. Upload & Validate (VideoProcessor)
    → Save to outputs/job_YYYYMMDD_HHMMSS/original_video.mp4
    ↓
2. Extract Audio (VideoProcessor)
    → FFmpeg: video → audio.wav (16kHz mono)
    ↓
3. Transcribe (Transcriber)
    → Upload audio to tmpfiles.org
    → Call RunPod WhisperX endpoint
    → Save transcript.json + transcript.srt
    ↓
4. Analyze Transcript (ClipSelector)
    → Build viral selection prompt
    → Call OpenRouter LLM API
    → Filter clips by duration constraints
    → Save clip_suggestions.json
    ↓
5. For Each Clip:
    a. Track Faces (FaceTracker)
       → YOLOv8 pose detection (MPS accelerated)
       → Calculate median face position
       → Determine 9:16 crop window
    b. Generate Clip (VideoProcessor)
       → FFmpeg: cut, crop, scale to 1080x1920
       → Save clip_01.mp4, clip_02.mp4, etc.
    ↓
6. Return Results
    → JSON response with clip URLs
    → Save results.json summary
```

### Data Flow

```
User Video
    ↓ [FastAPI File Upload]
original_video.mp4 (local)
    ↓ [FFmpeg extraction]
audio.wav (local)
    ↓ [tmpfiles.org upload]
Public audio URL
    ↓ [RunPod WhisperX API]
transcript.json (segments with timestamps)
    ↓ [OpenRouter LLM API]
clip_suggestions.json (timestamps + analysis)
    ↓ [YOLOv8 face tracking]
crop_params (x, y, width, height)
    ↓ [FFmpeg cut + crop]
clip_01.mp4, clip_02.mp4, ... (1080x1920)
```

---

## Codebase Structure

### File Organization

```
clip_app/
├── main.py                          # FastAPI app, routes, WebSocket
├── config.py                        # Pydantic settings, env vars
├── requirements.txt                 # Python dependencies
├── start.sh                         # Quick start script (bash)
│
├── modules/                         # Core business logic
│   ├── __init__.py
│   ├── video_processor.py           # FFmpeg operations (extract, cut, crop)
│   ├── transcriber.py               # WhisperX integration via RunPod
│   ├── clip_selector.py             # LLM viral clip analysis
│   └── face_tracker.py              # YOLOv8 face detection & tracking
│
├── utils/                           # Shared utilities
│   ├── __init__.py
│   └── helpers.py                   # Logging, timestamps, video info
│
├── static/                          # Web UI (served by FastAPI)
│   ├── index.html                   # Main interface
│   ├── style.css                    # Dark theme UI
│   └── script.js                    # Frontend logic, WebSocket client
│
├── uploads/                         # Temporary upload storage (auto-created)
│
└── outputs/                         # Generated clips (auto-created)
    └── job_YYYYMMDD_HHMMSS/        # Each job gets timestamped folder
        ├── original_video.mp4
        ├── audio.wav
        ├── transcript.json
        ├── transcript.srt
        ├── clip_suggestions.json
        ├── clip_01.mp4
        ├── clip_02.mp4
        ├── processing.log           # Detailed logs
        └── results.json             # Final summary
```

### Module Responsibilities

#### `main.py` (290 lines)
- **FastAPI application** entry point
- **Routes**:
  - `GET /` - Serve web UI
  - `POST /process` - Main video processing endpoint
  - `GET /outputs/{job_id}/{filename}` - Serve generated clips
  - `GET /health` - Health check
  - `WS /ws` - WebSocket for progress updates
- **WebSocket management** for real-time updates
- **Orchestrates** entire processing pipeline
- **Error handling** and logging

#### `config.py` (39 lines)
- **Pydantic Settings** for configuration management
- **Environment variables** from `.env` file:
  - API keys (RunPod, OpenRouter)
  - Processing constraints (clip duration, target count)
  - File paths (uploads, outputs, static)
- **Auto-creates** necessary directories on startup

#### `modules/video_processor.py` (183 lines)
- **FFmpeg wrapper** for video operations
- **Methods**:
  - `extract_audio()` - Convert video to 16kHz mono WAV
  - `cut_clip()` - Extract clip with timestamps and cropping
  - `create_vertical_clip()` - Generate 9:16 clip with face-centered crop
  - `get_frame_at_time()` - Extract single frame for analysis
- **Handles** crop boundary calculations
- **Validates** FFmpeg command success

#### `modules/transcriber.py` (245 lines)
- **WhisperX integration** via RunPod serverless endpoint
- **Methods**:
  - `transcribe()` - Main transcription method
  - `upload_audio_to_tmpfiles()` - Upload to public hosting
- **Converts** RunPod response to standardized format
- **Saves** both JSON and SRT formats
- **Alternative implementation** for direct file upload (TranscriberFileUpload)

#### `modules/clip_selector.py` (305 lines)
- **LLM-powered viral clip selection**
- **OpusClip-inspired** analysis methodology
- **Viral criteria**:
  - Strong hooks (first 3 seconds)
  - Complete thoughts (15-60 seconds)
  - Emotional peaks
  - Platform optimization
- **Methods**:
  - `select_clips()` - Analyze transcript and select clips
  - `_build_viral_prompt()` - Construct LLM prompt
  - `_call_llm()` - OpenRouter API call
- **Strict validation** of clip duration (enforces MAX_CLIP_DURATION)
- **Detailed system prompt** with platform-specific knowledge

#### `modules/face_tracker.py` (326 lines)
- **YOLOv8 pose detection** for accurate face tracking
- **Apple Silicon optimized** (uses MPS device)
- **Methods**:
  - `track_faces_in_clip()` - Track faces across clip duration
  - `_calculate_optimal_crop()` - Calculate 9:16 crop window
  - `_get_fallback_crop()` - Center crop if no faces detected
  - `detect_face_in_frame()` - Single frame detection
- **Uses keypoints** (nose, eyes) for precise face positioning
- **Median-based** crop calculation (robust to outliers)
- **Comprehensive logging** of detection quality

#### `utils/helpers.py` (96 lines)
- **Shared utility functions**
- **Methods**:
  - `setup_logger()` - Configure logging (console + file)
  - `create_job_folder()` - Create timestamped output directory
  - `format_timestamp()` - Convert seconds to HH:MM:SS
  - `parse_timestamp()` - Convert HH:MM:SS to seconds
  - `get_video_info()` - FFprobe wrapper for video metadata

---

## Key Technologies

### Core Stack

| Technology | Version | Purpose | Notes |
|------------|---------|---------|-------|
| **Python** | 3.10+ | Backend language | Async/await support required |
| **FastAPI** | 0.115.0+ | Web framework | Async endpoints, automatic docs |
| **Pydantic** | 2.0.0+ | Config/validation | Type-safe settings |
| **Uvicorn** | - | ASGI server | Included with FastAPI |

### Video Processing

| Technology | Purpose | Key Features |
|------------|---------|--------------|
| **FFmpeg** | Video/audio manipulation | Extract, cut, crop, scale, encode |
| **OpenCV** | Video frame access | Used by YOLOv8 for frame reading |
| **YOLOv8** | Face/person detection | Pose model (yolov8n-pose.pt) |
| **Ultralytics** | YOLO framework | MPS (Metal) GPU support |

### AI/ML Services

| Service | Model | Purpose | API |
|---------|-------|---------|-----|
| **RunPod** | WhisperX | Hindi transcription | Serverless endpoint (/runsync) |
| **OpenRouter** | Qwen 2.5 72B | Viral clip analysis | Chat completions API |

### Frontend

| Technology | Purpose | Notes |
|------------|---------|-------|
| **HTML5** | UI structure | Single-page app |
| **CSS3** | Styling | Dark theme, responsive |
| **JavaScript** | Client logic | WebSocket, drag-drop, fetch API |
| **WebSocket** | Real-time updates | Progress tracking |

---

## Development Workflows

### Initial Setup

```bash
# 1. Clone/navigate to repository
cd /home/user/clip_app

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment (copy and edit)
cp .env.example .env
nano .env  # Add API keys

# 5. Verify FFmpeg installation
ffmpeg -version

# 6. Start server
python main.py
# or
./start.sh
```

### Environment Variables (.env)

```env
# Required: RunPod WhisperX Configuration
RUNPOD_API_KEY=your_runpod_api_key_here
RUNPOD_ENDPOINT=https://api.runpod.ai/v2/YOUR_ENDPOINT_ID

# Required: OpenRouter LLM Configuration
OPENROUTER_API_KEY=your_openrouter_api_key_here
LLM_MODEL=qwen/qwen-2.5-72b-instruct

# Optional: Application Settings
MAX_VIDEO_SIZE_MB=2000
MIN_CLIP_DURATION=15
MAX_CLIP_DURATION=60
TARGET_CLIPS=5
```

### Running the Application

```bash
# Development mode (auto-reload)
fastapi dev main.py

# Production mode
python main.py
# or
uvicorn main:app --host 0.0.0.0 --port 8000

# Quick start script
./start.sh
```

### API Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## Code Conventions

### Python Style

- **Type hints** for function signatures (where applicable)
- **Docstrings** for classes and complex methods
- **Async/await** for I/O operations (API calls, file operations)
- **Pathlib** for file paths (not string concatenation)
- **Logging** instead of print statements
- **Snake_case** for variables/functions
- **PascalCase** for classes

### Example Pattern

```python
from pathlib import Path
from typing import Dict, Optional
from utils.helpers import setup_logger

class ExampleProcessor:
    """Brief class description"""

    def __init__(self, job_folder: Path):
        self.job_folder = job_folder
        self.logger = setup_logger(
            "ExampleProcessor",
            job_folder / "processing.log"
        )

    async def process(self, input_path: Path) -> Dict:
        """
        Process input and return result

        Args:
            input_path: Path to input file

        Returns:
            Dict with processing results
        """
        self.logger.info(f"Processing {input_path.name}")

        try:
            # Implementation
            result = self._do_work(input_path)
            self.logger.info("Processing complete")
            return result
        except Exception as e:
            self.logger.error(f"Processing failed: {e}")
            raise
```

### Error Handling

- **Try/except** blocks for external dependencies (FFmpeg, API calls)
- **Log errors** before raising
- **Raise HTTPException** in FastAPI endpoints
- **Provide context** in exception messages

### Logging Strategy

```python
# Each module creates its own logger
logger = setup_logger("ModuleName", job_folder / "processing.log")

# Log levels
logger.debug("Detailed diagnostic information")
logger.info("Normal operation updates")
logger.warning("Unexpected but handled situations")
logger.error("Errors that need attention")
```

### Configuration Management

- **All settings** defined in `config.py` using Pydantic
- **Environment variables** preferred over hardcoded values
- **Validation** happens at startup
- **Defaults** provided for optional settings

---

## External Dependencies

### FFmpeg Commands

**Extract Audio**:
```bash
ffmpeg -i input.mp4 -vn -acodec pcm_s16le -ar 16000 -ac 1 -y output.wav
```

**Cut and Crop Clip**:
```bash
ffmpeg -ss 00:01:30 -i input.mp4 -to 00:02:00 \
  -vf "crop=1080:1920:400:0,scale=1080:1920" \
  -c:v libx264 -preset medium -crf 23 \
  -c:a aac -b:a 128k -y output.mp4
```

### RunPod WhisperX API

**Endpoint**: `https://api.runpod.ai/v2/{ENDPOINT_ID}/runsync`

**Request**:
```json
{
  "input": {
    "audio_file": "https://tmpfiles.org/dl/12345/audio.wav",
    "language": "hi",
    "batch_size": 64,
    "align_output": true,
    "diarization": false
  }
}
```

**Response**:
```json
{
  "output": {
    "text": "Full transcript...",
    "segments": [
      {
        "start": 0.0,
        "end": 2.5,
        "text": "नमस्ते"
      }
    ],
    "language": "hi"
  }
}
```

### OpenRouter API

**Endpoint**: `https://openrouter.ai/api/v1/chat/completions`

**Request**:
```json
{
  "model": "qwen/qwen-2.5-72b-instruct",
  "messages": [
    {"role": "system", "content": "System prompt..."},
    {"role": "user", "content": "Analyze this transcript..."}
  ],
  "temperature": 0.7,
  "max_tokens": 2000
}
```

**Expected Response**:
```json
{
  "choices": [
    {
      "message": {
        "content": "{\"clips\": [{\"start_time\": \"00:01:30\", ...}]}"
      }
    }
  ]
}
```

### YOLOv8 Usage

```python
from ultralytics import YOLO

# Load pose model (downloads on first run)
model = YOLO('yolov8n-pose.pt')

# Run detection (MPS for Apple Silicon)
results = model(frame, device='mps', verbose=False)

# Extract keypoints (17 COCO keypoints)
for result in results:
    keypoints = result.keypoints.xy[0].cpu().numpy()
    nose = keypoints[0]      # [x, y]
    left_eye = keypoints[1]
    right_eye = keypoints[2]
```

---

## Common Tasks

### Adding a New Processing Step

1. **Create module** in `modules/` directory
2. **Import** in `main.py`
3. **Add step** in `/process` endpoint
4. **Send progress updates** via WebSocket
5. **Log to** job folder
6. **Save intermediate files** to job folder

Example:
```python
# In modules/subtitle_generator.py
class SubtitleGenerator:
    def __init__(self, job_folder: Path):
        self.job_folder = job_folder
        self.logger = setup_logger("SubtitleGen", job_folder / "processing.log")

    def add_subtitles(self, clip_path: Path, srt_path: Path) -> Path:
        # Implementation
        pass

# In main.py
from modules.subtitle_generator import SubtitleGenerator

@app.post("/process")
async def process_video(video: UploadFile = File(...)):
    # ... existing code ...

    # New step
    await send_progress("subtitles", "active", "Adding subtitles...", 95)
    subtitle_gen = SubtitleGenerator(job_folder)
    for clip_path in clip_paths:
        subtitle_gen.add_subtitles(clip_path, srt_path)
    await send_progress("subtitles", "complete", "Subtitles added", 100)
```

### Modifying Viral Selection Criteria

Edit `modules/clip_selector.py`:

1. **System message** (lines 167-212): Platform knowledge and rules
2. **Prompt template** (lines 67-131): Selection criteria
3. **Validation logic** (lines 256-290): Duration constraints

### Changing Video Output Format

Edit `modules/video_processor.py` → `create_vertical_clip()`:

```python
# Current: 9:16 (1080x1920)
crop_width = 1080
crop_height = 1920

# For 1:1 square (Instagram Feed)
crop_width = 1080
crop_height = 1080

# For 4:5 (Instagram Portrait)
crop_width = 1080
crop_height = 1350
```

### Adding New API Endpoints

```python
# In main.py

@app.get("/status/{job_id}")
async def get_job_status(job_id: str):
    """Get status of a processing job"""
    job_folder = settings.outputs_dir / job_id

    if not job_folder.exists():
        raise HTTPException(status_code=404, detail="Job not found")

    results_path = job_folder / "results.json"
    if results_path.exists():
        with open(results_path, 'r') as f:
            return json.load(f)

    return {"status": "processing", "job_id": job_id}
```

### Customizing Face Tracking

Edit `modules/face_tracker.py`:

```python
# Adjust sampling rate (default: every 5 frames)
sample_rate = 10  # Faster processing, less accuracy
sample_rate = 1   # Slower processing, more accuracy

# Adjust confidence threshold (default: 0.5)
if confidence > 0.7:  # Higher threshold, fewer false positives

# Use different YOLO model
self.model = YOLO('yolov8s-pose.pt')  # Small (more accurate, slower)
self.model = YOLO('yolov8m-pose.pt')  # Medium
self.model = YOLO('yolov8n-pose.pt')  # Nano (faster, less accurate)
```

---

## Testing Strategy

### Manual Testing Steps

**Step 1: Upload & Validate**
```bash
# Use API docs
open http://localhost:8000/docs

# Test endpoint
curl -X POST "http://localhost:8000/process" \
  -F "video=@test_video.mp4"
```

**Step 2: Check Audio Extraction**
```bash
# Verify audio file exists
ls outputs/job_*/audio.wav

# Play audio
ffplay outputs/job_*/audio.wav
```

**Step 3: Verify Transcription**
```bash
# Check transcript
cat outputs/job_*/transcript.json | jq

# Check SRT file
cat outputs/job_*/transcript.srt
```

**Step 4: Review Clip Suggestions**
```bash
# View suggestions
cat outputs/job_*/clip_suggestions.json | jq
```

**Step 5: Validate Clips**
```bash
# Check clip resolution
ffprobe outputs/job_*/clip_01.mp4

# Expected output: 1080x1920
```

### Unit Testing Patterns

```python
# tests/test_video_processor.py
import pytest
from pathlib import Path
from modules.video_processor import VideoProcessor

def test_extract_audio(tmp_path):
    """Test audio extraction from video"""
    processor = VideoProcessor(tmp_path)

    # Requires test video file
    test_video = Path("tests/fixtures/test_video.mp4")
    audio_path = processor.extract_audio(test_video)

    assert audio_path.exists()
    assert audio_path.suffix == '.wav'

def test_timestamp_conversion():
    """Test timestamp formatting"""
    from utils.helpers import format_timestamp, parse_timestamp

    # Round trip
    seconds = 3665.5
    timestamp = format_timestamp(seconds)  # "01:01:05"
    assert parse_timestamp(timestamp) == int(seconds)
```

### Integration Testing

```python
# tests/test_integration.py
import pytest
import httpx

@pytest.mark.asyncio
async def test_full_pipeline():
    """Test complete video processing pipeline"""
    async with httpx.AsyncClient() as client:
        # Upload video
        with open("tests/fixtures/test_video.mp4", "rb") as f:
            response = await client.post(
                "http://localhost:8000/process",
                files={"video": f}
            )

        assert response.status_code == 200
        result = response.json()

        assert result["success"] is True
        assert len(result["clips"]) > 0
```

### Health Check

```bash
# Check configuration
curl http://localhost:8000/health

# Expected response:
{
  "status": "healthy",
  "runpod_configured": true,
  "openrouter_configured": true
}
```

---

## Troubleshooting Guide

### Common Issues

#### FFmpeg Not Found

**Symptom**: `FileNotFoundError: ffmpeg`

**Solution**:
```bash
# macOS
brew install ffmpeg

# Verify installation
ffmpeg -version
```

#### RunPod Connection Failed

**Symptom**: `HTTPError: 401 Unauthorized` or timeout

**Check**:
1. `.env` has correct `RUNPOD_API_KEY`
2. `RUNPOD_ENDPOINT` format: `https://api.runpod.ai/v2/{ENDPOINT_ID}`
3. RunPod account has credits
4. Endpoint is active (not paused)

**Debug**:
```bash
# Check logs
tail -f outputs/job_*/processing.log
```

#### OpenRouter API Error

**Symptom**: `HTTPError: 402 Payment Required` or model not found

**Check**:
1. `.env` has valid `OPENROUTER_API_KEY`
2. Account has credits
3. Model name is correct: `qwen/qwen-2.5-72b-instruct`

**Alternative models**:
```env
LLM_MODEL=anthropic/claude-3.5-sonnet
LLM_MODEL=meta-llama/llama-3.1-70b-instruct
```

#### No Faces Detected

**Symptom**: Warning in logs: "No faces detected in clip"

**Behavior**: Application continues with center crop fallback

**To Improve Detection**:
1. Ensure people are clearly visible in clips
2. Reduce `sample_rate` in `face_tracker.py` (more frames analyzed)
3. Lower confidence threshold in `face_tracker.py`

#### Out of Memory

**Symptom**: Process killed, memory errors

**Solutions**:
1. Use shorter source videos
2. Reduce `TARGET_CLIPS` in `.env`
3. Increase `sample_rate` in face tracking (fewer frames)
4. Close other applications

#### LLM Returns Invalid JSON

**Symptom**: `JSONDecodeError` in logs

**Debug**:
```python
# Check logs for raw LLM response
tail -f outputs/job_*/processing.log | grep "LLM content"
```

**Solution**: Already handled in code (removes markdown code blocks)

### Debugging Tips

**Enable Verbose Logging**:
```python
# In utils/helpers.py
logger.setLevel(logging.DEBUG)
```

**Check Job Logs**:
```bash
# Real-time monitoring
tail -f outputs/job_YYYYMMDD_HHMMSS/processing.log

# Search for errors
grep -i error outputs/job_*/processing.log
```

**Test Individual Components**:
```python
# Test face tracking only
from modules.face_tracker import FaceTracker
from pathlib import Path

job_folder = Path("outputs/test_job")
job_folder.mkdir(exist_ok=True)

tracker = FaceTracker(job_folder)
result = tracker.track_faces_in_clip(
    Path("test_video.mp4"),
    "00:00:10",
    "00:00:20"
)
print(result)
```

**Verify API Connectivity**:
```bash
# Test RunPod endpoint
curl -X POST "https://api.runpod.ai/v2/{ENDPOINT_ID}/health" \
  -H "Authorization: Bearer YOUR_API_KEY"

# Test OpenRouter
curl -X POST "https://openrouter.ai/api/v1/chat/completions" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen/qwen-2.5-72b-instruct","messages":[{"role":"user","content":"test"}]}'
```

---

## Working with This Codebase as an AI Assistant

### What You Should Know

1. **This is a production-ready application** - Changes should maintain stability
2. **External API costs money** - Test carefully before making API calls
3. **Processing is CPU/GPU intensive** - Optimize for Apple Silicon MPS
4. **Logging is critical** - Users debug via `processing.log`
5. **WebSocket updates are expected** - UI shows real-time progress

### Safe Changes

✅ **Can modify freely**:
- Viral selection criteria in `clip_selector.py`
- UI styling in `static/style.css`
- Crop calculations in `face_tracker.py`
- Configuration defaults in `config.py`
- Logging messages
- Documentation

⚠️ **Modify with caution**:
- FFmpeg commands (test thoroughly)
- API request formats (may break integrations)
- File paths (will break existing jobs)
- WebSocket message format (breaks UI)

❌ **Avoid changing**:
- Core pipeline order (will break processing)
- Job folder structure (breaks result retrieval)
- Settings class structure (breaks .env loading)

### When Adding Features

1. **Check if it fits the modular architecture**
2. **Add proper logging** to job folder
3. **Update WebSocket progress** for UI feedback
4. **Save intermediate files** to job folder
5. **Handle errors gracefully** (don't crash entire pipeline)
6. **Document in this file** (CLAUDE.md)

### When Debugging

1. **Always check `processing.log` first**
2. **Verify `.env` configuration**
3. **Test individual modules** before full pipeline
4. **Check external service status** (RunPod, OpenRouter)
5. **Review FFmpeg stderr** for video processing issues

### Useful Commands for Analysis

```bash
# Find all TODO comments
grep -r "TODO" --include="*.py" .

# Check code complexity
wc -l modules/*.py utils/*.py main.py

# List all imports
grep -h "^import\|^from" **/*.py | sort -u

# Find all API endpoints
grep -n "@app\." main.py

# Check for hardcoded values
grep -r "http://\|https://" --include="*.py" . | grep -v "api.runpod\|openrouter"
```

---

## Performance Considerations

### Bottlenecks

1. **Transcription** (2-5 minutes): RunPod network + processing
2. **Face tracking** (1-2 min/clip): YOLO inference on video frames
3. **Clip generation** (30 sec/clip): FFmpeg encoding

### Optimization Opportunities

**Reduce Transcription Time**:
- Use smaller audio files (already optimized to 16kHz mono)
- Consider caching transcripts for repeated processing

**Faster Face Tracking**:
- Increase `sample_rate` in `track_faces_in_clip()` (trade accuracy for speed)
- Use `FaceTrackerOptimized` class (samples every 30 frames)
- Consider smaller YOLO model if accuracy is sufficient

**Parallel Clip Generation**:
```python
# Current: Sequential processing
for clip in clips:
    track_faces()
    generate_clip()

# Potential: Parallel processing
import asyncio
tasks = [process_clip(clip) for clip in clips]
await asyncio.gather(*tasks)
```

### Expected Performance (M4 Pro, 24GB RAM)

| Video Length | Resolution | Transcription | Face Tracking | Total |
|--------------|-----------|---------------|---------------|-------|
| 5 min | 1080p | 1-2 min | 0.5 min | 2-3 min |
| 15 min | 4K | 2-3 min | 2-3 min | 5-8 min |
| 30 min | 4K | 3-5 min | 5-10 min | 10-15 min |

---

## Future Enhancement Ideas

### High Priority

1. **Batch Processing** - Process multiple videos in queue
2. **Subtitle Burning** - Add SRT subtitles to clips (already have SRT files!)
3. **Clip Preview** - Show suggestions before generating
4. **Quality Presets** - Fast/balanced/high quality modes

### Medium Priority

1. **Multiple Aspect Ratios** - Support 1:1, 4:5, 16:9
2. **Custom Crop Control** - User-defined focus points
3. **Thumbnail Generation** - Auto-generate cover images
4. **Audio Enhancement** - Normalize volume, reduce noise

### Low Priority

1. **Direct Social Upload** - YouTube/Instagram API integration
2. **Template System** - Reusable clip selection templates
3. **Analytics Dashboard** - Track clip performance
4. **Collaborative Features** - Share projects, review clips

---

## Additional Resources

### Documentation

- **FastAPI**: https://fastapi.tiangolo.com/
- **Pydantic**: https://docs.pydantic.dev/
- **YOLOv8**: https://docs.ultralytics.com/
- **FFmpeg**: https://ffmpeg.org/documentation.html
- **RunPod**: https://docs.runpod.io/
- **OpenRouter**: https://openrouter.ai/docs

### Related Files

- `README.md` - User-facing documentation
- `PROJECT_SUMMARY.md` - Project overview
- `QUICKSTART.md` - 5-minute setup guide
- `requirements.txt` - Python dependencies
- `.gitignore` - Excluded files

---

**Last Updated**: 2025-11-15
**Maintainer**: AI Assistant
**Version**: 1.0.0
