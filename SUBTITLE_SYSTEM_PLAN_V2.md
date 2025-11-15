# Modern Subtitle System Implementation Plan V2
**Updated**: 2025-11-15
**Based on**: VinVideo Project Architecture

---

## Overview

After analyzing the reference project, we're implementing a **programmatic subtitle rendering system** with word-by-word effects, similar to TikTok/Reels style subtitles.

### Key Differences from V1 Plan

| Traditional Approach (V1) | Modern Approach (V2) |
|--------------------------|----------------------|
| ASS subtitle files | JSON style definitions |
| FFmpeg burn-in | Frame-by-frame rendering |
| Static text | Word-by-word animations |
| Single style | Multiple professional styles |
| Segment-level timing | Word-level precise timing |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│         EXISTING: Phase 1 & 2 (COMPLETED ✓)             │
│  - Word-level timestamps from WhisperX                  │
│  - Hindi → Roman transliteration                        │
│  - transcript_words.json + transcript_romanized.json    │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│         NEW: Programmatic Subtitle Rendering            │
│                                                          │
│  1. Style System (JSON configurations)                  │
│     └─> subtitle_styles/config/styles.json              │
│     └─> Styles: simple, glow, karaoke, hormozi, etc.    │
│                                                          │
│  2. Subtitle Engine                                     │
│     └─> Load word timestamps                            │
│     └─> Apply style configuration                       │
│     └─> Generate word-by-word effects                   │
│                                                          │
│  3. Frame Renderer                                      │
│     └─> PIL/OpenCV: Draw text on transparent frames     │
│     └─> Apply effects: outline, glow, background        │
│     └─> Handle word highlighting/scaling                │
│                                                          │
│  4. Video Compositor                                    │
│     └─> FFmpeg overlay filter                           │
│     └─> Composite subtitle frames onto video            │
│     └─> Output final clip with animated subtitles       │
└─────────────────────────────────────────────────────────┘
```

---

## Learned from Reference Project

### 1. **JSON Style System**
They define 9 professional styles in `subtitle_styles_v3.json`:
- **simple_caption**: Clean outline text (educational)
- **background_caption**: Dark background box (news-style)
- **karaoke_style**: Y2K word color changes
- **glow_caption**: Neon glow for gaming
- **hormozi_caption**: Motivational purple highlights
- **deep_diver**: Gray background, black active word
- **popling_caption**: Purple underline highlight
- **green_goblin**: Green glow + auto-scaling
- **sgone_caption**: 2-word max display

### 2. **Word-by-Word Effects**
- **Time-based activation**: Words highlight between start/end timestamps
- **Per-word styling**: Each word can have different color/size/effect
- **Animations**: Scale changes, color transitions, glow pulses
- **Safe zones**: Auto-scaling to prevent text overflow

### 3. **Rendering Pipeline**
```python
# Pseudocode from their system
style = StyleLoader.load_style_from_json("simple_caption")
subtitle_layer = StyledSubtitleLayer(
    words=word_timestamps,
    style=style,
    resolution=(1080, 1920),
    position="bottom"
)
# Generates RGBA numpy arrays for each frame
frames = subtitle_layer.render(duration=clip_duration)
```

### 4. **Key Technologies**
- **Movis**: Video composition library (we'll use FFmpeg instead)
- **PIL/OpenCV**: Text rendering on frames
- **NumPy**: Frame manipulation
- **FFmpeg**: Final video compositing

---

## Implementation Plan V2

### Phase 3: JSON Style System

**Create**: `subtitle_styles/config/styles.json`

```json
{
  "simple_caption": {
    "name": "Simple Caption",
    "description": "Clean educational text with outline",
    "platform": ["instagram", "youtube_shorts", "tiktok"],
    "format": {
      "resolution": [1080, 1920],
      "aspect_ratio": "9:16"
    },
    "layout": {
      "position": "bottom",
      "safe_zone_margin": 150,
      "max_width": 900,
      "alignment": "center"
    },
    "typography": {
      "font_family": "Arial-Bold",
      "font_size_inactive": 72,
      "font_size_active": 80,
      "color_inactive": "#FFFFFF",
      "color_active": "#FFFFFF",
      "line_height": 1.2,
      "letter_spacing": 0
    },
    "effect": {
      "type": "outline",
      "outline_width": 8,
      "outline_color": "#000000",
      "shadow_enabled": true,
      "shadow_offset": [4, 4],
      "shadow_color": "#00000080"
    },
    "animation": {
      "word_transition": "scale",
      "transition_duration": 0.1,
      "max_words_per_frame": 4
    }
  },

  "glow_caption": {
    "name": "Glow Caption",
    "description": "Neon glow for gaming/tech content",
    "format": {
      "resolution": [1080, 1920],
      "aspect_ratio": "9:16"
    },
    "layout": {
      "position": "bottom",
      "safe_zone_margin": 150,
      "max_width": 900,
      "alignment": "center"
    },
    "typography": {
      "font_family": "Arial-Bold",
      "font_size_inactive": 68,
      "font_size_active": 68,
      "color_inactive": "#FFFFFF",
      "color_active": "#00FF00",
      "line_height": 1.2
    },
    "effect": {
      "type": "glow",
      "outline_width": 6,
      "outline_color": "#000000",
      "glow_color_inactive": "#FFFFFF40",
      "glow_color_active": "#00FF00FF",
      "glow_radius": 20
    },
    "animation": {
      "word_transition": "color_glow",
      "transition_duration": 0.15,
      "max_words_per_frame": 4
    }
  },

  "karaoke_style": {
    "name": "Karaoke Style",
    "description": "Y2K nostalgic word highlighting",
    "layout": {
      "position": "bottom",
      "safe_zone_margin": 150,
      "max_width": 900
    },
    "typography": {
      "font_family": "Impact",
      "font_size_inactive": 70,
      "font_size_active": 70,
      "color_inactive": "#FFFFFF",
      "color_active": "#FFFF00",
      "line_height": 1.3
    },
    "effect": {
      "type": "outline",
      "outline_width": 7,
      "outline_color": "#000000"
    },
    "animation": {
      "word_transition": "color",
      "transition_duration": 0.05,
      "max_words_per_frame": 3
    }
  }
}
```

**File**: `subtitle_styles/__init__.py`
```python
from pathlib import Path

