"""
Subtitle Renderer Module
Adapted from VinVideo project for programmatic subtitle rendering
Generates word-by-word animated subtitles for short-form vertical videos
"""

import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import subprocess
from utils.helpers import setup_logger

# Import text effects from VinVideo project
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from subtitle_styles.effects.text_effects import TextEffects
from subtitle_styles.effects.word_highlight_effects import WordHighlightEffects


class StyleLoader:
    """Load subtitle styles from JSON configuration"""

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


class SubtitleRenderer:
    """
    Main subtitle rendering engine
    Generates word-by-word animated subtitle frames
    """

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
        self.logger.info(f"Total words to render: {len(romanized_words)}")

        # Load style
        style = StyleLoader.load_style(style_name)

        # Calculate total frames
        total_frames = int(clip_duration * fps)

        # Create temp folder for frames
        frames_folder = self.job_folder / "subtitle_frames"
        frames_folder.mkdir(exist_ok=True)

        self.logger.info(f"Generating {total_frames} frames at {fps} fps...")

        # Render each frame
        for frame_num in range(total_frames):
            current_time = frame_num / fps

            # Create subtitle frame
            frame_image = self._render_frame(
                words=romanized_words,
                current_time=current_time,
                style=style,
                resolution=resolution
            )

            # Save frame
            frame_path = frames_folder / f"frame_{frame_num:06d}.png"
            frame_image.save(frame_path)

            # Log progress every 100 frames
            if frame_num % 100 == 0:
                progress = (frame_num / total_frames) * 100
                self.logger.info(f"Rendering progress: {progress:.1f}% ({frame_num}/{total_frames} frames)")

        self.logger.info(f"✓ Rendered {total_frames} subtitle frames")

        # Create video from frames using FFmpeg
        subtitle_video = self._create_video_from_frames(
            frames_folder,
            fps,
            clip_duration
        )

        return subtitle_video

    def _render_frame(
        self,
        words: List[Dict],
        current_time: float,
        style: Dict,
        resolution: Tuple[int, int]
    ) -> Image:
        """
        Render a single subtitle frame

        Args:
            words: List of words with timestamps
            current_time: Current time in seconds
            style: Style configuration
            resolution: (width, height)

        Returns:
            PIL Image (RGBA) with subtitles
        """
        width, height = resolution

        # Get active words for this time
        active_words, highlighted_index = self._get_active_words(
            words,
            current_time,
            style['layout']['words_per_window']
        )

        if not active_words:
            # Return transparent frame
            return Image.new('RGBA', resolution, (0, 0, 0, 0))

        # Extract word texts
        word_texts = [w.get('text_roman', w.get('text', '')) for w in active_words]

        # Apply text transform
        text_transform = style['typography'].get('text_transform', 'none')
        if text_transform == 'uppercase':
            word_texts = [t.upper() for t in word_texts]
        elif text_transform == 'lowercase':
            word_texts = [t.lower() for t in word_texts]

        # Render based on effect type
        effect_type = style['effect_type']

        try:
            if effect_type == "outline":
                frame_array = self._render_outline_style(word_texts, highlighted_index, style, resolution)
            elif effect_type == "text_shadow":
                frame_array = self._render_glow_style(word_texts, highlighted_index, style, resolution)
            elif effect_type == "dual_glow":
                frame_array = self._render_karaoke_style(word_texts, highlighted_index, style, resolution)
            else:
                # Fallback to simple text
                frame_array = self._render_simple_text(word_texts, style, resolution)

            # Convert numpy array to PIL Image
            return Image.fromarray(frame_array.astype('uint8'), 'RGBA')

        except Exception as e:
            self.logger.error(f"Frame rendering failed: {e}")
            # Return transparent frame on error
            return Image.new('RGBA', resolution, (0, 0, 0, 0))

    def _get_active_words(
        self,
        words: List[Dict],
        current_time: float,
        max_words: int
    ) -> Tuple[List[Dict], int]:
        """
        Get words that should be visible at current time

        Returns:
            (active_words, highlighted_word_index)
        """
        # Find currently speaking word
        current_word_idx = None
        for idx, word in enumerate(words):
            if word['start'] <= current_time < word['end']:
                current_word_idx = idx
                break

        if current_word_idx is None:
            return [], -1

        # Get window of words around current word
        start_idx = max(0, current_word_idx - max_words // 2)
        end_idx = min(len(words), start_idx + max_words)

        # Adjust if at end of words
        if end_idx - start_idx < max_words:
            start_idx = max(0, end_idx - max_words)

        active_words = words[start_idx:end_idx]

        # Calculate highlighted index within window
        highlighted_index = current_word_idx - start_idx

        return active_words, highlighted_index

    def _render_outline_style(
        self,
        word_texts: List[str],
        highlighted_index: int,
        style: Dict,
        resolution: Tuple[int, int]
    ) -> np.ndarray:
        """
        Render simple_caption style (outline effect with size change)
        """
        width, height = resolution

        # Get style parameters
        font_family = style['typography']['font_family']
        font_size = style['typography']['font_size']
        font_size_highlighted = style['typography']['font_size_highlighted']
        text_color = tuple(style['typography']['colors']['text'])
        outline_color = tuple(style['typography']['colors']['outline'])
        outline_width = style['effect_parameters']['outline_width']
        bottom_margin = style['layout']['safe_margins']['bottom']

        # Use WordHighlightEffects for size-based highlighting
        try:
            frame_array = WordHighlightEffects.create_outline_with_size_highlight(
                words=word_texts,
                font_path=font_family,
                normal_font_size=font_size,
                highlighted_font_size=font_size_highlighted,
                text_color=text_color,
                outline_color=outline_color,
                outline_width=outline_width,
                highlighted_word_index=highlighted_index,
                image_size=resolution,
                bottom_margin=bottom_margin
            )
            return frame_array
        except Exception as e:
            self.logger.warning(f"WordHighlightEffects failed, using fallback: {e}")
            return self._render_simple_text(word_texts, style, resolution)

    def _render_glow_style(
        self,
        word_texts: List[str],
        highlighted_index: int,
        style: Dict,
        resolution: Tuple[int, int]
    ) -> np.ndarray:
        """
        Render glow_caption style (text shadow/glow effect)
        """
        width, height = resolution

        # Get style parameters
        font_family = style['typography']['font_family']
        font_size = style['typography']['font_size']
        text_normal = tuple(style['typography']['colors']['text_normal'])
        text_highlighted = tuple(style['typography']['colors']['text_highlighted'])
        outline_color = tuple(style['effect_parameters']['outline_color'])
        outline_width = style['effect_parameters']['outline_width']
        shadow_blur = style['text_shadow']['shadowBlur']
        bottom_margin = style['layout']['safe_margins']['bottom']

        # Use WordHighlightEffects for color-based highlighting with glow
        try:
            frame_array = WordHighlightEffects.create_color_highlight_with_glow(
                words=word_texts,
                font_path=font_family,
                font_size=font_size,
                normal_color=text_normal,
                highlighted_color=text_highlighted,
                outline_color=outline_color,
                outline_width=outline_width,
                glow_radius=shadow_blur,
                highlighted_word_index=highlighted_index,
                image_size=resolution,
                bottom_margin=bottom_margin
            )
            return frame_array
        except Exception as e:
            self.logger.warning(f"Glow rendering failed, using fallback: {e}")
            return self._render_simple_text(word_texts, style, resolution)

    def _render_karaoke_style(
        self,
        word_texts: List[str],
        highlighted_index: int,
        style: Dict,
        resolution: Tuple[int, int]
    ) -> np.ndarray:
        """
        Render karaoke_style (two-tone word colors, no glow)
        """
        width, height = resolution

        # Get style parameters
        font_family = style['typography']['font_family']
        font_size = style['typography']['font_size']
        text_normal = tuple(style['typography']['colors']['text_normal'])
        text_highlighted = tuple(style['typography']['colors']['text_highlighted'])
        outline_color = tuple(style['effect_parameters']['outline_color'])
        outline_width = style['effect_parameters']['outline_width']
        bottom_margin = style['layout']['safe_margins']['bottom']

        # Use TextEffects for two-tone effect
        try:
            frame_array = TextEffects.create_two_tone_glow_effect(
                words=word_texts,
                font_path=font_family,
                font_size=font_size,
                normal_text_color=text_normal,
                highlighted_text_color=text_highlighted,
                normal_glow_color=text_normal,
                highlighted_glow_color=text_highlighted,
                normal_glow_radius=0,  # No glow for karaoke
                highlighted_glow_radius=0,
                normal_glow_intensity=0.0,
                highlighted_glow_intensity=0.0,
                highlighted_word_index=highlighted_index,
                image_size=resolution
            )

            # Position at bottom with margin
            final_img = Image.new('RGBA', resolution, (0, 0, 0, 0))
            text_img = Image.fromarray(frame_array.astype('uint8'), 'RGBA')

            # Center horizontally, position at bottom with margin
            paste_y = height - bottom_margin - text_img.height
            final_img.paste(text_img, (0, paste_y), text_img)

            return np.array(final_img)

        except Exception as e:
            self.logger.warning(f"Karaoke rendering failed, using fallback: {e}")
            return self._render_simple_text(word_texts, style, resolution)

    def _render_simple_text(
        self,
        word_texts: List[str],
        style: Dict,
        resolution: Tuple[int, int]
    ) -> np.ndarray:
        """
        Fallback: render simple text without effects
        """
        width, height = resolution
        img = Image.new('RGBA', resolution, (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Join words
        text = ' '.join(word_texts)

        # Load font
        try:
            font_family = style['typography']['font_family']
            font_size = style['typography']['font_size']
            font = ImageFont.truetype(font_family, font_size)
        except:
            font = ImageFont.load_default()

        # Get text size
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        # Center position
        x = (width - text_width) // 2
        y = height - style['layout']['safe_margins']['bottom'] - text_height

        # Draw text
        text_color = tuple(style['typography']['colors'].get('text', [255, 255, 255]))
        draw.text((x, y), text, font=font, fill=(*text_color, 255))

        return np.array(img)

    def _create_video_from_frames(
        self,
        frames_folder: Path,
        fps: int,
        duration: float
    ) -> Path:
        """
        Create transparent video from PNG frames using FFmpeg

        Returns:
            Path to subtitle overlay video
        """
        output_path = self.job_folder / "subtitles_overlay.mov"

        self.logger.info("Creating subtitle video from frames...")

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

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            self.logger.info(f"✓ Subtitle video created: {output_path}")
            return output_path
        except subprocess.CalledProcessError as e:
            self.logger.error(f"FFmpeg failed: {e.stderr}")
            raise Exception("Subtitle video creation failed")
