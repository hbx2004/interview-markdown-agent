from __future__ import annotations

from pathlib import Path
from typing import Any
from collections.abc import Callable

from ..config import Settings
from ..models import TranscriptSegment


class TranscriptionService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._model: Any | None = None

    def _get_model(self) -> Any:
        if self._model is None:
            self._model = self._create_model(
                device=self.settings.whisper_device,
                compute_type=self.settings.whisper_compute_type,
            )
        return self._model

    def transcribe(
        self,
        audio_path: Path,
        progress_callback: Callable[[float], None] | None = None,
    ) -> list[TranscriptSegment]:
        try:
            model = self._get_model()
            raw_segments, info = model.transcribe(str(audio_path), vad_filter=True, language="zh")
        except Exception as exc:
            if self.settings.whisper_device == "cpu":
                raise

            message = str(exc).lower()
            gpu_markers = ("cublas", "cuda", "cudnn", "cannot be loaded")
            if not any(marker in message for marker in gpu_markers):
                raise

            self._model = self._create_model(device="cpu", compute_type="int8")
            raw_segments, info = self._model.transcribe(str(audio_path), vad_filter=True, language="zh")

        duration = float(getattr(info, "duration", 0.0) or 0.0)
        transcript_segments: list[TranscriptSegment] = []
        last_progress = -1.0

        for segment in raw_segments:
            text = segment.text.strip()
            if not text:
                continue

            transcript_segments.append(
                TranscriptSegment(start=segment.start, end=segment.end, text=text)
            )

            if progress_callback and duration > 0:
                current_progress = min(max(segment.end / duration, 0.0), 1.0)
                if current_progress > last_progress:
                    progress_callback(current_progress)
                    last_progress = current_progress

        return transcript_segments

    def _create_model(self, *, device: str, compute_type: str) -> Any:
        from faster_whisper import WhisperModel

        return WhisperModel(
            self.settings.whisper_model_size,
            device=device,
            compute_type=compute_type,
        )