STYLES_DIR = Path(__file__).parent / "config"
STYLES_JSON = STYLES_DIR / "styles.json"
```

---

### Phase 4: Subtitle Renderer Module

**Create**: `modules/subtitle_renderer.py`

```python
import json
from pathlib import Path
from typing import Dict, List, Tuple
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np
from utils.helpers import setup_logger


class StyleLoader:
    """Load and parse JSON subtitle style configurations"""

    @staticmethod
    def load_style(style_name: str, styles_path: Path = None) -> Dict:
        """
        Load subtitle style from JSON configuration

        Args:
            style_name: Name of style (e.g., "simple_caption")
            styles_path: Path to styles.json (optional)

        Returns:
            Dict with style configuration
        """
        if styles_path is None:
            from subtitle_styles import STYLES_JSON
            styles_path = STYLES_JSON

        with open(styles_path, 'r', encoding='utf-8') as f:
            all_styles = json.load(f)

        if style_name not in all_styles:
            raise ValueError(
                f"Style '{style_name}' not found. "
                f"Available: {list(all_styles.keys())}"
            )

        return all_styles[style_name]

    @staticmethod
    def get_available_styles(styles_path: Path = None) -> List[str]:
        """Get list of available style names"""
        if styles_path is None:
            from subtitle_styles import STYLES_JSON
            styles_path = STYLES_JSON

        with open(styles_path, 'r', encoding='utf-8') as f:
            all_styles = json.load(f)

        return list(all_styles.keys())


