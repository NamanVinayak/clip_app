import json
from pathlib import Path
from typing import Dict, List
from utils.helpers import setup_logger


class HindiTransliterator:
    """
    Transliterate Hindi Devanagari text to Roman script for subtitles

    Uses indic-transliteration library for rule-based transliteration.
    This converts Hindi text like "मैं जा रहा हूं" to "main jaa rahaa hoon"
    (not translation, but phonetic representation in Latin script).

    Note: This uses ITRANS romanization scheme which is widely used for
    Indic scripts.
    """

    def __init__(self, job_folder: Path):
        """
        Initialize transliterator

        Args:
            job_folder: Path to job folder for logging
        """
        self.job_folder = job_folder
        self.logger = setup_logger(
            "Transliterator",
            job_folder / "processing.log"
        )

        # Initialize indic-transliteration library
        try:
            from indic_transliteration import sanscript
            from indic_transliteration.sanscript import transliterate
            self.sanscript = sanscript
            self.transliterate = transliterate
            self.logger.info("indic-transliteration library loaded successfully")
        except ImportError as e:
            self.logger.error(
                "indic-transliteration not installed. "
                "Install with: pip install indic-transliteration"
            )
            raise ImportError(
                "indic-transliteration package required. "
                "Run: pip install indic-transliteration"
            ) from e
        except Exception as e:
            self.logger.error(f"Failed to initialize transliterator: {e}")
            raise

    def transliterate_transcript(self, transcript_data: Dict) -> Dict:
        """
        Transliterate all segments and words in transcript from Devanagari to Roman

        Takes the transcript data with word-level timestamps and adds romanized
        versions of all text, preserving the original structure.

        Args:
            transcript_data: Dict with 'segments' containing Hindi text and words

        Returns:
            Dict with added 'text_roman' fields for segments and words

        Example:
            Input segment: {"text": "मैं जा रहा हूं", "words": [...]}
            Output segment: {
                "text": "मैं जा रहा हूं",
                "text_roman": "main ja raha hoon",
                "words": [...]
            }
        """
        self.logger.info("Starting transcript transliteration...")

        # Create a copy to avoid modifying original
        romanized_data = {
            'text': transcript_data.get('text', ''),
            'text_roman': '',
            'segments': [],
            'language': transcript_data.get('language', 'hi')
        }

        # Transliterate full text
        if romanized_data['text']:
            romanized_data['text_roman'] = self._transliterate_text(
                romanized_data['text']
            )

        # Process each segment
        total_words = 0
        for segment in transcript_data.get('segments', []):
            romanized_segment = segment.copy()

            # Transliterate segment text
            if 'text' in segment:
                romanized_segment['text_roman'] = self._transliterate_text(
                    segment['text']
                )

            # Transliterate each word
            if 'words' in segment:
                romanized_words = []
                for word in segment['words']:
                    romanized_word = word.copy()

                    # Get word text (handle both 'word' and 'text' keys)
                    word_text = word.get('word', word.get('text', ''))

                    if word_text:
                        romanized_word['text_roman'] = self._transliterate_text(
                            word_text
                        )
                        total_words += 1

                    romanized_words.append(romanized_word)

                romanized_segment['words'] = romanized_words

            romanized_data['segments'].append(romanized_segment)

        self.logger.info(
            f"Transliterated {len(romanized_data['segments'])} segments "
            f"and {total_words} words"
        )

        # Save romanized transcript
        output_path = self.job_folder / "transcript_romanized.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(romanized_data, f, ensure_ascii=False, indent=2)

        self.logger.info(f"Romanized transcript saved to {output_path}")

        return romanized_data

    def _transliterate_text(self, text: str) -> str:
        """
        Transliterate a single text string from Hindi to Roman script

        Args:
            text: Hindi text in Devanagari script

        Returns:
            Romanized text using ITRANS scheme

        Example:
            Input: "नमस्ते"
            Output: "namaste"
        """
        if not text or not text.strip():
            return ""

        try:
            # Use ITRANS scheme for romanization
            # ITRANS is a widely-used ASCII transliteration scheme for Indic scripts
            romanized = self.transliterate(
                text,
                self.sanscript.DEVANAGARI,
                self.sanscript.ITRANS
            )

            self.logger.debug(f"Transliterated: '{text}' → '{romanized}'")
            return romanized

        except Exception as e:
            self.logger.error(f"Transliteration failed for '{text}': {e}")
            # Return original text as fallback
            return text

    def transliterate_word_list(self, words: List[Dict]) -> List[Dict]:
        """
        Transliterate a list of words with timestamps

        Useful for processing word-level data separately.

        Args:
            words: List of word dicts with 'text', 'start', 'end'

        Returns:
            List of words with added 'text_roman' field
        """
        romanized_words = []

        for word in words:
            romanized_word = word.copy()
            word_text = word.get('text', word.get('word', ''))

            if word_text:
                romanized_word['text_roman'] = self._transliterate_text(word_text)

            romanized_words.append(romanized_word)

        return romanized_words


class FallbackTransliterator:
    """
    Fallback transliterator using indic-transliteration library

    This is a lighter alternative if ai4bharat-transliteration is not available.
    Uses rule-based transliteration instead of ML model.

    To use this, install: pip install indic-transliteration
    """

    def __init__(self, job_folder: Path):
        self.job_folder = job_folder
        self.logger = setup_logger(
            "FallbackTransliterator",
            job_folder / "processing.log"
        )

        try:
            from indic_transliteration import sanscript
            from indic_transliteration.sanscript import transliterate
            self.sanscript = sanscript
            self.transliterate = transliterate
            self.logger.info("indic-transliteration loaded successfully")
        except ImportError as e:
            self.logger.error("indic-transliteration not installed")
            raise ImportError(
                "indic-transliteration package required. "
                "Run: pip install indic-transliteration"
            ) from e

    def transliterate_transcript(self, transcript_data: Dict) -> Dict:
        """Same interface as HindiTransliterator"""
        self.logger.info("Starting transcript transliteration (fallback method)...")

        romanized_data = {
            'text': transcript_data.get('text', ''),
            'text_roman': '',
            'segments': [],
            'language': transcript_data.get('language', 'hi')
        }

        # Transliterate full text
        if romanized_data['text']:
            romanized_data['text_roman'] = self._transliterate_text(
                romanized_data['text']
            )

        # Process segments and words
        for segment in transcript_data.get('segments', []):
            romanized_segment = segment.copy()

            if 'text' in segment:
                romanized_segment['text_roman'] = self._transliterate_text(
                    segment['text']
                )

            if 'words' in segment:
                romanized_words = []
                for word in segment['words']:
                    romanized_word = word.copy()
                    word_text = word.get('word', word.get('text', ''))

                    if word_text:
                        romanized_word['text_roman'] = self._transliterate_text(
                            word_text
                        )

                    romanized_words.append(romanized_word)

                romanized_segment['words'] = romanized_words

            romanized_data['segments'].append(romanized_segment)

        # Save romanized transcript
        output_path = self.job_folder / "transcript_romanized.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(romanized_data, f, ensure_ascii=False, indent=2)

        self.logger.info(f"Romanized transcript saved to {output_path}")

        return romanized_data

    def _transliterate_text(self, text: str) -> str:
        """Transliterate using rule-based method"""
        if not text or not text.strip():
            return ""

        try:
            # Use ITRANS scheme for romanization
            romanized = self.transliterate(
                text,
                self.sanscript.DEVANAGARI,
                self.sanscript.ITRANS
            )
            return romanized
        except Exception as e:
            self.logger.error(f"Transliteration failed for '{text}': {e}")
            return text
