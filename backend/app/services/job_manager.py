from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import UploadFile

from ..config import Settings
from ..models import JobArtifactPaths, JobRecord, JobStatus
from ..storage import JobStorage
from .audio import AudioProcessor
from .formatter import Formatter
from .transcription import TranscriptionService


class JobManager:
    def __init__(
        self,
        settings: Settings,
        storage: JobStorage,
        audio_processor: AudioProcessor,
        transcription_service: TranscriptionService,
        formatter: Formatter,
    ) -> None:
        self.settings = settings
        self.storage = storage
        self.audio_processor = audio_processor
        self.transcription_service = transcription_service
        self.formatter = formatter

    def create_job(self, upload: UploadFile) -> JobRecord:
        suffix = Path(upload.filename or "").suffix.lower()
        if suffix not in self.settings.allowed_extensions:
            raise ValueError("不支持的文件类型。")

        job_id = uuid.uuid4().hex
        job_dir = self.storage.ensure_job_dir(job_id)
        upload_path = job_dir / f"source{suffix}"

        size = 0
        with upload_path.open("wb") as sink:
            while True:
                chunk = upload.file.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > self.settings.max_upload_size_mb * 1024 * 1024:
                    raise ValueError("上传文件过大。")
                sink.write(chunk)

        job = JobRecord(
            job_id=job_id,
            filename=upload.filename or f"{job_id}{suffix}",
            status=JobStatus.queued,
            artifacts=JobArtifactPaths(upload_path=str(upload_path)),
        )
        self.storage.write_job(job)
        threading.Thread(target=self._run_job, args=(job_id,), daemon=True).start()
        return job

    def get_job(self, job_id: str) -> JobRecord | None:
        return self.storage.read_job(job_id)

    def _update_job(self, job: JobRecord, *, status: JobStatus | None = None, message: str | None = None) -> JobRecord:
        return self._set_job_state(job, status=status, message=message)

    def _set_job_state(
        self,
        job: JobRecord,
        *,
        status: JobStatus | None = None,
        message: str | None = None,
        stage: str | None = None,
        progress: int | None = None,
    ) -> JobRecord:
        if status is not None:
            job.status = status
        job.message = message
        if stage is not None:
            job.stage = stage
        if progress is not None:
            job.progress = max(0, min(100, progress))
        job.updated_at = datetime.now(timezone.utc)
        self.storage.write_job(job)
        return job

    def _run_job(self, job_id: str) -> None:
        job = self.storage.read_job(job_id)
        if job is None:
            return

        try:
            self._set_job_state(
                job,
                status=JobStatus.processing,
                stage="preparing_audio",
                progress=15,
                message="正在提取音频并准备转写。",
            )
            job_dir = self.storage.ensure_job_dir(job_id)
            source_path = Path(job.artifacts.upload_path or "")
            audio_path = self.audio_processor.normalize_to_wav(source_path, job_dir / "normalized.wav")
            job.artifacts.audio_path = str(audio_path)
            self.storage.write_job(job)

            self._set_job_state(
                job,
                status=JobStatus.processing,
                stage="transcribing",
                progress=20,
                message="正在进行语音转写，这一步通常最耗时。",
            )
            last_reported_progress = job.progress

            def handle_transcription_progress(ratio: float) -> None:
                nonlocal last_reported_progress
                mapped_progress = 20 + int(ratio * 60)
                if mapped_progress <= last_reported_progress:
                    return
                last_reported_progress = mapped_progress
                self._set_job_state(
                    job,
                    status=JobStatus.processing,
                    stage="transcribing",
                    progress=mapped_progress,
                    message=f"正在进行语音转写，已完成约 {mapped_progress}%。",
                )

            segments = self.transcription_service.transcribe(
                audio_path,
                progress_callback=handle_transcription_progress,
            )
            transcript_path = job_dir / "transcript.txt"
            transcript_text = "\n".join(segment.text for segment in segments)
            transcript_path.write_text(transcript_text, encoding="utf-8")
            job.artifacts.transcript_path = str(transcript_path)
            job.transcript_segments = segments
            self.storage.write_job(job)

            self._set_job_state(
                job,
                status=JobStatus.processing,
                stage="formatting_markdown",
                progress=85,
                message="正在整理角色、纠错并生成 Markdown。",
            )
            markdown = self.formatter.format(segments)
            markdown_path = job_dir / "interview.md"
            markdown_path.write_text(markdown, encoding="utf-8")
            job.artifacts.markdown_path = str(markdown_path)
            self._set_job_state(
                job,
                status=JobStatus.completed,
                stage="completed",
                progress=100,
                message="处理完成，可下载 Markdown。",
            )
        except Exception as exc:
            error_log_path = self.storage.ensure_job_dir(job_id) / "error.log"
            error_log_path.write_text(str(exc), encoding="utf-8")
            job.artifacts.error_log_path = str(error_log_path)
            self._set_job_state(
                job,
                status=JobStatus.failed,
                stage="failed",
                progress=100,
                message=str(exc),
            )
