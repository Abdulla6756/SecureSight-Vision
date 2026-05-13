from fastapi import APIRouter, HTTPException

from data_store import load_reports, save_reports

router = APIRouter(prefix="/api")


@router.get("/reports")
def reports():
    """Return saved analysis reports, newest first."""
    return load_reports()


@router.delete("/reports/{job_id}")
def delete_report(job_id: str):
    """Delete one saved report by job id."""
    reports = load_reports()
    remaining = [report for report in reports if report.get("job_id") != job_id]
    if len(remaining) == len(reports):
        raise HTTPException(404, "Report not found")
    save_reports(remaining)
    return {"ok": True, "deleted": job_id}
