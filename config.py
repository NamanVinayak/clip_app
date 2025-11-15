from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    """Application configuration"""

    # API Keys
    runpod_api_key: str = ""
    runpod_endpoint: str = ""
    openrouter_api_key: str = ""
    llm_model: str = "qwen/qwen-2.5-72b-instruct"

    # Application Settings
    max_video_size_mb: int = 2000
    min_clip_duration: int = 15
    max_clip_duration: int = 60
    target_clips: int = 5

    # Paths
    base_dir: Path = Path(__file__).parent
    uploads_dir: Path = base_dir / "uploads"
    outputs_dir: Path = base_dir / "outputs"
    static_dir: Path = base_dir / "static"

    class Config:
        env_file = ".env"
        case_sensitive = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Create necessary directories
        self.uploads_dir.mkdir(exist_ok=True)
        self.outputs_dir.mkdir(exist_ok=True)
        self.static_dir.mkdir(exist_ok=True)


settings = Settings()
