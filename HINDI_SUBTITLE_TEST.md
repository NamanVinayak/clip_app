# Hindi Subtitle System Test Guide

## Overview

The complete subtitle system has been integrated into the `newmaybe` branch and is ready for testing with actual Hindi audio. This document explains how to test the full pipeline.

## What's Been Built

### Complete Subtitle Pipeline

```
Hindi Video (16:9)
    ↓
[1] WhisperX Transcription → Word-level timestamps
    ↓
[2] Hindi → Roman Transliteration → "namaste" format
    ↓
[3] LLM Clip Selection → Viral clip identification
    ↓
[4] Face Tracking → Smart 9:16 crop
    ↓
[5] Subtitle Rendering → Frame-by-frame with effects
    ↓
[6] Video Compositing → Final 9:16 clip with subtitles
```

### New Modules

1. **`modules/transliterator.py`** - Hindi Devanagari → Roman script using ITRANS
2. **`modules/subtitle_renderer.py`** - Frame-by-frame subtitle rendering
3. **`subtitle_styles/effects/`** - Text effects (glow, outline, word highlighting)
4. **`subtitle_styles/config/styles.json`** - 3 professional subtitle styles

### Modified Modules

1. **`modules/transcriber.py`** - Now extracts word-level timestamps from WhisperX
2. **`modules/video_processor.py`** - Added subtitle compositing
3. **`config.py`** - Added subtitle configuration
4. **`main.py`** - Full subtitle pipeline integration (lines 206-293)

## Testing Requirements

### API Keys Required

Create a `.env` file with:

```env
# RunPod WhisperX (for Hindi transcription)
RUNPOD_API_KEY=your_runpod_key_here
RUNPOD_ENDPOINT=https://api.runpod.ai/v2/YOUR_ENDPOINT_ID

# OpenRouter LLM (for clip selection)
OPENROUTER_API_KEY=your_openrouter_key_here
LLM_MODEL=qwen/qwen-2.5-72b-instruct

# Subtitle Settings
enable_subtitles=true
subtitle_style=simple_caption
subtitle_fps=30
```

### Hindi Video Requirements

- **Audio**: Must contain actual Hindi speech
- **Format**: MP4, MOV, or AVI
- **Aspect Ratio**: 16:9 recommended (1920x1080, 1280x720, etc.)
- **Duration**: 5-30 minutes (optimal for processing)
- **Audio Quality**: Clear speech, minimal background noise

## Testing Methods

### Method 1: Web Interface (Easiest)

1. **Start the server:**
   ```bash
   python main.py
   ```

2. **Open browser:**
   ```
   http://localhost:8000
   ```

3. **Upload your Hindi video:**
   - Drag and drop or click to select
   - Watch real-time progress via WebSocket
   - Download generated clips with subtitles

4. **Check results:**
   - Clips will be in `outputs/job_YYYYMMDD_HHMMSS/`
   - Look for `clip_01.mp4`, `clip_02.mp4`, etc.
   - Each clip will have Hindi subtitles in Roman script

### Method 2: Python Test Script

1. **Run the test script:**
   ```bash
   python3 test_hindi_full_pipeline.py your_hindi_video.mp4
   ```

2. **The script will:**
   - Extract audio from video
   - Call WhisperX for transcription
   - Transliterate to Roman script
   - Select viral clips with LLM
   - Generate 9:16 clips with subtitles
   - Save detailed test results

3. **Output location:**
   ```
   outputs/job_YYYYMMDD_HHMMSS/
   ├── original_video.mp4
   ├── audio.wav
   ├── transcript.json
   ├── transcript_words.json
   ├── romanized_transcript.json
   ├── clip_01.mp4 (with subtitles!)
   ├── clip_02.mp4 (with subtitles!)
   ├── test_results.json
   └── processing.log
   ```

### Method 3: API Endpoint

```bash
curl -X POST http://localhost:8000/process \
  -F "video=@your_hindi_video.mp4"
```

## Expected Subtitle Output

### What You'll See

The subtitles will appear at the bottom of the vertical video with:

