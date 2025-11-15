# Subtitle System Implementation Plan

**Date**: 2025-11-15
**Project**: Automated Shorts Generator - Subtitle System
**Target**: 9:16 vertical videos (Instagram Reels/YouTube Shorts)

---

## Executive Summary

This document outlines the implementation plan for adding a romanized Hindi subtitle system to the automated shorts generator. The system will:

1. **Extract word-level timestamps** from WhisperX (already supported with `align_output=True`)
2. **Transliterate Hindi text to Roman script** using AI4Bharat IndicXlit
3. **Generate intelligent subtitle chunks** (2-4 words per frame, max 37 chars/line)
4. **Burn subtitles into clips** with optimal positioning for 9:16 format
5. **Support customization** via configuration settings

---

## Current State Analysis

### Existing Capabilities

✅ **WhisperX Integration** (`modules/transcriber.py`)
- Already configured with `align_output=True` (line 110)
- Returns word-level timestamps (though currently unused)
- Saves both JSON and SRT formats

✅ **Video Processing Pipeline** (`modules/video_processor.py`)
- FFmpeg wrapper for video operations
- Clip generation with cropping and scaling

✅ **Face Tracking** (`modules/face_tracker.py`)
- Detects face positions in clips
- Important for subtitle placement (avoid covering faces)

### Current Gaps

❌ **Word-level timestamp extraction** - Currently only using segment-level
❌ **Transliteration** - Output is Devanagari, need Roman script
❌ **Subtitle chunking logic** - No system to group words into readable chunks
❌ **Subtitle rendering** - No FFmpeg integration for burning subtitles
❌ **Positioning system** - No safe zone calculations for 9:16 format

---

## Technical Approach

### Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                  Existing Pipeline                       │
│  Upload → Audio Extract → Transcribe → Select Clips     │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│              NEW: Subtitle Processing                    │
│                                                          │
│  1. Extract Word Timestamps (from WhisperX response)    │
│     └─> Parse "words" array from each segment           │
│                                                          │
│  2. Transliterate to Roman Script                       │
│     └─> Use ai4bharat-transliteration library           │
│     └─> Convert: "मैं जा रहा हूं" → "main ja raha hoon" │
│                                                          │
│  3. Create Subtitle Chunks                              │
│     └─> Group words (max 37 chars, 2-4 words)           │
│     └─> Calculate display duration                      │
│     └─> Generate ASS subtitle file                      │
│                                                          │
│  4. Calculate Subtitle Position                         │
│     └─> Get face position from FaceTracker              │
│     └─> Apply safe zone rules (bottom 30%)              │
│     └─> Position at Y=1200-1400px                       │
│                                                          │
│  5. Burn Subtitles into Video                           │
│     └─> FFmpeg with ASS filter                          │
│     └─> Generate final clip with subtitles              │
└─────────────────────────────────────────────────────────┘
```

### Data Flow

```
WhisperX Response (JSON)
  │
  ├─> segments: [
  │     {
  │       "start": 0.427,
  │       "end": 7.751,
  │       "text": "मैं अभी जा रहा हूं",
  │       "words": [                      ← WORD-LEVEL TIMESTAMPS
  │         {"text": "मैं", "start": 0.427, "end": 0.850},
  │         {"text": "अभी", "start": 0.851, "end": 1.200},
  │         {"text": "जा", "start": 1.201, "end": 1.450},
  │         {"text": "रहा", "start": 1.451, "end": 1.750},
  │         {"text": "हूं", "start": 1.751, "end": 2.100}
  │       ]
  │     }
  │   ]
  ↓
Transliterate each word
  │
  ├─> "मैं" → "main"
  ├─> "अभी" → "abhi"
  ├─> "जा" → "ja"
  ├─> "रहा" → "raha"
  └─> "हूं" → "hoon"
  ↓
Create subtitle chunks (group words)
  │
  ├─> Chunk 1: "main abhi" (0.427 - 1.200)
  └─> Chunk 2: "ja raha hoon" (1.201 - 2.100)
  ↓
Generate ASS subtitle file
  │
  └─> clip_01_subtitles.ass
      [Events]
      Dialogue: 0,0:00:00.42,0:00:01.20,Default,,0,0,0,,main abhi
      Dialogue: 0,0:00:01.20,0:00:02.10,Default,,0,0,0,,ja raha hoon
  ↓