class SubtitleFrame:
    """Single frame of subtitle rendering with word-level effects"""

    def __init__(
        self,
        width: int,
        height: int,
        words: List[Dict],
        style: Dict,
        current_time: float
    ):
        """
        Initialize subtitle frame

        Args:
            width: Frame width (e.g., 1080)
            height: Frame height (e.g., 1920)
            words: List of word dicts with 'text_roman', 'start', 'end'
            style: Style configuration dict
            current_time: Current video timestamp in seconds
        """
        self.width = width
        self.height = height
        self.words = words
        self.style = style
        self.current_time = current_time

        # Create transparent RGBA image
        self.image = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        self.draw = ImageDraw.Draw(self.image)

    def get_active_words(self) -> List[Dict]:
        """
        Get words that should be visible at current time

        Returns word window based on style's max_words_per_frame
        """
        max_words = self.style.get('animation', {}).get('max_words_per_frame', 4)

        # Find currently speaking word
        current_word_idx = None
        for idx, word in enumerate(self.words):
            if word['start'] <= self.current_time < word['end']:
                current_word_idx = idx
                break

        if current_word_idx is None:
            return []

        # Get window of words around current word
        start_idx = max(0, current_word_idx - max_words // 2)
        end_idx = min(len(self.words), start_idx + max_words)

        # Adjust if at end of words
        if end_idx - start_idx < max_words:
            start_idx = max(0, end_idx - max_words)

        return self.words[start_idx:end_idx]

    def is_word_active(self, word: Dict) -> bool:
        """Check if word is currently being spoken"""
        return word['start'] <= self.current_time < word['end']

    def render(self) -> Image:
        """
        Render subtitle frame with word-level effects

        Returns:
            PIL Image (RGBA) with subtitles
        """
        active_words = self.get_active_words()
        if not active_words:
            return self.image

        # Load font
        font_size_inactive = self.style['typography']['font_size_inactive']
        font_size_active = self.style['typography']['font_size_active']

        # For now, use default font (TODO: custom font loading)
        try:
            font_inactive = ImageFont.truetype("Arial", font_size_inactive)
            font_active = ImageFont.truetype("Arial", font_size_active)
        except:
            font_inactive = ImageFont.load_default()
            font_active = ImageFont.load_default()

        # Calculate text layout
        layout = self._calculate_layout(active_words, font_inactive, font_active)

        # Render each word
        for word_info in layout:
            self._render_word(word_info)

        return self.image

    def _calculate_layout(
        self,
        words: List[Dict],
        font_inactive,
        font_active
    ) -> List[Dict]:
        """
        Calculate position for each word

        Returns list of word layout info with x, y, font, color
        """
        layout = []

        # Get style parameters
        position = self.style['layout']['position']
        safe_zone = self.style['layout']['safe_zone_margin']
        max_width = self.style['layout']['max_width']

        # Build text line
        text_line = " ".join([w.get('text_roman', w.get('text', '')) for w in words])

        # Calculate total width (using largest font)
        bbox = self.draw.textbbox((0, 0), text_line, font=font_active)
        total_width = bbox[2] - bbox[0]

        # Calculate Y position based on position setting
        if position == "bottom":
            y_pos = self.height - safe_zone - font_active.size
        elif position == "middle":
            y_pos = self.height // 2
        else:  # top
            y_pos = safe_zone

        # Calculate starting X (center aligned)
        x_start = (self.width - total_width) // 2
        x_current = x_start

        # Layout each word
        for word in words:
            is_active = self.is_word_active(word)
            font = font_active if is_active else font_inactive
            text = word.get('text_roman', word.get('text', ''))

            # Get word dimensions
            bbox = self.draw.textbbox((0, 0), text, font=font)
            word_width = bbox[2] - bbox[0]

            # Determine colors
            if is_active:
                color = self.style['typography']['color_active']
            else:
                color = self.style['typography']['color_inactive']

            layout.append({
                'text': text,
                'x': x_current,
                'y': y_pos,
                'font': font,
                'color': color,
                'is_active': is_active,
                'word_data': word
            })

            # Move x for next word
            x_current += word_width + 10  # 10px spacing

        return layout

    def _render_word(self, word_info: Dict):
        """
        Render a single word with effects

        Applies outline, shadow, glow based on style configuration
        """
        text = word_info['text']
        x = word_info['x']
        y = word_info['y']
        font = word_info['font']
        color = word_info['color']

        effect_type = self.style['effect']['type']

        if effect_type == "outline":
            self._render_outline_word(text, x, y, font, color)
        elif effect_type == "glow":
            self._render_glow_word(text, x, y, font, color, word_info['is_active'])
        elif effect_type == "background":
            self._render_background_word(text, x, y, font, color)
        else:
            # Simple text
            self.draw.text((x, y), text, font=font, fill=color)

    def _render_outline_word(self, text: str, x: int, y: int, font, color: str):
        """Render word with outline effect"""
        outline_width = self.style['effect']['outline_width']
        outline_color = self.style['effect']['outline_color']

        # Draw outline (draw text multiple times with offset)
        for adj_x in range(-outline_width, outline_width + 1):
            for adj_y in range(-outline_width, outline_width + 1):
                if adj_x != 0 or adj_y != 0:
                    self.draw.text(
                        (x + adj_x, y + adj_y),
                        text,
                        font=font,
                        fill=outline_color
                    )

        # Draw main text
        self.draw.text((x, y), text, font=font, fill=color)

    def _render_glow_word(
        self,
        text: str,
        x: int,
        y: int,
        font,
        color: str,
        is_active: bool
    ):
        """Render word with glow effect"""
        outline_width = self.style['effect']['outline_width']
        outline_color = self.style['effect']['outline_color']

        # Render outline first
        self._render_outline_word(text, x, y, font, outline_color)

        # Add glow layer
        glow_radius = self.style['effect'].get('glow_radius', 20)
        if is_active:
            glow_color = self.style['effect']['glow_color_active']
        else:
            glow_color = self.style['effect']['glow_color_inactive']

        # Create temporary image for glow
        glow_layer = Image.new('RGBA', self.image.size, (0, 0, 0, 0))
        glow_draw = ImageDraw.Draw(glow_layer)
        glow_draw.text((x, y), text, font=font, fill=glow_color)

        # Apply Gaussian blur
        glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(glow_radius))

        # Composite glow onto main image
        self.image = Image.alpha_composite(self.image, glow_layer)

        # Draw main text on top
        self.draw = ImageDraw.Draw(self.image)
        self.draw.text((x, y), text, font=font, fill=color)

    def _render_background_word(self, text: str, x: int, y: int, font, color: str):
        """Render word with background box"""
        # Get text bounding box
        bbox = self.draw.textbbox((x, y), text, font=font)

        # Add padding
        padding = 20
        box = [
            bbox[0] - padding,
            bbox[1] - padding,
            bbox[2] + padding,
            bbox[3] + padding
        ]

        # Draw rounded rectangle background
        bg_color = self.style['effect'].get('background_color', '#1E3A5F')
        self.draw.rounded_rectangle(box, radius=10, fill=bg_color)

        # Draw text
        self.draw.text((x, y), text, font=font, fill=color)


