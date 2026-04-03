from __future__ import annotations

from functools import lru_cache

from .config import Settings, get_settings
from .services.audio import AudioProcessor
from .services.formatter import build_formatter
from .services.job_manager import JobManager
from .services.transcription import TranscriptionService
from .storage import JobStorage


@lru_cache(maxsize=1)
def get_job_manager() -> JobManager:
    settings: Settings = get_settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    storage = JobStorage(settings.data_dir)
    return JobManager(
        settings=settings,
        storage=storage,
        audio_processor=AudioProcessor(),
        transcription_service=TranscriptionService(settings),
        formatter=build_formatter(settings),
    )