FFmpeg burn subtitles
  │
  └─> ffmpeg -i clip_01.mp4 -vf "ass=clip_01_subtitles.ass" clip_01_final.mp4
```

---

## Implementation Plan

### Phase 1: Update Transcription Module (High Priority)

**File**: `modules/transcriber.py`

**Changes**:
1. **Update `_parse_whisperx_response()` method** (line 159)
   - Extract `words` array from each segment
   - Preserve word-level timestamps
   - Return enhanced structure:
     ```python
     {
       'text': 'full transcript',
       'segments': [
         {
           'start': 0.427,
           'end': 7.751,
           'text': 'segment text',
           'words': [  # NEW!
             {'text': 'word', 'start': 0.427, 'end': 0.850}
           ]
         }
       ],
       'language': 'hi'
     }
     ```

2. **Add new method `save_word_timestamps()`**
   - Save word-level data as JSON for subtitle processing
   - Format: `transcript_words.json`

**Estimated Effort**: 1-2 hours

---

### Phase 2: Create Transliteration Module (High Priority)

**New File**: `modules/transliterator.py`

**Purpose**: Convert Hindi Devanagari to Roman script using AI4Bharat

**Dependencies**:
```bash
pip install ai4bharat-transliteration
```

**Class Structure**:
```python
from ai4bharat.transliteration import XlitEngine
from pathlib import Path
from typing import Dict, List

class HindiTransliterator:
    """Transliterate Hindi text to Roman script"""

    def __init__(self, job_folder: Path):
        self.job_folder = job_folder
        self.engine = XlitEngine(beam_width=10, rescore=True)
        self.logger = setup_logger("Transliterator", job_folder / "processing.log")

    def transliterate_transcript(self, transcript_data: Dict) -> Dict:
        """
        Transliterate all words in transcript from Devanagari to Roman

        Args:
            transcript_data: Dict with segments and words

        Returns:
            Dict with romanized text
        """
        romanized_data = transcript_data.copy()

        for segment in romanized_data['segments']:
            # Transliterate segment text
            segment['text_roman'] = self._transliterate_text(segment['text'])

            # Transliterate each word
            if 'words' in segment:
                for word in segment['words']:
                    word['text_roman'] = self._transliterate_text(word['text'])

        # Save romanized transcript
        output_path = self.job_folder / "transcript_romanized.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(romanized_data, f, ensure_ascii=False, indent=2)

        self.logger.info(f"Romanized transcript saved to {output_path}")
        return romanized_data

    def _transliterate_text(self, text: str) -> str:
        """Transliterate single text using IndicXlit"""
        # IndicXlit expects text in Devanagari
        result = self.engine.translit_sentence(text, lang_code='hi')
        return result
```

**Alternative Option** (if AI4Bharat is too heavy):
Use `indic-transliteration` library (lighter, rule-based):
```python
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate

def _transliterate_text(self, text: str) -> str:
    return transliterate(text, sanscript.DEVANAGARI, sanscript.ITRANS)
```

**Estimated Effort**: 2-3 hours

---

### Phase 3: Create Subtitle Generator Module (Critical)

**New File**: `modules/subtitle_generator.py`

**Purpose**: Generate optimized subtitle chunks and create ASS files

**Key Features**:
- Intelligent word grouping (2-4 words per chunk)
- Character limit enforcement (max 37 chars/line)
- Line breaking logic
- ASS subtitle file generation
- Positioning calculation

**Class Structure**:
```python
from pathlib import Path
from typing import Dict, List, Tuple
import re

