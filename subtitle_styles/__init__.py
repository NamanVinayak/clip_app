from pathlib import Path

STYLES_DIR = Path(__file__).parent / "config"
STYLES_JSON = STYLES_DIR / "styles.json"

__all__ = ['STYLES_DIR', 'STYLES_JSON']
