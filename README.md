# Automated Shorts Generator

Transform long-form Hindi videos into viral-ready vertical clips automatically using AI.

## Features

- **Automated Transcription**: Hindi audio transcription using WhisperX on RunPod
- **Viral Clip Selection**: AI-powered clip selection using LLM (Qwen 32B via OpenRouter)
- **Smart Face Tracking**: YOLOv8 face detection optimized for M4 Pro
- **9:16 Cropping**: Automatic vertical format conversion with face-centered cropping
- **Real-time Progress**: WebSocket-based progress tracking
- **Simple Web UI**: Drag-and-drop interface, no coding required

## System Requirements

- **Hardware**: MacBook M4 Pro (or similar Apple Silicon Mac)
- **Memory**: 24GB RAM (base M4 Pro variant)
- **Storage**: 10GB+ free space for processing
- **Software**:
  - Python 3.10 or higher
  - FFmpeg (for video processing)

## Installation

### Step 1: Install FFmpeg

```bash
# Using Homebrew
brew install ffmpeg
```

### Step 2: Clone/Download the Project

You already have the project in `/Users/naman/Downloads/clip_app`

### Step 3: Create Python Virtual Environment

```bash
cd /Users/naman/Downloads/clip_app

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate
```

### Step 4: Install Python Dependencies

```bash
pip install -r requirements.txt
```

This will install:
- FastAPI (web framework)
- Ultralytics (YOLOv8)
- OpenCV (video processing)
- HTTPx (API calls)
- And other dependencies

### Step 5: Configure Environment Variables

```bash
# Copy example env file
cp .env.example .env

# Edit .env with your API keys
nano .env
```

Fill in your credentials:

```env
# RunPod WhisperX Configuration
RUNPOD_API_KEY=your_runpod_api_key_here
RUNPOD_ENDPOINT=your_whisperx_endpoint_url_here

# OpenRouter LLM Configuration
OPENROUTER_API_KEY=your_openrouter_api_key_here
LLM_MODEL=qwen/qwen-2.5-72b-instruct

# Application Settings (optional)
MAX_VIDEO_SIZE_MB=2000
MIN_CLIP_DURATION=15
MAX_CLIP_DURATION=60
TARGET_CLIPS=5
```

## Running the App

### Start the Server

```bash
# Make sure virtual environment is activated
source venv/bin/activate

# Run the app
python main.py
```

Or use FastAPI's dev mode:

```bash
fastapi dev main.py
```

You should see:

```
============================================================
🎬 Automated Shorts Generator
============================================================
📁 Upload folder: /Users/naman/Downloads/clip_app/uploads
📁 Output folder: /Users/naman/Downloads/clip_app/outputs
🔧 RunPod configured: True
🔧 OpenRouter configured: True
============================================================
🌐 Starting server at http://localhost:8000
📖 API docs at http://localhost:8000/docs
============================================================
```

### Access the Web Interface

Open your browser and go to:

```
http://localhost:8000
```

## How to Use

### Basic Workflow

1. **Upload Video**: Drag and drop a 16:9 Hindi video (MP4, MOV, AVI)
2. **Click "Generate Shorts"**: Processing starts automatically
3. **Monitor Progress**: Watch real-time updates for each step
4. **Download Clips**: Preview and download generated vertical clips

### Processing Steps

The app will show you progress through these steps:

1. ✅ **Upload Video** - Validates and saves your video
2. ✅ **Extract Audio** - FFmpeg extracts audio as WAV
3. ✅ **Transcribe** - WhisperX transcribes Hindi audio (2-5 minutes)
4. ✅ **Analyze** - LLM selects 3-6 viral-worthy clips
5. ✅ **Track Faces** - YOLOv8 detects and tracks faces
6. ✅ **Generate Clips** - Creates 1080×1920 vertical clips

## Testing Step by Step

Since you mentioned wanting to test each step individually:

### Test 1: Upload Video

```bash
# Use the API docs
open http://localhost:8000/docs

# Or use curl
curl -X POST "http://localhost:8000/process" \
  -F "video=@/path/to/your/test-video.mp4"
```

### Test 2: Extract Audio Only

Check the logs in `outputs/job_YYYYMMDD_HHMMSS/processing.log` to see:
- Video uploaded successfully
- Audio extracted to `audio.wav`

### Test 3: Transcription

After upload and extraction, check:
- `outputs/job_YYYYMMDD_HHMMSS/transcript.json` - Full transcript
- `outputs/job_YYYYMMDD_HHMMSS/transcript.srt` - Subtitle format