class SubtitleGenerator:
    """Generate subtitles for vertical video clips"""

    # Configuration (from settings)
    MAX_CHARS_PER_LINE = 37  # BBC standard for vertical video
    MAX_LINES = 2
    MIN_DURATION = 0.3  # Minimum subtitle display time (seconds)
    MAX_WORDS_PER_CHUNK = 4

    def __init__(self, job_folder: Path, video_width: int = 1080, video_height: int = 1920):
        self.job_folder = job_folder
        self.video_width = video_width
        self.video_height = video_height
        self.logger = setup_logger("SubtitleGen", job_folder / "processing.log")

    def generate_subtitles(
        self,
        romanized_transcript: Dict,
        clip_start: float,
        clip_end: float,
        face_position: Dict = None
    ) -> Path:
        """
        Generate subtitle file for a specific clip

        Args:
            romanized_transcript: Full transcript with romanized words
            clip_start: Clip start time in seconds
            clip_end: Clip end time in seconds
            face_position: Dict with face position {'y_center': 500}

        Returns:
            Path to generated .ass subtitle file
        """
        # Extract words for this clip's timeframe
        clip_words = self._extract_clip_words(
            romanized_transcript,
            clip_start,
            clip_end
        )

        # Create subtitle chunks
        chunks = self._create_chunks(clip_words)

        # Calculate subtitle position
        subtitle_y = self._calculate_subtitle_position(face_position)

        # Generate ASS file
        ass_path = self.job_folder / f"clip_{clip_start:.0f}_{clip_end:.0f}_subs.ass"
        self._create_ass_file(chunks, ass_path, subtitle_y)

        self.logger.info(f"Generated {len(chunks)} subtitle chunks for clip")
        return ass_path

    def _extract_clip_words(
        self,
        transcript: Dict,
        clip_start: float,
        clip_end: float
    ) -> List[Dict]:
        """Extract words that fall within clip timeframe"""
        clip_words = []

        for segment in transcript['segments']:
            if 'words' not in segment:
                continue

            for word in segment['words']:
                word_start = word['start']
                word_end = word['end']

                # Check if word overlaps with clip timeframe
                if word_end > clip_start and word_start < clip_end:
                    # Adjust timestamps relative to clip start
                    clip_words.append({
                        'text': word.get('text_roman', word['text']),
                        'start': max(0, word_start - clip_start),
                        'end': min(clip_end - clip_start, word_end - clip_start)
                    })

        return clip_words

    def _create_chunks(self, words: List[Dict]) -> List[Dict]:
        """
        Group words into subtitle chunks

        Rules:
        - Max 37 characters per line
        - Max 2 lines
        - Max 4 words per chunk (for readability)
        - Minimum duration 0.3 seconds
        """
        chunks = []
        current_chunk = []
        current_text = ""

        for i, word in enumerate(words):
            # Calculate if adding this word exceeds limits
            test_text = current_text + (" " if current_text else "") + word['text']

            # Check if we should start new chunk
            should_break = (
                len(test_text) > self.MAX_CHARS_PER_LINE or
                len(current_chunk) >= self.MAX_WORDS_PER_CHUNK
            )

            if should_break and current_chunk:
                # Finalize current chunk
                chunks.append({
                    'text': current_text,
                    'start': current_chunk[0]['start'],
                    'end': current_chunk[-1]['end']
                })
                current_chunk = []
                current_text = ""

            # Add word to current chunk
            current_chunk.append(word)
            current_text = test_text

        # Add final chunk
        if current_chunk:
            chunks.append({
                'text': current_text,
                'start': current_chunk[0]['start'],
                'end': current_chunk[-1]['end']
            })

        # Enforce minimum duration
        for chunk in chunks:
            if chunk['end'] - chunk['start'] < self.MIN_DURATION:
                chunk['end'] = chunk['start'] + self.MIN_DURATION

        return chunks

    def _calculate_subtitle_position(self, face_position: Dict = None) -> int:
        """
        Calculate Y position for subtitles in 9:16 format

        Safe zones for Instagram Reels/YouTube Shorts:
        - Bottom ~30% is covered by UI (buttons, captions)
        - Recommended Y position: 1200-1400px
        - Avoid covering faces (use face tracker data)
        """
        # Default position (bottom third, above UI)
        default_y = 1350  # px from top

        if face_position and 'y_center' in face_position:
            face_y = face_position['y_center']

            # If face is in bottom half, place subtitles higher
            if face_y > self.video_height / 2:
                # Place subtitles above face
                subtitle_y = max(800, face_y - 300)
            else:
                # Face is in top half, use default bottom position
                subtitle_y = default_y
        else:
            subtitle_y = default_y

        return subtitle_y

    def _create_ass_file(self, chunks: List[Dict], output_path: Path, subtitle_y: int):
        """
        Create ASS subtitle file

        ASS format allows precise styling and positioning
        """
        # ASS header with styling
        ass_content = f"""[Script Info]
Title: Auto-generated Subtitles
ScriptType: v4.00+
PlayResX: {self.video_width}
PlayResY: {self.video_height}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,64,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,2,2,30,30,{self.video_height - subtitle_y},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

        # Add subtitle events
        for chunk in chunks:
            start_time = self._format_ass_time(chunk['start'])
            end_time = self._format_ass_time(chunk['end'])
            text = chunk['text'].strip()

            ass_content += f"Dialogue: 0,{start_time},{end_time},Default,,0,0,0,,{text}\n"

        # Write to file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(ass_content)

        self.logger.info(f"ASS file created: {output_path}")

    @staticmethod
    def _format_ass_time(seconds: float) -> str:
        """Format seconds as ASS timestamp (H:MM:SS.CC)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        centis = int((seconds % 1) * 100)
        return f"{hours}:{minutes:02d}:{secs:02d}.{centis:02d}"