class SubtitleRenderer:
    """Main subtitle rendering engine"""

    def __init__(self, job_folder: Path):
        self.job_folder = job_folder
        self.logger = setup_logger("SubtitleRenderer", job_folder / "processing.log")

    def render_subtitles_for_clip(
        self,
        romanized_words: List[Dict],
        clip_duration: float,
        style_name: str = "simple_caption",
        resolution: Tuple[int, int] = (1080, 1920),
        fps: int = 30
    ) -> Path:
        """
        Render subtitle frames for a clip

        Args:
            romanized_words: Words with text_roman, start, end
            clip_duration: Clip duration in seconds
            style_name: Subtitle style to use
            resolution: Video resolution (width, height)
            fps: Frames per second

        Returns:
            Path to rendered subtitle video file
        """
        self.logger.info(f"Rendering subtitles with style: {style_name}")

        # Load style
        style = StyleLoader.load_style(style_name)

        # Calculate total frames
        total_frames = int(clip_duration * fps)

        # Create temp folder for frames
        frames_folder = self.job_folder / "subtitle_frames"
        frames_folder.mkdir(exist_ok=True)

        # Render each frame
        for frame_num in range(total_frames):
            current_time = frame_num / fps

            # Create subtitle frame
            subtitle_frame = SubtitleFrame(
                width=resolution[0],
                height=resolution[1],
                words=romanized_words,
                style=style,
                current_time=current_time
            )

            # Render and save frame
            frame_image = subtitle_frame.render()
            frame_path = frames_folder / f"frame_{frame_num:06d}.png"
            frame_image.save(frame_path)

        self.logger.info(f"Rendered {total_frames} subtitle frames")

        # Create video from frames using FFmpeg
        subtitle_video = self._create_video_from_frames(
            frames_folder,
            fps,
            clip_duration
        )

        return subtitle_video

    def _create_video_from_frames(
        self,
        frames_folder: Path,
        fps: int,
        duration: float
    ) -> Path:
        """Create transparent video from PNG frames"""
        import subprocess

        output_path = self.job_folder / "subtitles_overlay.mov"

        # FFmpeg command to create video from PNG sequence
        # Using ProRes 4444 for transparency support
        cmd = [
            'ffmpeg',
            '-framerate', str(fps),
            '-i', str(frames_folder / 'frame_%06d.png'),
            '-c:v', 'prores_ks',
            '-profile:v', '4444',
            '-pix_fmt', 'yuva444p10le',
            '-t', str(duration),
            '-y',
            str(output_path)
        ]

        self.logger.info("Creating subtitle video from frames...")
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            self.logger.error(f"FFmpeg failed: {result.stderr}")
            raise Exception("Subtitle video creation failed")

        self.logger.info(f"Subtitle video created: {output_path}")
        return output_path
