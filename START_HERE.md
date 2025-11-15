# 🎬 START HERE - Automated Shorts Generator

Welcome! This is your complete automated shorts generator for converting Hindi videos into viral vertical clips.

## What This App Does

**INPUT**: Long-form 16:9 Hindi video
**OUTPUT**: 3-6 viral-ready 9:16 clips optimized for Instagram/YouTube Shorts

**The app automatically**:
1. Transcribes your Hindi audio (WhisperX)
2. Finds viral-worthy moments (AI-powered)
3. Tracks faces and centers them (YOLOv8)
4. Generates perfect vertical clips (FFmpeg)

## Quick Start (3 Steps)

### Step 1: Install FFmpeg
```bash
brew install ffmpeg
```

### Step 2: Run Setup Checker
```bash
cd /Users/naman/Downloads/clip_app
python3 check_setup.py
```

This checks everything and tells you what to fix.

### Step 3: Run the App
```bash
./start.sh
```

Then open: **http://localhost:8000**

## First Time Setup Details

If `check_setup.py` shows issues, follow these:

### Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
```

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Configure API Keys
```bash
cp .env.example .env
nano .env  # or use any text editor
```

Add your keys:
```env
RUNPOD_API_KEY=your_key_here
RUNPOD_ENDPOINT=https://api.runpod.ai/v2/your-endpoint/runsync
OPENROUTER_API_KEY=sk-or-v1-your_key_here
```

Save and exit.

### Verify Setup
```bash
python3 check_setup.py
```

Should show: "🎉 All checks passed!"

## Using the App

1. **Start Server**:
   ```bash
   ./start.sh
   ```

2. **Open Browser**: http://localhost:8000

3. **Upload Video**: Drag & drop your Hindi video

4. **Generate**: Click "Generate Shorts" and wait

5. **Download**: Preview and download your clips

## Documentation

- **[QUICKSTART.md](QUICKSTART.md)** - 5-minute setup guide
- **[README.md](README.md)** - Complete documentation
- **[PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)** - Technical overview

## Project Structure

```
clip_app/
├── START_HERE.md          ← You are here
├── QUICKSTART.md          ← Fast setup guide
├── README.md              ← Full documentation
├── PROJECT_SUMMARY.md     ← Technical details
│
├── start.sh               ← Run this to start the app
├── check_setup.py         ← Verify your setup
├── main.py                ← FastAPI server
├── config.py              ← Configuration
├── requirements.txt       ← Python packages
├── .env.example           ← Environment template
│
├── modules/               ← Core processing
│   ├── video_processor.py
│   ├── transcriber.py
│   ├── clip_selector.py
│   └── face_tracker.py
│
├── utils/                 ← Helper functions
│   └── helpers.py
│
├── static/                ← Web interface
│   ├── index.html
│   ├── style.css
│   └── script.js
│
└── outputs/               ← Your generated clips go here
    └── job_YYYYMMDD_HHMMSS/
        ├── clip_01.mp4
        ├── clip_02.mp4
        └── ...
```

## Need Help?

### Check if setup is correct:
```bash
python3 check_setup.py
```

### Common issues:

**"FFmpeg not found"**
```bash
brew install ffmpeg
```

**"No module named 'fastapi'"**
```bash
source venv/bin/activate
pip install -r requirements.txt
```

**"API key invalid"**
- Check `.env` file
- Verify keys on RunPod/OpenRouter dashboards

**"Port already in use"**
```bash
lsof -i :8000
kill -9 <PID>
```

## Testing

Start with a **short test video** (2-5 minutes) to verify everything works.

Expected processing time:
- 5 min video: ~3 minutes
- 15 min video: ~8 minutes
- 30 min video: ~15 minutes

## Output

Each clip is:
- ✅ 1080×1920 resolution (9:16)
- ✅ Face-centered and cropped
- ✅ 15-60 seconds long
- ✅ Ready to upload to Instagram/YouTube

Saved in: `outputs/job_YYYYMMDD_HHMMSS/clip_XX.mp4`

## What You Need Before Starting

1. ✅ **MacBook M4 Pro** (you have this)
2. ✅ **RunPod account** with WhisperX endpoint
3. ✅ **OpenRouter account** with API key
4. ⬜ **FFmpeg installed** (run: `brew install ffmpeg`)
5. ⬜ **Test video** (short Hindi video for testing)

## Your Workflow

```
┌─────────────────────────────────────────┐
│  1. Open http://localhost:8000          │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│  2. Upload Hindi video (16:9)           │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│  3. Click "Generate Shorts"             │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│  4. Watch progress (5-15 minutes)       │
│     • Upload ✓                          │
│     • Extract Audio ✓                   │
│     • Transcribe ✓                      │
│     • Analyze ✓                         │
│     • Track Faces ✓                     │
│     • Generate Clips ✓                  │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│  5. Download clips                      │
│     • Preview each clip                 │
│     • See virality score                │
│     • Read why it was selected          │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│  6. Upload to Instagram/YouTube         │
└─────────────────────────────────────────┘
```

## Ready to Start?

Run this now:

```bash
cd /Users/naman/Downloads/clip_app
python3 check_setup.py
```

If all checks pass:

```bash
./start.sh
```

Then open your browser to **http://localhost:8000** and upload your first video!

---

**Questions?** Check [README.md](README.md) for detailed docs or [QUICKSTART.md](QUICKSTART.md) for setup help.

**Happy clipping!** 🚀
