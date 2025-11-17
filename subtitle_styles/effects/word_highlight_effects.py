"""
Word-by-word background highlighting effects for subtitle styles
Similar to karaoke color changes but using background highlights instead
"""

from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np
from typing import List, Tuple, Optional

class WordHighlightEffects:
    """Text effects that highlight individual words with background colors based on audio timing"""
    
    @staticmethod
    def create_word_background_highlight_effect(words: List[str],
                                              font_path: str,
                                              font_size: int,
                                              text_color: Tuple[int, int, int],
                                              normal_bg_color: Optional[Tuple[int, int, int]] = None,
                                              highlight_bg_color: Tuple[int, int, int] = (138, 43, 226),  # Purple
                                              highlighted_word_index: int = -1,
                                              background_padding: Tuple[int, int] = (20, 10),
                                              corner_radius: int = 15,
                                              image_size: Tuple[int, int] = (1080, 200)) -> np.ndarray:
        """
        Create text with word-by-word background highlighting
        Each word can have its own background color based on audio timing
        
        Args:
            words: List of words to render
            font_path: Path to font file
            font_size: Font size in pixels
            text_color: RGB color for text
            normal_bg_color: RGB color for normal word backgrounds (None = transparent)
            highlight_bg_color: RGB color for highlighted word background
            highlighted_word_index: Index of word to highlight (-1 = none)
            background_padding: (x, y) padding around each word background
            corner_radius: Radius for rounded corners on backgrounds
            image_size: Output image dimensions
        """
        width, height = image_size
        padding = max(background_padding) * 3
        
        # Create main canvas
        img = Image.new('RGBA', (width + padding*2, height + padding*2), (0, 0, 0, 0))
        
        # Load font
        try:
            font = ImageFont.truetype(font_path, font_size)
        except:
            font = ImageFont.load_default()
        
        # Split text and calculate positions
        draw = ImageDraw.Draw(img)
        
        # Calculate word positions
        word_positions = []
        total_width = 0
        word_widths = []
        
        # Get width of each word
        for word in words:
            bbox = draw.textbbox((0, 0), word, font=font)
            word_width = bbox[2] - bbox[0]
            word_widths.append(word_width)
            total_width += word_width
        
        # Add spacing between words
        space_width = draw.textbbox((0, 0), " ", font=font)[2]
        total_width += space_width * (len(words) - 1)
        
        # Calculate starting position (centered)
        x = (width - total_width) // 2 + padding
        y = (height - font_size) // 2 + padding
        
        # Position each word
        for i, word in enumerate(words):
            word_positions.append({
                'word': word,
                'x': x,
                'y': y,
                'width': word_widths[i]
            })
            x += word_widths[i] + space_width
        
        # Draw backgrounds first
        bg_img = Image.new('RGBA', img.size, (0, 0, 0, 0))
        bg_draw = ImageDraw.Draw(bg_img)
        
        for i, pos in enumerate(word_positions):
            # Determine background color
            if i == highlighted_word_index:
                bg_color = highlight_bg_color
            elif normal_bg_color is not None:
                bg_color = normal_bg_color
            else:
                continue  # Skip if no background for normal words
            
            # Calculate background bounds with padding
            bg_x1 = pos['x'] - background_padding[0]
            bg_y1 = pos['y'] - background_padding[1]
            bg_x2 = pos['x'] + pos['width'] + background_padding[0]
            bg_y2 = pos['y'] + font_size + background_padding[1]
            
            # Draw rounded rectangle background
            if corner_radius > 0:
                # Draw rounded rectangle
                bg_draw.rounded_rectangle(
                    [bg_x1, bg_y1, bg_x2, bg_y2],
                    radius=corner_radius,
                    fill=(*bg_color, 255)
                )
            else:
                # Draw regular rectangle
                bg_draw.rectangle(
                    [bg_x1, bg_y1, bg_x2, bg_y2],
                    fill=(*bg_color, 255)
                )
        
        # Composite background onto main image
        img = Image.alpha_composite(img, bg_img)
        draw = ImageDraw.Draw(img)
        
        # Draw text on top
        for pos in word_positions:
            draw.text(
                (pos['x'], pos['y']), 
                pos['word'], 
                font=font, 
                fill=(*text_color, 255)
            )
        
        # Crop to original size
        img = img.crop((padding, padding, width + padding, height + padding))
        
        # Ensure RGBA format
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        
        return np.array(img)
    
    @staticmethod
    def create_deep_diver_effect(words: List[str],
                                font_path: str,
                                font_size: int,
                                active_text_color: Tuple[int, int, int] = (0, 0, 0),  # Black
                                inactive_text_color: Tuple[int, int, int] = (80, 80, 80),  # Gray
                                background_color: Tuple[int, int, int] = (140, 140, 140),  # Light gray
                                highlighted_word_index: int = -1,
                                background_padding: Tuple[int, int] = (20, 10),
                                corner_radius: int = 25,
                                image_size: Tuple[int, int] = (1080, 200)) -> np.ndarray:
        """
        Create Deep Diver style: gray background with black active word, gray inactive words
        
        Args:
            words: List of words to render
            font_path: Path to font file
            font_size: Font size in pixels
            active_text_color: RGB color for active/highlighted word
            inactive_text_color: RGB color for inactive words
            background_color: RGB color for background
            highlighted_word_index: Index of word to highlight (-1 = none)
            background_padding: (x, y) padding around text background
            corner_radius: Radius for rounded corners on background
            image_size: Output image dimensions
        """
        width, height = image_size
        padding = 50  # Minimal external padding for proper centering
        
        # Create main canvas
        img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        
        # Load font and get font metrics
        try:
            font = ImageFont.truetype(font_path, font_size)
        except:
            font = ImageFont.load_default()
            
        # Create a temporary draw object to measure text
        temp_draw = ImageDraw.Draw(img)
        
        # Calculate total text dimensions for all words
        total_width = 0
        max_height = 0
        word_widths = []
        word_data = []
        
        # Measure each word
        for i, word in enumerate(words):
            bbox = temp_draw.textbbox((0, 0), word, font=font)
            word_width = bbox[2] - bbox[0]
            word_height = bbox[3] - bbox[1]
            word_widths.append(word_width)
            word_data.append({
                'word': word,
                'width': word_width,
                'height': word_height,
                'bbox': bbox
            })
            total_width += word_width
            max_height = max(max_height, word_height)
        
        # Add spacing between words
        space_bbox = temp_draw.textbbox((0, 0), " ", font=font)
        space_width = space_bbox[2] - space_bbox[0]
        total_width += space_width * (len(words) - 1)
        
        # Get font metrics for proper vertical alignment
        ascent, descent = font.getmetrics()
        
        # Calculate the single background rectangle that contains all text
        bg_width = total_width + (background_padding[0] * 2)
        bg_height = ascent + descent + (background_padding[1] * 2)
        
        # Center the background rectangle
        bg_x = (width - bg_width) // 2
        bg_y = (height - bg_height) // 2
        
        # Draw the background
        bg_img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        bg_draw = ImageDraw.Draw(bg_img)
        
        # Draw background rectangle
        bg_draw.rounded_rectangle(
            [bg_x, bg_y, bg_x + bg_width, bg_y + bg_height],
            radius=corner_radius,
            fill=(*background_color, 255)
        )
        
        # Composite background onto main image
        img = Image.alpha_composite(img, bg_img)
        draw = ImageDraw.Draw(img)
        
        # Calculate text starting position (centered within background)
        text_x = bg_x + background_padding[0]
        text_y = bg_y + background_padding[1]
        
        # Draw each word
        current_x = text_x
        for i, word_info in enumerate(word_data):
            # Choose color based on whether word is highlighted
            if i == highlighted_word_index:
                color = active_text_color
            else:
                color = inactive_text_color
            
            # Draw word at calculated position
            draw.text(
                (current_x, text_y), 
                word_info['word'], 
                font=font, 
                fill=(*color, 255)
            )
            
            # Move to next word position
            current_x += word_info['width'] + space_width
        
        # Ensure RGBA format
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        
        return np.array(img)
    
    @staticmethod
    def create_full_background_with_word_highlight(words: List[str],
                                                 font_path: str,
                                                 font_size: int,
                                                 text_color: Tuple[int, int, int],
                                                 background_color: Tuple[int, int, int],
                                                 highlighted_word_index: int = -1,
                                                 background_padding: Tuple[int, int] = (40, 20),
                                                 corner_radius: int = 15,
                                                 highlight_brightness_boost: int = 0,
                                                 image_size: Tuple[int, int] = (1080, 200)) -> np.ndarray:
        """
        Create text with full background and optional word highlighting through brightness change
        
        Args:
            words: List of words to render
            font_path: Path to font file
            font_size: Font size in pixels
            text_color: RGB color for text
            background_color: RGB color for background
            highlighted_word_index: Index of word to highlight (-1 = none)
            background_padding: (x, y) padding around text
            corner_radius: Radius for rounded corners
            highlight_brightness_boost: Amount to brighten background for highlighted word
            image_size: Output image dimensions
        """
        width, height = image_size
        padding = max(background_padding) * 2
        
        # Create main canvas
        img = Image.new('RGBA', (width + padding*2, height + padding*2), (0, 0, 0, 0))
        
        # Load font
        try:
            font = ImageFont.truetype(font_path, font_size)
        except:
            font = ImageFont.load_default()
        
        # Join words
        text = ' '.join(words)
        
        # Measure text
        draw = ImageDraw.Draw(img)
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # Calculate background bounds
        bg_width = text_width + (background_padding[0] * 2)
        bg_height = text_height + (background_padding[1] * 2)
        
        # Center position
        bg_x = (width - bg_width) // 2 + padding
        bg_y = (height - bg_height) // 2 + padding
        
        # Draw background
        bg_draw = ImageDraw.Draw(img)
        
        # Apply brightness boost if word is highlighted
        bg_color = background_color
        if highlighted_word_index >= 0 and highlight_brightness_boost > 0:
            bg_color = tuple(min(255, c + highlight_brightness_boost) for c in background_color)
        
        # Draw rounded rectangle background
        bg_draw.rounded_rectangle(
            [bg_x, bg_y, bg_x + bg_width, bg_y + bg_height],
            radius=corner_radius,
            fill=(*bg_color, 255)
        )
        
        # Draw text
        text_x = bg_x + background_padding[0]
        text_y = bg_y + background_padding[1]
        
        draw.text(
            (text_x, text_y), 
            text, 
            font=font, 
            fill=(*text_color, 255)
        )
        
        # Crop to original size
        img = img.crop((padding, padding, width + padding, height + padding))
        
        # Ensure RGBA format
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        
        return np.array(img)
    
    @staticmethod
    def create_horizontal_flip_effect(words: List[str],
                                    font_path: str,
                                    font_size: int,
                                    text_color: Tuple[int, int, int],
                                    background_color: Tuple[int, int, int],
                                    highlighted_word_index: int = -1,
                                    flip_progress: float = 0.0,
                                    background_padding: Tuple[int, int] = (20, 10),
                                    corner_radius: int = 15,
                                    image_size: Tuple[int, int] = (1080, 200)) -> np.ndarray:
        """
        Create text with horizontal flip animation for highlighted word
        
        Args:
            words: List of words to render
            font_path: Path to font file
            font_size: Font size in pixels
            text_color: RGB color for text
            background_color: RGB color for background
            highlighted_word_index: Index of word to flip (-1 = none)
            flip_progress: Animation progress (0.0 to 1.0)
            background_padding: (x, y) padding around each word
            corner_radius: Radius for rounded corners
            image_size: Output image dimensions
        """
        width, height = image_size
        padding = 50
        
        # Create main canvas
        img = Image.new('RGBA', (width + padding*2, height + padding*2), (0, 0, 0, 0))
        
        # Load font
        try:
            font = ImageFont.truetype(font_path, font_size)
        except:
            font = ImageFont.load_default()
        
        # Calculate word positions (same as before)
        draw = ImageDraw.Draw(img)
        word_positions = []
        total_width = 0
        word_widths = []
        
        for word in words:
            bbox = draw.textbbox((0, 0), word, font=font)
            word_width = bbox[2] - bbox[0]
            word_widths.append(word_width)
            total_width += word_width
        
        space_width = draw.textbbox((0, 0), " ", font=font)[2]
        total_width += space_width * (len(words) - 1)
        
        x = (width - total_width) // 2 + padding
        y = (height - font_size) // 2 + padding
        
        for i, word in enumerate(words):
            word_positions.append({
                'word': word,
                'x': x,
                'y': y,
                'width': word_widths[i]
            })
            x += word_widths[i] + space_width
        
        # Draw each word
        for i, pos in enumerate(word_positions):
            # Create word image
            word_img = Image.new('RGBA', (int(pos['width'] + background_padding[0]*2), 
                                         int(font_size + background_padding[1]*2)), 
                                        (0, 0, 0, 0))
            word_draw = ImageDraw.Draw(word_img)
            
            # Draw background
            word_draw.rounded_rectangle(
                [0, 0, word_img.width-1, word_img.height-1],
                radius=corner_radius,
                fill=(*background_color, 255)
            )
            
            # Draw text
            word_draw.text(
                (background_padding[0], background_padding[1]), 
                pos['word'], 
                font=font, 
                fill=(*text_color, 255)
            )
            
            # Apply flip effect if this is the highlighted word
            if i == highlighted_word_index and flip_progress > 0:
                # Scale horizontally based on flip progress
                # 0->0.5: scale from 1 to 0, 0.5->1: scale from 0 to 1
                if flip_progress <= 0.5:
                    scale_x = 1.0 - (flip_progress * 2)
                else:
                    scale_x = (flip_progress - 0.5) * 2
                
                if scale_x > 0:
                    new_width = max(1, int(word_img.width * scale_x))
                    word_img = word_img.resize((new_width, word_img.height), Image.Resampling.LANCZOS)
            
            # Paste word onto main image
            paste_x = pos['x'] - background_padding[0]
            if i == highlighted_word_index and flip_progress > 0:
                # Center the flipped word
                paste_x += (pos['width'] + background_padding[0]*2 - word_img.width) // 2
            
            img.paste(word_img, (int(paste_x), int(pos['y'] - background_padding[1])), word_img)
        
        # Crop to original size
        img = img.crop((padding, padding, width + padding, height + padding))
        
        # Ensure RGBA format
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        
        return np.array(img)
    
    @staticmethod
    def create_underline_effect(text: str,
                               font_path: str,
                               font_size: int,
                               text_color: Tuple[int, int, int],
                               outline_color: Tuple[int, int, int] = (0, 0, 0),
                               outline_width: int = 5,
                               underline_color: Tuple[int, int, int] = (147, 51, 234),
                               underline_height: int = 8,
                               underline_offset: int = 10,
                               highlighted_word_index: int = -1,
                               image_size: Tuple[int, int] = (1080, 200)) -> np.ndarray:
        """
        Create text with hand-drawn style underline effect for highlighted word
        
        Args:
            text: Text to render
            font_path: Path to font file
            font_size: Font size in pixels
            text_color: RGB color for text
            outline_color: RGB color for text outline
            outline_width: Width of text outline
            underline_color: RGB color for underline
            underline_height: Height/thickness of underline
            underline_offset: Vertical offset from text baseline
            highlighted_word_index: Index of word to underline (-1 = none)
            image_size: Output image dimensions
        """
        width, height = image_size
        padding = 50
        
        # Create main canvas
        img = Image.new('RGBA', (width + padding*2, height + padding*2), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Load font
        try:
            font = ImageFont.truetype(font_path, font_size)
        except:
            font = ImageFont.load_default()
        
        # Split text into words
        words = text.split()
        
        # Calculate word positions
        word_positions = []
        total_width = 0
        word_widths = []
        
        # Get width of each word
        for word in words:
            bbox = draw.textbbox((0, 0), word, font=font)
            word_width = bbox[2] - bbox[0]
            word_widths.append(word_width)
            total_width += word_width
        
        # Add spacing between words
        space_width = draw.textbbox((0, 0), " ", font=font)[2]
        total_width += space_width * (len(words) - 1)
        
        # Calculate starting position (centered)
        x = (width - total_width) // 2 + padding
        y = (height - font_size) // 2 + padding
        
        # Position each word
        for i, word in enumerate(words):
            word_positions.append({
                'word': word,
                'x': x,
                'y': y,
                'width': word_widths[i]
            })
            x += word_widths[i] + space_width
        
        # Draw text with outline effect
        for i, pos in enumerate(word_positions):
            # Draw outline
            for dx in range(-outline_width, outline_width + 1):
                for dy in range(-outline_width, outline_width + 1):
                    if dx*dx + dy*dy <= outline_width*outline_width:
                        draw.text(
                            (pos['x'] + dx, pos['y'] + dy), 
                            pos['word'], 
                            font=font, 
                            fill=(*outline_color, 255)
                        )
            
            # Draw main text
            draw.text(
                (pos['x'], pos['y']), 
                pos['word'], 
                font=font, 
                fill=(*text_color, 255)
            )
        
        # Draw underline for highlighted word
        if 0 <= highlighted_word_index < len(word_positions):
            pos = word_positions[highlighted_word_index]
            
            # Calculate underline position
            text_bbox = draw.textbbox((pos['x'], pos['y']), pos['word'], font=font)
            underline_y = text_bbox[3] + underline_offset
            underline_start_x = pos['x']
            underline_end_x = pos['x'] + pos['width']
            
            # Create hand-drawn effect with slight waviness
            points = []
            num_points = 20
            for i in range(num_points + 1):
                x_pos = underline_start_x + (underline_end_x - underline_start_x) * i / num_points
                # Add slight wave effect
                y_offset = np.sin(i * 0.5) * 2
                points.append((x_pos, underline_y + y_offset))
            
            # Draw underline with thickness
            for i in range(len(points) - 1):
                draw.line([points[i], points[i + 1]], fill=(*underline_color, 255), width=underline_height)
        
        # Crop to original size
        img = img.crop((padding, padding, width + padding, height + padding))
        
        # Ensure RGBA format
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        
        return np.array(img)