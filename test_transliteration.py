#!/usr/bin/env python3
"""
Quick test script for Hindi transliteration module
"""

from pathlib import Path
import json
import tempfile
from modules.transliterator import HindiTransliterator


def test_basic_transliteration():
    """Test basic Hindi to Roman transliteration"""
    print("Testing Hindi Transliteration Module")
    print("=" * 50)

    # Create temporary job folder
    with tempfile.TemporaryDirectory() as tmpdir:
        job_folder = Path(tmpdir)

        # Initialize transliterator
        try:
            translator = HindiTransliterator(job_folder)
            print("✓ Transliterator initialized successfully")
        except Exception as e:
            print(f"✗ Failed to initialize: {e}")
            return False

        # Test cases: Hindi text → Expected romanization (approximate)
        test_cases = [
            ("नमस्ते", "namaste"),
            ("मैं जा रहा हूं", "main"),  # Should contain 'main'
            ("यह बहुत अच्छा है", "yah"),  # Should contain 'yah'
            ("धन्यवाद", "dhanyavaad"),
            ("आप कैसे हैं", "aap"),
        ]

        print("\nTest Cases:")
        print("-" * 50)

        passed = 0
        for hindi, expected_contains in test_cases:
            try:
                result = translator._transliterate_text(hindi)
                contains_expected = expected_contains.lower() in result.lower()

                status = "✓" if contains_expected else "?"
                print(f"{status} '{hindi}' → '{result}'")

                if contains_expected:
                    passed += 1
            except Exception as e:
                print(f"✗ '{hindi}' → ERROR: {e}")

        print("-" * 50)
        print(f"Results: {passed}/{len(test_cases)} tests passed")

        # Test full transcript transliteration
        print("\nTesting transcript transliteration...")
        mock_transcript = {
            "text": "नमस्ते दोस्तों",
            "language": "hi",
            "segments": [
                {
                    "start": 0.0,
                    "end": 5.0,
                    "text": "नमस्ते दोस्तों",
                    "words": [
                        {"text": "नमस्ते", "start": 0.0, "end": 1.5},
                        {"text": "दोस्तों", "start": 1.5, "end": 3.0}
                    ]
                }
            ]
        }

        try:
            result = translator.transliterate_transcript(mock_transcript)
            print(f"✓ Full transcript transliterated")
            print(f"  Original: {result['segments'][0]['text']}")
            print(f"  Romanized: {result['segments'][0]['text_roman']}")

            # Check if romanized file was created
            romanized_file = job_folder / "transcript_romanized.json"
            if romanized_file.exists():
                print(f"✓ Romanized transcript saved to file")

                # Display content
                with open(romanized_file, 'r', encoding='utf-8') as f:
                    saved_data = json.load(f)
                    print(f"\nSaved romanized words:")
                    for word in saved_data['segments'][0]['words']:
                        print(f"  - {word.get('text', '')} → {word.get('text_roman', '')}")
            else:
                print(f"✗ Romanized file not created")

        except Exception as e:
            print(f"✗ Transcript transliteration failed: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 50)
    print("Test complete!")


if __name__ == "__main__":
    test_basic_transliteration()
