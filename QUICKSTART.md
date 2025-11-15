# Quick Start Guide

Get your Shorts Generator running in 5 minutes!

## Prerequisites

1. **Install FFmpeg**:
   ```bash
   brew install ffmpeg
   ```

2. **Have your API keys ready**:
   - RunPod API key and WhisperX endpoint URL
   - OpenRouter API key

## Setup (First Time Only)

### Option 1: Use the Start Script (Easiest)

```bash
cd /Users/naman/Downloads/clip_app
./start.sh
```

The script will:
- Create virtual environment
- Install dependencies
- Check for FFmpeg
- Create .env file (you'll need to edit it with your keys)

### Option 2: Manual Setup

```bash
cd /Users/naman/Downloads/clip_app

# 1. Create virtual environment
python3 -m venv venv

# 2. Activate it
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
nano .env  # Edit with your API keys
```

## Configure Your API Keys

Edit the `.env` file:

```env
RUNPOD_API_KEY=your_actual_runpod_key_here
RUNPOD_ENDPOINT=https://api.runpod.ai/v2/your-endpoint-id/runsync
OPENROUTER_API_KEY=sk-or-v1-your_actual_openrouter_key_here
```

Save and close the file.

## Run the App

```bash
# Make sure you're in the project directory
cd /Users/naman/Downloads/clip_app

# Activate virtual environment (if not already active)
source venv/bin/activate

# Start the server
python main.py
```

You should see:

```
============================================================
🎬 Automated Shorts Generator
============================================================
🌐 Starting server at http://localhost:8000
============================================================
```

## Use the App

1. **Open your browser**: Go to `http://localhost:8000`

2. **Upload a video**: Drag and drop a Hindi video (16:9 format)

3. **Click "Generate Shorts"**: Processing starts automatically

4. **Watch the progress**:
   - Upload Video ✓
   - Extract Audio ✓
   - Transcribe ✓
   - Analyze for Viral Clips ✓
   - Track Faces ✓
   - Generate Clips ✓

5. **Download your clips**: Preview and download each generated clip

## Expected Processing Time

For a 30-minute 4K video on M4 Pro:
- Upload: 10-30 seconds
- Extract Audio: 30 seconds
- Transcribe: 2-5 minutes (RunPod)
- Analyze: 30-60 seconds (LLM)
- Face Tracking: 1-2 minutes per clip
- Generate Clips: 30 seconds per clip

**Total: ~10-15 minutes** for 5 clips

## First Test

Use a **short test video** (2-5 minutes) for your first run to verify everything works!

## Outputs

All generated clips are saved in:
```
outputs/job_YYYYMMDD_HHMMSS/
├── clip_01.mp4  ← Your vertical shorts
├── clip_02.mp4
├── clip_03.mp4
└── ...
```

Each clip is:
- 1080×1920 resolution (9:16 aspect ratio)
- Face-centered and cropped
- Ready to upload to Instagram/YouTube

## Troubleshooting

### "FFmpeg not found"
```bash
brew install ffmpeg
```

### "ModuleNotFoundError"
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### "API key invalid"
- Double-check your `.env` file
- Ensure no spaces around the `=` sign
- Verify keys on RunPod and OpenRouter dashboards

### App won't start
```bash
# Check if port 8000 is in use
lsof -i :8000

# Kill existing process if needed
kill -9 <PID>
```

## Next Steps

Once your first video processes successfully:

1. **Experiment with settings** in `.env`:
   - `TARGET_CLIPS=3` for faster processing
   - `MIN_CLIP_DURATION=20` for longer clips

2. **Check the logs** in `outputs/job_*/processing.log`

3. **Review clip suggestions** in `outputs/job_*/clip_suggestions.json`

## Stop the Server

Press `Ctrl+C` in the terminal where the server is running.

## Need Help?

1. Check [README.md](README.md) for detailed documentation
2. Look at `outputs/job_*/processing.log` for error details
3. Verify API credits on RunPod and OpenRouter

---

**That's it! You're ready to generate viral shorts!** 🎬
