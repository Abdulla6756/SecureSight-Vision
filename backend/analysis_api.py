from fastapi import APIRouter, File, HTTPException, UploadFile, Form

from video_analysis_service import start_analysis_job
from state import JOBS

router = APIRouter(prefix="/api")


@router.post("/analyze/start")
def analyze_start(file: UploadFile = File(...), sample_every: float = Form(1.0)):
    job_id = start_analysis_job(file, float(sample_every))
    return {"job_id": job_id}


@router.get("/analyze/status/{job_id}")
def analyze_status(job_id: str):
    if job_id not in JOBS:
        raise HTTPException(404, "Job not found")

    return {k: v for k, v in JOBS[job_id].items() if k not in {"result", "traceback"}}


@router.get("/analyze/result/{job_id}")
def analyze_result(job_id: str):
    if job_id not in JOBS:
        raise HTTPException(404, "Job not found")

    job = JOBS[job_id]
    if job.get("status") != "done":
        raise HTTPException(400, job.get("error", "Job is not done"))

    return job["result"]