```

---

### Phase 5: Video Compositor

**Update**: `modules/video_processor.py`

Add new method:

```python
def composite_subtitles(
    self,
    video_path: Path,
    subtitle_overlay_path: Path,
    output_path: Path
) -> Path:
    """
    Composite subtitle overlay onto video

    Args:
        video_path: Base video clip
        subtitle_overlay_path: Transparent subtitle video
        output_path: Output path for final video

    Returns:
        Path to composited video
    """
    self.logger.info("Compositing subtitles onto video...")

    # FFmpeg overlay filter
    cmd = [
        'ffmpeg',
        '-i', str(video_path),
        '-i', str(subtitle_overlay_path),
        '-filter_complex', '[0:v][1:v]overlay=0:0',
        '-c:v', 'libx264',
        '-preset', 'medium',
        '-crf', '23',
        '-c:a', 'copy',
        '-y',
        str(output_path)
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, check=True)

    self.logger.info(f"Subtitles composited: {output_path}")
    return output_path
```

---

### Phase 6: Pipeline Integration

**Update**: `main.py`

```python
# After clip generation
if settings.enable_subtitles:
    await send_progress("subtitles", "active", "Rendering subtitles...", 85)

    # Initialize modules
    transliterator = HindiTransliterator(job_folder)
    subtitle_renderer = SubtitleRenderer(job_folder)

    # Transliterate transcript
    romanized_transcript = transliterator.transliterate_transcript(transcript_data)

    # Get subtitle style from config
    subtitle_style = settings.subtitle_style  # e.g., "simple_caption"

    # Process each clip
    for i, (clip_info, clip_path) in enumerate(zip(clip_suggestions, generated_clips)):
        # Get words for this clip's timeframe
        clip_words = []
        for segment in romanized_transcript['segments']:
            if 'words' in segment:
                for word in segment['words']:
                    # Filter words in clip timeframe
                    if (clip_info['start_seconds'] <= word['start'] < clip_info['end_seconds']):
                        # Adjust timestamps relative to clip start
                        clip_words.append({
                            'text_roman': word.get('text_roman', word['text']),
                            'start': word['start'] - clip_info['start_seconds'],
                            'end': word['end'] - clip_info['start_seconds']
                        })

        # Render subtitles
        clip_duration = clip_info['end_seconds'] - clip_info['start_seconds']
        subtitle_overlay = subtitle_renderer.render_subtitles_for_clip(
            romanized_words=clip_words,
            clip_duration=clip_duration,
            style_name=subtitle_style,
            resolution=(1080, 1920)
        )

        # Composite subtitles onto clip
        final_clip_path = job_folder / f"clip_{i+1:02d}_final.mp4"
        video_processor.composite_subtitles(
            clip_path,
            subtitle_overlay,
            final_clip_path
        )

        # Update clip path
        generated_clips[i] = final_clip_path

    await send_progress("subtitles", "complete", "Subtitles rendered!", 95)
