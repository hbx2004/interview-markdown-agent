from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    queued = "queued"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class TranscriptSegment(BaseModel):
    start: float
    end: float
    text: str


class JobArtifactPaths(BaseModel):
    upload_path: str | None = None
    audio_path: str | None = None
    transcript_path: str | None = None
    markdown_path: str | None = None
    error_log_path: str | None = None


class JobRecord(BaseModel):
    job_id: str
    filename: str
    status: JobStatus
    message: str | None = None
    stage: str = "queued"
    progress: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    artifacts: JobArtifactPaths = Field(default_factory=JobArtifactPaths)
    transcript_segments: list[TranscriptSegment] = Field(default_factory=list)

    def job_dir(self, root: Path) -> Path:
        return root / self.job_id


class CreateJobResponse(BaseModel):
    job_id: str
    status: JobStatus


class JobStatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    message: str | None = None
    stage: str
    progress: int
    result_available: bool


class JobResultResponse(BaseModel):
    markdown: str
    filename: str
