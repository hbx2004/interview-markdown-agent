from __future__ import annotations

import json
from pathlib import Path

from .models import JobRecord


class JobStorage:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.jobs_root = self.root / "jobs"
        self.jobs_root.mkdir(parents=True, exist_ok=True)

    def ensure_job_dir(self, job_id: str) -> Path:
        path = self.jobs_root / job_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def write_job(self, job: JobRecord) -> None:
        job_dir = self.ensure_job_dir(job.job_id)
        target = job_dir / "job.json"
        target.write_text(job.model_dump_json(indent=2), encoding="utf-8")

    def read_job(self, job_id: str) -> JobRecord | None:
        target = self.jobs_root / job_id / "job.json"
        if not target.exists():
            return None
        return JobRecord.model_validate(json.loads(target.read_text(encoding="utf-8")))

