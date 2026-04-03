from __future__ import annotations

from io import BytesIO
from pathlib import Path
from fastapi.testclient import TestClient

from app.dependencies import get_job_manager
from app.main import app
from app.models import JobArtifactPaths, JobRecord, JobStatus


class FakeManager:
    def __init__(self) -> None:
        self.jobs: dict[str, JobRecord] = {}

    def create_job(self, upload):
        suffix = Path(upload.filename).suffix.lower()
        if suffix not in {".mp3", ".wav", ".mp4"}:
            raise ValueError("不支持的文件类型。")
        job = JobRecord(
            job_id="job-1",
            filename=upload.filename,
            status=JobStatus.queued,
            stage="queued",
            progress=0,
            artifacts=JobArtifactPaths(),
        )
        self.jobs[job.job_id] = job
        return job

    def get_job(self, job_id: str):
        return self.jobs.get(job_id)


def create_client(manager: FakeManager) -> TestClient:
    app.dependency_overrides[get_job_manager] = lambda: manager
    return TestClient(app)


def test_create_job_success() -> None:
    client = create_client(FakeManager())
    response = client.post("/jobs", files={"file": ("sample.mp3", BytesIO(b"abc"), "audio/mpeg")})
    assert response.status_code == 200
    assert response.json()["status"] == "queued"
    app.dependency_overrides.clear()


def test_create_job_invalid_file_type() -> None:
    client = create_client(FakeManager())
    response = client.post("/jobs", files={"file": ("sample.txt", BytesIO(b"abc"), "text/plain")})
    assert response.status_code == 400
    app.dependency_overrides.clear()


def test_get_job_status(tmp_path: Path) -> None:
    manager = FakeManager()
    manager.jobs["job-1"] = JobRecord(
        job_id="job-1",
        filename="sample.mp3",
        status=JobStatus.completed,
        message="ok",
        stage="completed",
        progress=100,
        artifacts=JobArtifactPaths(markdown_path=str(tmp_path / "sample.md")),
    )
    Path(manager.jobs["job-1"].artifacts.markdown_path).write_text("# ok", encoding="utf-8")
    client = create_client(manager)
    response = client.get("/jobs/job-1")
    assert response.status_code == 200
    assert response.json()["progress"] == 100
    assert response.json()["stage"] == "completed"
    assert response.json()["result_available"] is True
    app.dependency_overrides.clear()


def test_get_job_result(tmp_path: Path) -> None:
    manager = FakeManager()
    path = tmp_path / "result.md"
    path.write_text("# 面试记录整理稿", encoding="utf-8")
    manager.jobs["job-1"] = JobRecord(
        job_id="job-1",
        filename="sample.mp3",
        status=JobStatus.completed,
        stage="completed",
        progress=100,
        artifacts=JobArtifactPaths(markdown_path=str(path)),
    )
    client = create_client(manager)
    response = client.get("/jobs/job-1/result")
    assert response.status_code == 200
    assert "markdown" in response.json()
    app.dependency_overrides.clear()
