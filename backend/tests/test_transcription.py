from __future__ import annotations

from pathlib import Path

from app.config import Settings
from app.services.formatter import MockFormatter, _append_summary_sections, _chunk_segments, _merge_markdown_bodies
from app.services.transcription import TranscriptionService


class FakeSegment:
    def __init__(self, start: float, end: float, text: str) -> None:
        self.start = start
        self.end = end
        self.text = text


def test_transcription_falls_back_to_cpu_on_cuda_error(tmp_path: Path) -> None:
    settings = Settings(whisper_device="cuda", whisper_compute_type="float16")
    service = TranscriptionService(settings)
    calls: list[tuple[str, str]] = []

    class FakeModel:
        def __init__(self, device: str) -> None:
            self.device = device

        def transcribe(self, _audio_path: str, vad_filter: bool, language: str):
            assert vad_filter is True
            assert language == "zh"
            if self.device == "cuda":
                raise RuntimeError("Library cublas64_12.dll is not found or cannot be loaded")
            return [FakeSegment(0.0, 1.0, "你好")], None

    def fake_create_model(*, device: str, compute_type: str):
        calls.append((device, compute_type))
        return FakeModel(device)

    service._create_model = fake_create_model  # type: ignore[method-assign]
    result = service.transcribe(tmp_path / "sample.wav")

    assert [(segment.start, segment.end, segment.text) for segment in result] == [(0.0, 1.0, "你好")]
    assert calls == [("cuda", "float16"), ("cpu", "int8")]


def test_transcription_reports_segment_progress(tmp_path: Path) -> None:
    settings = Settings(whisper_device="cpu", whisper_compute_type="int8")
    service = TranscriptionService(settings)
    reported: list[float] = []

    class FakeInfo:
        duration = 10.0

    class FakeModel:
        def transcribe(self, _audio_path: str, vad_filter: bool, language: str):
            assert vad_filter is True
            assert language == "zh"
            return [
                FakeSegment(0.0, 2.0, "第一句"),
                FakeSegment(2.0, 7.0, "第二句"),
                FakeSegment(7.0, 10.0, "第三句"),
            ], FakeInfo()

    service._model = FakeModel()
    result = service.transcribe(tmp_path / "sample.wav", progress_callback=reported.append)

    assert [segment.text for segment in result] == ["第一句", "第二句", "第三句"]
    assert reported == [0.2, 0.7, 1.0]


def test_formatter_chunks_segments_by_target_chars() -> None:
    segments = [
        FakeSegment(0.0, 1.0, "a" * 10),
        FakeSegment(1.0, 2.0, "b" * 10),
        FakeSegment(2.0, 3.0, "c" * 10),
    ]

    chunks = _chunk_segments(segments, 25)

    assert len(chunks) == 3
    assert [chunk[0].text for chunk in chunks] == ["a" * 10, "b" * 10, "c" * 10]


def test_formatter_merges_chunk_markdown_without_duplicate_summary() -> None:
    markdowns = [
        "# 面试记录（整理版）\n\n------\n\n## 一、C++\n\n### 面试官\nA\n\n### 候选人\n\nB\n\n## 面试总结\n- x\n\n## 可提升点\n- y",
        "# 面试记录（整理版）\n\n------\n\n## 二、项目\n\n### 面试官\nC",
    ]

    merged = _merge_markdown_bodies(markdowns)

    assert merged.startswith("# 面试记录（整理版）")
    assert "## 一、C++" in merged
    assert "## 二、项目" in merged
    assert "### 面试官" in merged
    assert "## 面试总结" not in merged


def test_append_summary_sections_appends_summary_and_improvements() -> None:
    markdown = "# 面试记录（整理版）\n\n------\n\n## 一、项目经历"
    summary = "## 面试总结\n- 总结一\n\n## 可提升点\n- 提升一"

    result = _append_summary_sections(markdown, summary)

    assert result.startswith("# 面试记录（整理版）")
    assert "## 面试总结" in result
    assert "## 可提升点" in result


def test_mock_formatter_outputs_summary_sections() -> None:
    formatter = MockFormatter()
    segments = [
        FakeSegment(0.0, 1.0, "请你先做一下自我介绍"),
        FakeSegment(1.0, 2.0, "我主要做过 Java 后端开发和两个项目"),
        FakeSegment(2.0, 3.0, "你项目里 Redis 是怎么用的"),
        FakeSegment(3.0, 4.0, "我们主要拿 Redis 做缓存和热点数据存储"),
    ]

    markdown = formatter.format(segments)

    assert markdown.startswith("# 面试记录（整理版）")
    assert "## 面试总结" in markdown
    assert "## 可提升点" in markdown
    assert "### 面试官" in markdown
    assert "### 候选人" in markdown