### Test 4: Clip Selection

Check `outputs/job_YYYYMMDD_HHMMSS/clip_suggestions.json` for:
- Suggested clips with timestamps
- Virality scores
- Reasons for selection

### Test 5: Face Tracking

Look for face detection confidence in logs:
```
Detected N face positions
```

### Test 6: Final Clips

Check `outputs/job_YYYYMMDD_HHMMSS/` for:
- `clip_01.mp4`, `clip_02.mp4`, etc.
- Each should be 1080×1920 (9:16 aspect ratio)

## File Structure After Processing

```
outputs/
└── job_20250114_153045/
    ├── original_video.mp4      # Your uploaded video
    ├── audio.wav                # Extracted audio
    ├── transcript.json          # WhisperX transcript
    ├── transcript.srt           # Subtitle file
    ├── clip_suggestions.json    # LLM-selected clips
    ├── clip_01.mp4             # Generated short #1
    ├── clip_02.mp4             # Generated short #2
    ├── clip_03.mp4             # Generated short #3
    ├── processing.log           # Detailed logs
    └── results.json            # Final summary
```

## Troubleshooting

### FFmpeg Not Found

```bash
# Install FFmpeg
brew install ffmpeg

# Verify installation
ffmpeg -version
```

### YOLOv8 Model Download

On first run, YOLOv8 will download ~6MB model file. This is normal and only happens once.

### RunPod Connection Issues

Check:
- Your API key is correct in `.env`
- RunPod endpoint URL is correct
- You have credits in your RunPod account

### OpenRouter API Issues

Check:
- API key is valid
- You have credits
- Model name is correct: `qwen/qwen-2.5-72b-instruct`

### Out of Memory

If processing fails with memory errors:
- Try shorter videos
- Reduce `TARGET_CLIPS` in `.env`
- Close other applications

### No Faces Detected

The app will still work! It uses center-crop as fallback if no faces are found.

## API Endpoints

### Main Endpoints

- `GET /` - Web interface
- `POST /process` - Upload and process video
- `GET /outputs/{job_id}/{filename}` - Download clips
- `GET /health` - Check configuration
- `WS /ws` - WebSocket for progress updates

### API Documentation

Interactive API docs available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Performance Notes

### M4 Pro Optimization

- YOLOv8 uses MPS (Metal Performance Shaders) for GPU acceleration
- Expect ~1-2 minutes per clip for face tracking + cropping
- Total processing time: 5-15 minutes for a 30-minute video

### Speed Tips

1. Use shorter source videos for testing
2. Reduce `TARGET_CLIPS` for faster processing
3. The app keeps intermediate files for debugging

## Customization

### Adjust Clip Criteria

Edit [config.py](config.py):

```python
MIN_CLIP_DURATION = 15  # Minimum clip length (seconds)
MAX_CLIP_DURATION = 60  # Maximum clip length (seconds)
TARGET_CLIPS = 5        # Number of clips to generate
```

### Change LLM Model

Edit `.env`:

```env
LLM_MODEL=qwen/qwen-2.5-72b-instruct
# Or try: anthropic/claude-3.5-sonnet
```

### Modify Viral Criteria

Edit [modules/clip_selector.py](modules/clip_selector.py) to adjust the prompt that selects clips.

## Architecture

```
┌─────────────┐
│  Web UI     │  ← You interact here
└──────┬──────┘
       │
┌──────▼──────┐
│  FastAPI    │  ← Main server
└──────┬──────┘
       │
       ├─► Video Processor (FFmpeg)
       ├─► Transcriber (WhisperX/RunPod)
       ├─► Clip Selector (LLM/OpenRouter)
       ├─► Face Tracker (YOLOv8)
       └─► Cropper (Smart 9:16)
```

## Technologies Used

- **FastAPI**: Modern Python web framework
- **YOLOv8**: State-of-the-art object detection
- **WhisperX**: Accurate speech-to-text with timestamps
- **FFmpeg**: Industry-standard video processing
- **OpenRouter**: LLM API gateway
- **Qwen 32B**: Advanced language model for clip analysis

## Credits

Built for personal use on M4 Pro MacBook.

Inspired by OpusClip's viral clip selection methodology.

## License

Personal use only. Not for commercial distribution.

## Support

For issues or questions:
1. Check `processing.log` in the job folder
2. Verify `.env` configuration
3. Check API credits (RunPod, OpenRouter)
4. Review the [Troubleshooting](#troubleshooting) section

---

**Happy clip generation!** 🎬
