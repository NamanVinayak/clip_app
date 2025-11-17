"""
Text Effects Module
Provides various text effects like glow, shadow, outline using PIL/Pillow
"""

from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np
from typing import Tuple, Optional, Union, List
import os


class TextEffects:
    """Collection of text effect methods"""
    
    @staticmethod
    def create_glow_effect(text: str,
                          font_path: str,
                          font_size: int,
                          text_color: Tuple[int, int, int],
                          glow_color: Tuple[int, int, int],
                          glow_radius: int = 10,
                          glow_intensity: float = 0.8,
                          image_size: Tuple[int, int] = (1080, 1920)) -> np.ndarray:
        """
        Create glowing text effect
        Returns RGBA numpy array
        """
        # Create image with transparent background
        padding = glow_radius * 3
        width, height = image_size
        
        # Create larger canvas for glow effect
        img = Image.new('RGBA', (width + padding*2, height + padding*2), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        print(f"[TextEffects.create_glow_effect] Received text: '{text}', font_path: '{font_path}', font_size: {font_size}") # Log input text
        
        # Load font
        try:
            font = ImageFont.truetype(font_path, font_size)
        except:
            # Fallback to default font
            font = ImageFont.load_default()
        
        # Get text bounding box
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # Center position
        x = (width + padding*2 - text_width) // 2
        y = (height + padding*2 - text_height) // 2
        
        # Create glow layers
        glow_img = Image.new('RGBA', img.size, (0, 0, 0, 0))
        glow_draw = ImageDraw.Draw(glow_img)
        
        # Draw multiple glow layers with decreasing opacity
        for i in range(glow_radius, 0, -1):
            opacity = int(255 * glow_intensity * (i / glow_radius))
            current_glow_color = (*glow_color, opacity)
            
            # Draw text with stroke for glow
            print(f"[TextEffects.create_glow_effect] Drawing glow layer with text: '{text}'") # Log text for glow layer
            glow_draw.text((x, y), text, font=font, 
                          fill=current_glow_color,
                          stroke_width=i*2, 
                          stroke_fill=current_glow_color)
        
        # Apply gaussian blur to glow
        glow_img = glow_img.filter(ImageFilter.GaussianBlur(radius=glow_radius//2))
        
        # Composite glow onto main image
        img = Image.alpha_composite(img, glow_img)
        
        # Draw main text on top
        draw = ImageDraw.Draw(img)
        print(f"[TextEffects.create_glow_effect] Drawing main text: '{text}'") # Log text for main text
        draw.text((x, y), text, font=font, fill=(*text_color, 255))
        
        # Crop back to original size
        img = img.crop((padding, padding, width + padding, height + padding))
        
        # Convert to numpy array (RGBA)
        return np.array(img)
    
    @staticmethod
    def create_two_tone_glow_effect(words: List[str],
                                   font_path: str,
                                   font_size: int,
                                   normal_text_color: Tuple[int, int, int],
                                   highlighted_text_color: Tuple[int, int, int],
                                   normal_glow_color: Tuple[int, int, int],
                                   highlighted_glow_color: Tuple[int, int, int],
                                   normal_glow_radius: int = 12,
                                   highlighted_glow_radius: int = 15,
                                   normal_glow_intensity: float = 0.4,
                                   highlighted_glow_intensity: float = 0.6,
                                   highlighted_word_index: int = -1,
                                   image_size: Tuple[int, int] = (1080, 1920)) -> np.ndarray:
        """
        Create two-tone glow effect with separate styling for each word
        Some words are normal (white + white glow), others are highlighted (red + red glow)
        """
        width, height = image_size
        padding = max(normal_glow_radius, highlighted_glow_radius) * 3
        
        # Create main canvas
        img = Image.new('RGBA', (width + padding*2, height + padding*2), (0, 0, 0, 0))
        
        # Load font
        try:
            font = ImageFont.truetype(font_path, font_size)
        except:
            font = ImageFont.load_default()
        
        # Calculate text layout - all words in one line
        full_text = ' '.join(words)
        draw = ImageDraw.Draw(img)
        bbox = draw.textbbox((0, 0), full_text, font=font)
        total_width = bbox[2] - bbox[0]
        total_height = bbox[3] - bbox[1]
        
        # Auto-scale font if text is too wide (ensure 5% margins on each side)
        max_text_width = width * 0.9  # Use 90% of canvas width
        if total_width > max_text_width:
            scale_factor = max_text_width / total_width
            new_font_size = int(font_size * scale_factor)
            
            # Reload font with new size
            try:
                font = ImageFont.truetype(font_path, new_font_size)
            except:
                font = ImageFont.load_default()
                
            # Recalculate dimensions with new font
            bbox = draw.textbbox((0, 0), full_text, font=font)
            total_width = bbox[2] - bbox[0]
            total_height = bbox[3] - bbox[1]
            
            # Uncomment for debugging: print(f"Auto-scaled font in text effects: {font_size}px -> {new_font_size}px (text width: {total_width}px)")
        
        # Center the entire text block
        start_x = (width + padding*2 - total_width) // 2
        start_y = (height + padding*2 - total_height) // 2
        
        # Create glow layer first (behind text)
        glow_img = Image.new('RGBA', img.size, (0, 0, 0, 0))
        
        # Render each word separately
        current_x = start_x
        for i, word in enumerate(words):
            # Determine if this word is highlighted
            is_highlighted = (i == highlighted_word_index)
            
            # Choose colors and settings
            if is_highlighted:
                text_color = highlighted_text_color
                glow_color = highlighted_glow_color
                glow_radius = highlighted_glow_radius
                glow_intensity = highlighted_glow_intensity
            else:
                text_color = normal_text_color
                glow_color = normal_glow_color
                glow_radius = normal_glow_radius
                glow_intensity = normal_glow_intensity
            
            # Get word dimensions
            word_bbox = draw.textbbox((0, 0), word, font=font)
            word_width = word_bbox[2] - word_bbox[0]
            
            # Only create glow if glow_radius > 0
            if glow_radius > 0 and glow_intensity > 0:
                # Create glow for this word
                word_glow_img = Image.new('RGBA', img.size, (0, 0, 0, 0))
                glow_draw = ImageDraw.Draw(word_glow_img)
                
                # Draw glow layers with proper layering (glow behind text)
                for layer in range(glow_radius, 0, -1):
                    opacity = int(255 * glow_intensity * (layer / glow_radius) * 0.3)  # Reduced opacity
                    glow_layer_color = (*glow_color, opacity)
                    
                    # Draw glow with minimal stroke
                    glow_draw.text((current_x, start_y), word, font=font,
                                 fill=glow_layer_color,
                                 stroke_width=max(1, layer//3),
                                 stroke_fill=glow_layer_color)
                
                # Apply subtle blur to glow
                word_glow_img = word_glow_img.filter(ImageFilter.GaussianBlur(radius=glow_radius//4))
                
                # Composite this word's glow
                glow_img = Image.alpha_composite(glow_img, word_glow_img)
            
            # Move to next word position (add space)
            current_x += word_width + draw.textbbox((0, 0), ' ', font=font)[2]
        
        # Composite glow onto main image (only if there are glow effects)
        if any([normal_glow_radius > 0, highlighted_glow_radius > 0]):
            img = Image.alpha_composite(img, glow_img)
        
        # Now render crisp text on top
        text_draw = ImageDraw.Draw(img)
        current_x = start_x
        
        for i, word in enumerate(words):
            # Determine colors
            is_highlighted = (i == highlighted_word_index)
            text_color = highlighted_text_color if is_highlighted else normal_text_color
            
            # Draw crisp text with no stroke/outline
            text_draw.text((current_x, start_y), word, font=font, fill=(*text_color, 255))
            
            # Move to next position
            word_bbox = draw.textbbox((0, 0), word, font=font)
            word_width = word_bbox[2] - word_bbox[0]
            current_x += word_width + draw.textbbox((0, 0), ' ', font=font)[2]
        
        # Crop to original size
        img = img.crop((padding, padding, width + padding, height + padding))
        
        return np.array(img)
    
    @staticmethod
    def create_text_shadow_glow_effect(words: List[str],
                                      font_path: str,
                                      font_size: int,
                                      normal_text_color: Tuple[int, int, int],
                                      highlighted_text_color: Tuple[int, int, int],
                                      shadow_blur_1: int = 8,
                                      shadow_opacity_1: float = 0.6,
                                      shadow_opacity_1_highlighted: float = None,
                                      shadow_blur_2: int = 12,
                                      shadow_opacity_2: float = 0.5,
                                      shadow_opacity_2_highlighted: float = None,
                                      highlighted_word_index: int = -1,
                                      image_size: Tuple[int, int] = (1080, 1920)) -> np.ndarray:
        """
        Create text with soft text-shadow glow effects (currentColor logic)
        Two shadow layers behind crisp text fill
        """
        width, height = image_size
        padding = max(shadow_blur_1, shadow_blur_2) * 3
        
        # Create main canvas
        img = Image.new('RGBA', (width + padding*2, height + padding*2), (0, 0, 0, 0))
        
        # Load font
        try:
            font = ImageFont.truetype(font_path, font_size)
        except:
            font = ImageFont.load_default()
        
        # Calculate text layout
        full_text = ' '.join(words)
        draw = ImageDraw.Draw(img)
        bbox = draw.textbbox((0, 0), full_text, font=font)
        total_width = bbox[2] - bbox[0]
        total_height = bbox[3] - bbox[1]
        
        # Center the entire text block
        start_x = (width + padding*2 - total_width) // 2
        start_y = (height + padding*2 - total_height) // 2
        
        # Create shadow layers first (behind text)
        shadow_img = Image.new('RGBA', img.size, (0, 0, 0, 0))
        
        # Render each word separately for shadows
        current_x = start_x
        for i, word in enumerate(words):
            # Determine current color (currentColor logic)
            is_highlighted = (i == highlighted_word_index)
            current_color = highlighted_text_color if is_highlighted else normal_text_color
            
            # Get word dimensions
            word_bbox = draw.textbbox((0, 0), word, font=font)
            word_width = word_bbox[2] - word_bbox[0]
            
            # Choose opacity based on whether this word is highlighted
            current_shadow_opacity_1 = (shadow_opacity_1_highlighted if shadow_opacity_1_highlighted is not None 
                                       else shadow_opacity_1 * 1.2) if is_highlighted else shadow_opacity_1
            current_shadow_opacity_2 = (shadow_opacity_2_highlighted if shadow_opacity_2_highlighted is not None 
                                       else shadow_opacity_2 * 1.2) if is_highlighted else shadow_opacity_2
            
            # Create shadow layer 1 with appropriate opacity
            shadow_1_img = Image.new('RGBA', img.size, (0, 0, 0, 0))
            shadow_1_draw = ImageDraw.Draw(shadow_1_img)
            shadow_1_opacity = int(255 * current_shadow_opacity_1)
            shadow_1_color = (*current_color, shadow_1_opacity)
            
            # Draw shadow 1 with good expansion for visibility (70% level)
            for offset in range(1, shadow_blur_1//2 + 1):
                current_opacity = int(shadow_1_opacity * 0.75)  # 70% level opacity
                if current_opacity > 0:
                    shadow_1_draw.text((current_x, start_y), word, font=font,
                                     fill=(*current_color, current_opacity),
                                     stroke_width=int(offset * 1.7),  # 70% level stroke
                                     stroke_fill=(*current_color, current_opacity))
            
            # Apply stronger blur to shadow 1
            shadow_1_img = shadow_1_img.filter(ImageFilter.GaussianBlur(radius=shadow_blur_1//2))
            
            # Create shadow layer 2 with appropriate opacity
            shadow_2_img = Image.new('RGBA', img.size, (0, 0, 0, 0))
            shadow_2_draw = ImageDraw.Draw(shadow_2_img)
            shadow_2_opacity = int(255 * current_shadow_opacity_2)
            
            # Draw shadow 2 with good expansion for soft glow (70% level)
            for offset in range(1, shadow_blur_2//2 + 1):
                current_opacity = int(shadow_2_opacity * 0.65)  # 70% level opacity
                if current_opacity > 0:
                    shadow_2_draw.text((current_x, start_y), word, font=font,
                                     fill=(*current_color, current_opacity),
                                     stroke_width=int(offset * 2.3),  # 70% level stroke for outer glow
                                     stroke_fill=(*current_color, current_opacity))
            
            # Apply maximum blur to shadow 2 for soft outer glow
            shadow_2_img = shadow_2_img.filter(ImageFilter.GaussianBlur(radius=shadow_blur_2//2))
            
            # Composite shadows
            shadow_img = Image.alpha_composite(shadow_img, shadow_2_img)  # Layer 2 first (behind)
            shadow_img = Image.alpha_composite(shadow_img, shadow_1_img)  # Layer 1 on top
            
            # Move to next word position
            current_x += word_width + draw.textbbox((0, 0), ' ', font=font)[2]
        
        # Composite shadows onto main image
        img = Image.alpha_composite(img, shadow_img)
        
        # Now render crisp text on top
        text_draw = ImageDraw.Draw(img)
        current_x = start_x
        
        for i, word in enumerate(words):
            # Determine colors
            is_highlighted = (i == highlighted_word_index)
            text_color = highlighted_text_color if is_highlighted else normal_text_color
            
            # Draw crisp text with NO stroke/outline (clean fill only)
            text_draw.text((current_x, start_y), word, font=font, fill=(*text_color, 255))
            
            # Move to next position
            word_bbox = draw.textbbox((0, 0), word, font=font)
            word_width = word_bbox[2] - word_bbox[0]
            current_x += word_width + draw.textbbox((0, 0), ' ', font=font)[2]
        
        # Crop to original size
        img = img.crop((padding, padding, width + padding, height + padding))
        
        return np.array(img)
    
    @staticmethod
    def create_shadow_effect(text: str,
                           font_path: str,
                           font_size: int,
                           text_color: Tuple[int, int, int],
                           shadow_color: Tuple[int, int, int] = (0, 0, 0),
                           shadow_offset: Tuple[int, int] = (5, 5),
                           shadow_blur: int = 3,
                           shadow_opacity: float = 0.7,
                           image_size: Tuple[int, int] = (1080, 1920)) -> np.ndarray:
        """
        Create text with drop shadow effect
        Returns RGBA numpy array
        """
        width, height = image_size
        img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        
        # Load font
        try:
            font = ImageFont.truetype(font_path, font_size)
        except:
            font = ImageFont.load_default()
        
        # Get text bounding box
        draw = ImageDraw.Draw(img)
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # Center position
        x = (width - text_width) // 2
        y = (height - text_height) // 2
        
        # Create shadow layer
        shadow_img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow_img)
        
        # Draw shadow
        shadow_alpha = int(255 * shadow_opacity)
        shadow_draw.text((x + shadow_offset[0], y + shadow_offset[1]), 
                        text, font=font, 
                        fill=(*shadow_color, shadow_alpha))
        
        # Blur shadow
        if shadow_blur > 0:
            shadow_img = shadow_img.filter(ImageFilter.GaussianBlur(radius=shadow_blur))
        
        # Composite shadow onto main image
        img = Image.alpha_composite(img, shadow_img)
        
        # Draw main text
        draw = ImageDraw.Draw(img)
        draw.text((x, y), text, font=font, fill=(*text_color, 255))
        
        return np.array(img)
    
    @staticmethod
    def create_outline_effect(text: str,
                            font_path: str,
                            font_size: int,
                            text_color: Tuple[int, int, int],
                            outline_color: Tuple[int, int, int],
                            outline_width: int = 3,
                            image_size: Tuple[int, int] = (1080, 1920)) -> np.ndarray:
        """
        Create text with outline effect
        Returns RGBA numpy array
        """
        width, height = image_size
        img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Load font
        try:
            font = ImageFont.truetype(font_path, font_size)
        except:
            font = ImageFont.load_default()
        
        # Get text bounding box
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # Center position
        x = (width - text_width) // 2
        y = (height - text_height) // 2
        
        # Draw text with outline
        draw.text((x, y), text, font=font, 
                 fill=(*text_color, 255),
                 stroke_width=outline_width,
                 stroke_fill=(*outline_color, 255))
        
        return np.array(img)
    
    @staticmethod
    def create_gradient_text(text: str,
                           font_path: str,
                           font_size: int,
                           gradient_colors: List[Tuple[int, int, int]],
                           gradient_direction: str = 'vertical',
                           image_size: Tuple[int, int] = (1080, 1920)) -> np.ndarray:
        """
        Create text with gradient fill
        Returns RGBA numpy array
        """
        width, height = image_size
        
        # Create base image
        img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        
        # Load font
        try:
            font = ImageFont.truetype(font_path, font_size)
        except:
            font = ImageFont.load_default()
        
        # Create text mask
        mask = Image.new('L', (width, height), 0)
        mask_draw = ImageDraw.Draw(mask)
        
        # Get text position
        bbox = mask_draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (width - text_width) // 2
        y = (height - text_height) // 2
        
        # Draw text on mask
        mask_draw.text((x, y), text, font=font, fill=255)
        
        # Create gradient
        gradient = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        gradient_draw = ImageDraw.Draw(gradient)
        
        if gradient_direction == 'vertical':
            for i in range(height):
                factor = i / height
                color = TextEffects._interpolate_gradient(gradient_colors, factor)
                gradient_draw.line([(0, i), (width, i)], fill=(*color, 255))
        else:  # horizontal
            for i in range(width):
                factor = i / width
                color = TextEffects._interpolate_gradient(gradient_colors, factor)
                gradient_draw.line([(i, 0), (i, height)], fill=(*color, 255))
        
        # Apply mask to gradient
        gradient.putalpha(mask)
        
        # Composite onto main image
        img = Image.alpha_composite(img, gradient)
        
        return np.array(img)
    
    @staticmethod
    def _interpolate_gradient(colors: List[Tuple[int, int, int]], factor: float) -> Tuple[int, int, int]:
        """Helper function to interpolate between multiple colors"""
        if len(colors) < 2:
            return colors[0] if colors else (255, 255, 255)
        
        # Determine which two colors to interpolate between
        segment_size = 1.0 / (len(colors) - 1)
        segment = int(factor / segment_size)
        segment = min(segment, len(colors) - 2)
        
        local_factor = (factor - segment * segment_size) / segment_size
        
        color1 = colors[segment]
        color2 = colors[segment + 1]
        
        r = int(color1[0] + (color2[0] - color1[0]) * local_factor)
        g = int(color1[1] + (color2[1] - color1[1]) * local_factor)
        b = int(color1[2] + (color2[2] - color1[2]) * local_factor)
        
        return (r, g, b)
    
    @staticmethod
    def create_animated_glow_pulse(text: str,
                                 font_path: str,
                                 font_size: int,
                                 text_color: Tuple[int, int, int],
                                 glow_color: Tuple[int, int, int],
                                 time: float,
                                 pulse_frequency: float = 0.5,
                                 min_intensity: float = 0.3,
                                 max_intensity: float = 1.0,
                                 image_size: Tuple[int, int] = (1080, 1920)) -> np.ndarray:
        """
        Create animated pulsing glow effect based on time
        """
        # Calculate current intensity based on time and frequency
        pulse_phase = (time * pulse_frequency * 2 * np.pi) % (2 * np.pi)
        intensity = min_intensity + (max_intensity - min_intensity) * (np.sin(pulse_phase) + 1) / 2
        
        # Calculate glow radius based on intensity
        base_radius = 10
        glow_radius = int(base_radius + intensity * 10)
        
        return TextEffects.create_glow_effect(
            text, font_path, font_size, text_color, glow_color,
            glow_radius=glow_radius, glow_intensity=intensity,
            image_size=image_size
        )