- **Roman script**: Hindi words written in English letters
  - Example: "namaste dosto, aaj main aapko batane ja raha hoon"
- **Word-by-word highlighting**: Current word changes size/color
- **Smooth animations**: Size pulses, glow effects, or color changes
- **Professional styling**: Based on selected style (simple_caption, glow_caption, karaoke_style)

### Subtitle Styles

1. **simple_caption** (default)
   - White text with black outline
   - Current word slightly larger
   - Clean and readable

2. **glow_caption**
   - Neon glow effect
   - Color shift on active word
   - Modern TikTok-style

3. **karaoke_style**
   - Color change from white to yellow
   - Word-by-word progression
   - Classic karaoke effect

Change style in `.env`:
```env
subtitle_style=glow_caption
```

## Sample Test Video Creation

If you don't have a Hindi video, you can:

1. **Record yourself speaking Hindi** (use phone camera)
2. **Find Creative Commons Hindi videos** on YouTube
3. **Use Hindi news clips** (check licensing)
4. **Generate with TTS** (though may be lower quality):
   ```python
   from gtts import gTTS
   tts = gTTS(text="नमस्ते दोस्तों", lang='hi')
   tts.save("hindi_audio.mp3")
   ```

## Troubleshooting

### No subtitles appearing

- Check `processing.log` in the output folder
- Verify `enable_subtitles=true` in `.env`
- Ensure WhisperX returned word-level timestamps

### Incorrect transliteration

- Check `romanized_transcript.json` in output folder
- The ITRANS scheme is used (standard for Hindi)
- Example: "नमस्ते" → "namaste"

### Subtitles not synced

- Check if WhisperX `align_output=true` is set
- Verify word timestamps in `transcript_words.json`
- Audio quality may affect timing accuracy

### Video processing fails

- Check FFmpeg is installed: `ffmpeg -version`
- Ensure input video is valid 16:9 format
- Check available disk space in `outputs/`

## Validation Checklist

After processing, verify:

- [ ] Output video is 1080x1920 (9:16 ratio)
- [ ] Subtitles appear at bottom of video
- [ ] Text is in Roman script (English letters)
- [ ] Words highlight one by one matching speech
- [ ] Subtitles stay within safe zone (not cut off)
- [ ] Multiple clips generated (if video is long enough)
- [ ] Each clip has different viral-worthy content

## Demo Video Structure

An ideal test video should have:

```
0:00-0:10 - Strong hook/introduction
0:10-1:00 - Main content with clear Hindi speech
1:00-1:30 - Emotional peak or key insight
1:30-2:00 - Call to action or conclusion
```

This allows the LLM to select diverse clips demonstrating different viral criteria.

## Cost Estimates

Processing a 10-minute Hindi video:

- **WhisperX (RunPod)**: ~$0.10-0.20
- **LLM Clip Selection (OpenRouter)**: ~$0.05-0.10
- **Total**: ~$0.15-0.30

Processing is GPU-accelerated on M4 Pro (face tracking) but transcription happens on RunPod servers.

## Expected Processing Time

For a 10-minute Hindi video:

| Step | Duration |
|------|----------|
| Audio extraction | 10 seconds |
| WhisperX transcription | 2-3 minutes |
| Transliteration | 5 seconds |
| LLM clip selection | 30 seconds |
| Face tracking (per clip) | 1-2 minutes |
| Subtitle rendering (per clip) | 2-3 minutes |
| **Total** | **8-12 minutes** |

## Next Steps

1. **Get a Hindi video** (see suggestions above)
2. **Configure API keys** in `.env`
3. **Run test** using Method 1, 2, or 3
4. **Check output** in `outputs/` folder
5. **Report results** - share generated clips!

## Support

If you encounter issues:

1. Check `processing.log` in the output folder
2. Verify all API keys are valid
3. Ensure video has Hindi audio (use `ffprobe` to check)
4. Test with a shorter video first (2-3 minutes)

---

**Ready to test?** Just provide a Hindi video and run the pipeline!