```

---

## Configuration

**Update**: `config.py`

```python
class Settings(BaseSettings):
    # ... existing settings ...

    # Subtitle settings
    enable_subtitles: bool = True
    subtitle_style: str = "simple_caption"  # simple_caption, glow_caption, karaoke_style
    subtitle_fps: int = 30
```

**.env**:
```env
ENABLE_SUBTITLES=true
SUBTITLE_STYLE=simple_caption
SUBTITLE_FPS=30
```

---

## Dependencies

**Add to requirements.txt**:
```txt
Pillow>=10.0.0  # Image manipulation for subtitle rendering
numpy>=1.24.0   # Frame manipulation
```

---

## File Structure

```
clip_app/
├── subtitle_styles/
│   ├── __init__.py
│   ├── config/
│   │   └── styles.json              [NEW] Style definitions
│   └── fonts/                        [NEW] Custom fonts (optional)
│
├── modules/
│   ├── transcriber.py                [✓ Phase 1]
│   ├── transliterator.py             [✓ Phase 2]
│   ├── subtitle_renderer.py          [NEW Phase 4]
│   └── video_processor.py            [UPDATE Phase 5]
│
├── main.py                           [UPDATE Phase 6]
├── config.py                         [UPDATE]
└── requirements.txt                  [UPDATE]

outputs/job_XXX/
├── transcript_romanized.json
├── subtitle_frames/                  [NEW] Frame images
│   ├── frame_000001.png
│   ├── frame_000002.png
│   └── ...
├── subtitles_overlay.mov             [NEW] Transparent subtitle video
├── clip_01.mp4                       (base clip)
└── clip_01_final.mp4                 (with subtitles)
```

---

## Comparison: Our System vs Reference Project

| Feature | VinVideo (Reference) | Our System |
|---------|---------------------|------------|
| **Composition Library** | Movis | FFmpeg |
| **Style Definition** | JSON | JSON (same) |
| **Word-level Timing** | WhisperX | WhisperX (same) |
| **Frame Rendering** | NumPy arrays | PIL Images |
| **Effects** | 9 styles | 3-5 styles (start small) |
| **Language** | English | Hindi → Roman |
| **Output** | MP4 via Movis | MP4 via FFmpeg |
| **Fonts** | Custom TTF | System fonts (start) |

---

## Implementation Timeline

### Week 1
- **Day 1-2**: Create JSON style system + StyleLoader
- **Day 3-5**: Build SubtitleFrame and basic rendering

### Week 2
- **Day 1-3**: Implement SubtitleRenderer with frame generation
- **Day 4**: Add video compositor to video_processor.py
- **Day 5**: Integrate into main pipeline + testing

**Total**: ~10 days

---

## Testing Strategy

1. **Test style loading**: Verify JSON parsing
2. **Test frame rendering**: Single frame with simple_caption
3. **Test word activation**: Verify word highlighting logic
4. **Test full clip**: 15-second clip with subtitles
5. **Test multiple styles**: Switch between styles
6. **Test performance**: Measure rendering time

---

## Performance Considerations

**Rendering Time Estimate**:
- 30-second clip @ 30fps = 900 frames
- ~0.1s per frame (PIL rendering) = 90 seconds
- **Total per clip**: ~1.5-2 minutes

**Optimizations**:
1. **Only render frames with text** (skip empty frames)
2. **Cache font objects** (don't reload each frame)
3. **Parallel rendering** (multiprocessing for frames)
4. **Lower FPS option** (15fps for faster rendering)

---

## Next Steps

1. ✅ **Phase 1 & 2 Complete** - Word timestamps + transliteration
2. **Phase 3**: Create `subtitle_styles/config/styles.json`
3. **Phase 4**: Build `modules/subtitle_renderer.py`
4. **Phase 5**: Update `video_processor.py` with compositor
5. **Phase 6**: Integrate into `main.py` pipeline

---

## Questions Before Implementation

1. **Which styles to implement first?**
   - Recommend: simple_caption, glow_caption, karaoke_style

2. **Font preferences?**
   - Start with system fonts (Arial, Impact)
   - Can add custom fonts later

3. **Performance vs Quality?**
   - 30fps for smooth animation
   - 15fps option for faster rendering

---

**Ready to implement Phase 3?** Let me know and I'll start building the JSON style system and subtitle renderer!