```

**Estimated Effort**: 4-6 hours

---

### Phase 4: Update Video Processor for Subtitle Burning

**File**: `modules/video_processor.py`

**New Method**:
```python
def burn_subtitles(
    self,
    video_path: Path,
    subtitle_path: Path,
    output_path: Path
) -> Path:
    """
    Burn ASS subtitles into video using FFmpeg

    Args:
        video_path: Input video file
        subtitle_path: ASS subtitle file
        output_path: Output video file

    Returns:
        Path to output video
    """
    self.logger.info(f"Burning subtitles into {video_path.name}")

    # FFmpeg command with ASS filter
    cmd = [
        'ffmpeg',
        '-i', str(video_path),
        '-vf', f"ass='{subtitle_path}'",
        '-c:v', 'libx264',
        '-preset', 'medium',
        '-crf', '23',
        '-c:a', 'copy',  # Copy audio without re-encoding
        '-y',
        str(output_path)
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        self.logger.info(f"Subtitles burned successfully: {output_path}")
        return output_path
    except subprocess.CalledProcessError as e:
        self.logger.error(f"FFmpeg subtitle burning failed: {e.stderr}")
        raise
```

**Estimated Effort**: 1-2 hours

---

### Phase 5: Update Configuration

**File**: `config.py`

**New Settings**:
```python
class Settings(BaseSettings):
    # ... existing settings ...

    # Subtitle settings
    enable_subtitles: bool = True
    subtitle_max_chars_per_line: int = 37
    subtitle_max_lines: int = 2
    subtitle_font_size: int = 64
    subtitle_position_y: int = 1350  # Default Y position
    subtitle_transliteration: bool = True  # Enable romanization
```

**File**: `.env.example`
```env
# Subtitle Configuration
ENABLE_SUBTITLES=true
SUBTITLE_MAX_CHARS_PER_LINE=37
SUBTITLE_FONT_SIZE=64
SUBTITLE_TRANSLITERATION=true
```

**Estimated Effort**: 30 minutes

---

### Phase 6: Update Main Processing Pipeline

**File**: `main.py`

**Update `/process` endpoint** (add subtitle processing step):

```python
# After clip generation loop
if settings.enable_subtitles:
    await send_progress("subtitles", "active", "Adding subtitles to clips...", 90)

    # Initialize modules
    transliterator = HindiTransliterator(job_folder)
    subtitle_gen = SubtitleGenerator(job_folder)

    # Transliterate transcript
    romanized_transcript = transliterator.transliterate_transcript(transcript_data)

    # Process each clip
    for i, (clip_info, clip_path) in enumerate(zip(clip_suggestions, generated_clips)):
        # Get face position for this clip
        face_position = clip_info.get('face_tracking', {})

        # Generate subtitle file
        subtitle_path = subtitle_gen.generate_subtitles(
            romanized_transcript,
            clip_info['start_seconds'],
            clip_info['end_seconds'],
            face_position
        )

        # Burn subtitles into video
        final_clip_path = job_folder / f"clip_{i+1:02d}_final.mp4"
        video_processor.burn_subtitles(clip_path, subtitle_path, final_clip_path)

        # Update clip path to final version
        generated_clips[i] = final_clip_path

    await send_progress("subtitles", "complete", "Subtitles added successfully", 95)
```

**Estimated Effort**: 2-3 hours

---

### Phase 7: Update Face Tracker Integration

**File**: `modules/face_tracker.py`

**Modification**: Return face position data for subtitle placement

```python
def track_faces_in_clip(
    self,
    video_path: Path,
    start_time: str,
    end_time: str
) -> Dict:
    """
    Track faces and return position data

    Returns:
        Dict with crop params AND face position:
        {
            'crop_x': 400,
            'crop_y': 0,
            'crop_width': 1080,
            'crop_height': 1920,
            'face_position': {  # NEW!
                'y_center': 500,
                'confidence': 0.8
            }
        }
    """
    # ... existing tracking logic ...

    return {
        'crop_x': crop_x,
        'crop_y': crop_y,
        'crop_width': crop_width,
        'crop_height': crop_height,
        'face_position': {
            'y_center': median_y if face_positions else None,
            'confidence': confidence
        }
    }
```

**Estimated Effort**: 1 hour

---

## Testing Strategy

### Unit Tests

**Test 1: Transliteration**
```python
def test_transliteration():
    """Test Hindi to Roman conversion"""
    translator = HindiTransliterator(Path("/tmp/test"))

    test_cases = [
        ("नमस्ते", "namaste"),
        ("मैं जा रहा हूं", "main ja raha hoon"),
        ("यह बहुत अच्छा है", "yah bahut accha hai")
    ]

    for hindi, expected in test_cases:
        result = translator._transliterate_text(hindi)
        assert result.lower() == expected.lower()
```

**Test 2: Subtitle Chunking**
```python
def test_subtitle_chunking():
    """Test word grouping logic"""
    sub_gen = SubtitleGenerator(Path("/tmp/test"))

    words = [
        {'text': 'hello', 'start': 0.0, 'end': 0.5},
        {'text': 'this', 'start': 0.5, 'end': 0.8},
        {'text': 'is', 'start': 0.8, 'end': 1.0},
        {'text': 'a', 'start': 1.0, 'end': 1.1},
        {'text': 'test', 'start': 1.1, 'end': 1.5}
    ]

    chunks = sub_gen._create_chunks(words)

    # Should create 2 chunks (max 4 words per chunk)
    assert len(chunks) == 2
    assert chunks[0]['text'] == "hello this is a"
    assert chunks[1]['text'] == "test"
```

**Test 3: ASS File Generation**
```python
def test_ass_file_generation():
    """Test ASS subtitle file creation"""
    sub_gen = SubtitleGenerator(Path("/tmp/test"))

    chunks = [
        {'text': 'hello world', 'start': 0.0, 'end': 1.0},
        {'text': 'testing subtitles', 'start': 1.0, 'end': 2.5}
    ]

    ass_path = Path("/tmp/test/test.ass")
    sub_gen._create_ass_file(chunks, ass_path, 1350)

    assert ass_path.exists()
    content = ass_path.read_text()
    assert "hello world" in content
    assert "testing subtitles" in content
```

### Integration Tests

**Test 4: End-to-End Subtitle Pipeline**
```python
async def test_full_subtitle_pipeline():
    """Test complete subtitle processing"""
    # Setup
    job_folder = Path("/tmp/test_job")
    job_folder.mkdir(exist_ok=True)

    # Mock transcript with word-level data
    transcript = {
        'segments': [
            {
                'start': 0.0,
                'end': 5.0,
                'text': 'नमस्ते दोस्तों',
                'words': [
                    {'text': 'नमस्ते', 'start': 0.0, 'end': 1.0},
                    {'text': 'दोस्तों', 'start': 1.0, 'end': 2.5}
                ]
            }
        ]
    }

    # Process
    transliterator = HindiTransliterator(job_folder)
    romanized = transliterator.transliterate_transcript(transcript)

    sub_gen = SubtitleGenerator(job_folder)
    ass_path = sub_gen.generate_subtitles(romanized, 0.0, 5.0)

    # Verify
    assert ass_path.exists()
    assert romanized['segments'][0]['words'][0]['text_roman'] == 'namaste'
```

### Manual Testing Checklist

- [ ] Upload test Hindi video
- [ ] Verify word-level timestamps in `transcript_words.json`
- [ ] Check transliteration accuracy in `transcript_romanized.json`
- [ ] Review subtitle chunks (max 37 chars, readable grouping)
- [ ] Verify subtitle position (not covering face, above UI)
- [ ] Test subtitle timing (smooth transitions, no flicker)
- [ ] Validate ASS file format
- [ ] Confirm FFmpeg subtitle burning works
- [ ] Test with different clip durations (15s, 30s, 60s)
- [ ] Verify performance (processing time acceptable)

---

## Dependencies

### New Python Packages

```txt
# Add to requirements.txt

# Transliteration (choose one)
ai4bharat-transliteration>=1.0.1  # Recommended: ML-based, more accurate

# OR (lighter alternative)
indic-transliteration>=2.3.0  # Rule-based, faster but less natural
```

### System Dependencies

```bash
# Already installed
ffmpeg  # For subtitle burning (ass filter)
```

---

## Configuration Examples

### Enable Subtitles with Transliteration

```env
# .env
ENABLE_SUBTITLES=true
SUBTITLE_TRANSLITERATION=true
SUBTITLE_FONT_SIZE=64
SUBTITLE_POSITION_Y=1350
```

### Disable Subtitles

```env
ENABLE_SUBTITLES=false
```

### Custom Subtitle Styling

Modify `SubtitleGenerator._create_ass_file()` for:
- Font family (Arial, Helvetica, Impact, etc.)
- Font size (48-80px recommended for mobile)
- Colors (use `&HAABBGGRR` format)
- Outline/shadow effects
- Animation effects (karaoke style)

---

## Performance Considerations

### Expected Processing Time

| Step | Duration (per clip) | Notes |
|------|---------------------|-------|
| Transliteration | 0.1-0.2s | Fast, local processing |
| Chunk generation | 0.05s | Fast, algorithmic |
| ASS file creation | 0.02s | Fast, text generation |
| Subtitle burning | 5-15s | FFmpeg encoding |

**Total overhead per clip**: ~5-15 seconds (mostly FFmpeg)

### Optimization Opportunities

1. **Parallel subtitle burning**: Process multiple clips simultaneously
2. **Cache transliteration**: Reuse common word translations
3. **GPU encoding**: Use FFmpeg hardware acceleration (VideoToolbox on macOS)

```python
# Example: GPU-accelerated subtitle burning
cmd = [
    'ffmpeg',
    '-i', str(video_path),
    '-vf', f"ass='{subtitle_path}'",
    '-c:v', 'h264_videotoolbox',  # Apple Silicon GPU
    '-b:v', '5M',
    '-c:a', 'copy',
    '-y',
    str(output_path)
]
```

---

## Alternative Approaches Considered

### Approach 1: LLM-based Transliteration (Rejected)

**Pros**:
- Flexible, can handle context
- Natural output

**Cons**:
- **Expensive**: $0.01-0.05 per clip (OpenRouter API)
- **Slow**: 1-3 seconds per API call
- **Unreliable**: May fail or timeout
- **Overkill**: Simple transliteration doesn't need AI

**Decision**: Use dedicated transliteration library instead

---

### Approach 2: Direct Romanization from Whisper (Investigated)

**Question**: Can WhisperX directly output romanized Hindi?

**Findings**:
- WhisperX uses OpenAI Whisper model
- Whisper `task='transcribe'` outputs in source script (Devanagari)
- Whisper `task='translate'` translates to English (not transliteration)
- No built-in romanization option

**Decision**: Post-process with transliteration library

---

### Approach 3: SRT vs ASS Format

**SRT Pros**:
- Simpler format
- Widely supported

**SRT Cons**:
- Limited styling options
- No precise positioning control
- No font/color customization

**ASS Pros**:
- Precise positioning (critical for 9:16 format)
- Full styling control (fonts, colors, outlines)
- Animation support (future: karaoke effect)
- Professional quality

**Decision**: Use ASS format for quality and control

---

## File Structure After Implementation

```
clip_app/
├── modules/
│   ├── video_processor.py       [UPDATED] +burn_subtitles()
│   ├── transcriber.py            [UPDATED] +word timestamps
│   ├── face_tracker.py           [UPDATED] +face position data
│   ├── transliterator.py         [NEW]
│   └── subtitle_generator.py     [NEW]
│
├── config.py                     [UPDATED] +subtitle settings
├── main.py                       [UPDATED] +subtitle pipeline
├── requirements.txt              [UPDATED] +transliteration lib
│
└── outputs/
    └── job_YYYYMMDD_HHMMSS/
        ├── original_video.mp4
        ├── audio.wav
        ├── transcript.json
        ├── transcript_words.json       [NEW] Word-level timestamps
        ├── transcript_romanized.json   [NEW] Transliterated text
        ├── transcript.srt
        ├── clip_01.mp4                 (without subtitles)
        ├── clip_01_subs.ass            [NEW] Subtitle file
        ├── clip_01_final.mp4           [NEW] With burned subtitles
        ├── clip_02_subs.ass            [NEW]
        ├── clip_02_final.mp4           [NEW]
        └── results.json
```

---

## Implementation Timeline

### Week 1: Core Functionality
- **Day 1-2**: Update `transcriber.py` for word-level timestamps
- **Day 2-3**: Create `transliterator.py` module
- **Day 3-5**: Build `subtitle_generator.py` with chunking logic

### Week 2: Integration & Polish
- **Day 1-2**: Update `video_processor.py` for subtitle burning
- **Day 2-3**: Integrate into `main.py` pipeline
- **Day 3-4**: Testing and bug fixes
- **Day 5**: Documentation and configuration

**Total Estimated Time**: 10-12 days (with testing)

---

## Risk Assessment

### High Risk
- **WhisperX response structure** - May vary by RunPod implementation
  - *Mitigation*: Test with actual RunPod response, add fallback parsing

### Medium Risk
- **Transliteration quality** - May not match user expectations
  - *Mitigation*: Support multiple libraries, allow manual correction

- **Subtitle positioning** - May cover important visual elements
  - *Mitigation*: Use face tracking data, make position configurable

### Low Risk
- **FFmpeg subtitle burning** - Well-documented feature
- **Performance impact** - Acceptable overhead (5-15s per clip)

---

## Success Metrics

### Functional Requirements
✅ Subtitles appear on all generated clips
✅ Romanized Hindi text is readable and accurate
✅ Subtitles don't cover faces or important UI elements
✅ Timing is synchronized with audio
✅ Text chunks are properly sized (max 37 chars)

### Performance Requirements
✅ Subtitle processing adds <20 seconds per clip
✅ No degradation in video quality
✅ System remains stable with long videos (30+ min)

### Quality Requirements
✅ Transliteration accuracy >90% (manual review)
✅ Subtitle readability on mobile devices
✅ Professional appearance (fonts, positioning, styling)

---

## Future Enhancements

### Phase 2 Features (Post-Launch)
1. **Karaoke-style highlighting** - Highlight current word
2. **Custom fonts** - User-selectable fonts
3. **Color themes** - Match brand colors
4. **Emoji support** - Auto-insert relevant emojis
5. **Multi-language support** - Support other Indic languages

### Advanced Features
1. **Dynamic positioning** - Adapt to scene content
2. **Subtitle effects** - Fade in/out, animations
3. **Manual editing** - Web UI for subtitle correction
4. **A/B testing** - Different subtitle styles for performance testing

---

## References

### Documentation
- **WhisperX**: https://github.com/m-bain/whisperX
- **AI4Bharat Transliteration**: https://github.com/AI4Bharat/IndicXlit
- **FFmpeg ASS Filter**: https://ffmpeg.org/ffmpeg-filters.html#ass
- **ASS Format Spec**: https://fileformats.fandom.com/wiki/SubStation_Alpha

### Research
- **BBC Subtitle Guidelines**: https://www.bbc.co.uk/accessibility/forproducts/guides/subtitles/
- **Vertical Video Best Practices**: See CLAUDE.md references
- **WhisperX Paper**: https://arxiv.org/abs/2303.00747

---

## Questions for Clarification

Before implementation, please confirm:

1. **Transliteration Library**: AI4Bharat (ML-based, 50MB) or indic-transliteration (rule-based, <1MB)?
   - Recommended: AI4Bharat for better quality

2. **Subtitle Style**: Simple white text or branded design?
   - Default: White text with black outline (high contrast)

3. **Toggle Option**: Should users be able to disable subtitles?
   - Recommended: Yes, via `ENABLE_SUBTITLES` setting

4. **Performance Priority**: Optimize for speed or quality?
   - Recommended: Balance (current approach)

---

**End of Plan**

**Next Steps**:
1. Review and approve plan
2. Install dependencies (`ai4bharat-transliteration`)
3. Begin Phase 1 implementation (update transcriber.py)
4. Test with sample RunPod response to verify word-level timestamps

**Questions?** Please review and provide feedback before implementation begins.
