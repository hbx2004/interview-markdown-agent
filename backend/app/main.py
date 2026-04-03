from __future__ import annotations

from pathlib import Path
import logging

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .dependencies import get_job_manager
from .models import CreateJobResponse, JobResultResponse, JobStatusResponse
from .services.job_manager import JobManager

settings = get_settings()
logger = logging.getLogger("uvicorn.error")
app = FastAPI(title=settings.app_name)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def log_runtime_settings() -> None:
    logger.info(
        "Interview backend ready: data_dir=%s whisper_device=%s compute_type=%s model=%s",
        settings.data_dir.resolve(),
        settings.whisper_device,
        settings.whisper_compute_type,
        settings.whisper_model_size,
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/jobs", response_model=CreateJobResponse)
def create_job(
    file: UploadFile = File(...),
    manager: JobManager = Depends(get_job_manager),
) -> CreateJobResponse:
    try:
        job = manager.create_job(file)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return CreateJobResponse(job_id=job.job_id, status=job.status)


@app.get("/jobs/{job_id}", response_model=JobStatusResponse)
def get_job_status(job_id: str, manager: JobManager = Depends(get_job_manager)) -> JobStatusResponse:
    job = manager.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="任务不存在。")
    return JobStatusResponse(
        job_id=job.job_id,
        status=job.status,
        message=job.message,
        stage=job.stage,
        progress=job.progress,
        result_available=bool(job.artifacts.markdown_path and Path(job.artifacts.markdown_path).exists()),
    )


@app.get("/jobs/{job_id}/result", response_model=JobResultResponse)
def get_job_result(job_id: str, manager: JobManager = Depends(get_job_manager)) -> JobResultResponse:
    job = manager.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="任务不存在。")
    if not job.artifacts.markdown_path:
        raise HTTPException(status_code=409, detail="任务尚未生成结果。")
    result_path = Path(job.artifacts.markdown_path)
    if not result_path.exists():
        raise HTTPException(status_code=409, detail="结果文件不存在。")
    return JobResultResponse(markdown=result_path.read_text(encoding="utf-8"), filename=result_path.name)
