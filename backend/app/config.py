from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field


class Settings(BaseModel):
    app_name: str = "Interview Markdown Converter"
    data_dir: Path = Field(default_factory=lambda: Path(__file__).resolve().parents[1] / "data")
    max_upload_size_mb: int = 500
    whisper_model_size: str = "small"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"
    llm_provider: str = "mock"
    llm_model: str = "gpt-4o-mini"
    llm_max_tokens: int = 8192
    llm_chunk_target_chars: int = 6000
    openai_api_key: str | None = None
    deepseek_api_key: str | None = None
    deepseek_base_url: str = "https://api.deepseek.com"
    allowed_extensions: set[str] = {
        ".mp3",
        ".wav",
        ".m4a",
        ".aac",
        ".flac",
        ".ogg",
        ".mp4",
        ".mov",
        ".mkv",
        ".webm",
    }


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    data_dir_env = os.getenv("INTERVIEW_AGENT_DATA_DIR")
    default_dir = Path(data_dir_env).expanduser() if data_dir_env else Path(__file__).resolve().parents[1] / "data"
    return Settings(
        data_dir=default_dir,
        max_upload_size_mb=int(os.getenv("MAX_UPLOAD_SIZE_MB", "500")),
        whisper_model_size=os.getenv("WHISPER_MODEL_SIZE", "small"),
        whisper_device=os.getenv("WHISPER_DEVICE", "cpu"),
        whisper_compute_type=os.getenv("WHISPER_COMPUTE_TYPE", "int8"),
        llm_provider=os.getenv("LLM_PROVIDER", "mock"),
        llm_model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
        llm_max_tokens=int(os.getenv("LLM_MAX_TOKENS", "8192")),
        llm_chunk_target_chars=int(os.getenv("LLM_CHUNK_TARGET_CHARS", "6000")),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        deepseek_api_key=os.getenv("DEEPSEEK_API_KEY"),
        deepseek_base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
    )
