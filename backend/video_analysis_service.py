import os
import threading
import time
import traceback
import uuid
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import cv2

import face_recognition_engine
from config import UNKNOWN_DIR, UPLOADS_DIR
from face_recognition_engine import best_match_from_index, build_match_index, crop_face, get_face_app, is_embedding_known
from state import JOBS
from data_store import load_ignored_unknown, load_people, load_reports, save_reports
from utils import normalize, save_upload, timecode, unknown_image_url


MAX_SIDE_WORKERS = max(2, min(4, (os.cpu_count() or 2)))
# CPU_FRAME_WORKERS controls optional parallel face extraction for CPU builds.
# GPU stays sequential because one CUDA/ONNX session is safest there.
DEFAULT_CPU_FRAME_WORKERS = max(1, min(4, (os.cpu_count() or 2)))
CPU_BATCH_SIZE = max(2, DEFAULT_CPU_FRAME_WORKERS * 2)
REPORT_LIMIT = 50
UNKNOWN_REPORT_LIMIT = 100


def start_analysis_job(upload_file, sample_every: float) -> str:
    """Save the uploaded video and run analysis on a background worker thread."""
    job_id = str(uuid.uuid4())
    ext = Path(upload_file.filename or "video.mp4").suffix or ".mp4"
    video_path = UPLOADS_DIR / f"{job_id}{ext}"
    save_upload(upload_file, video_path)

    JOBS[job_id] = {
        "job_id": job_id,
        "status": "queued",
        "step": "Queued",
        "progress": 0,
        "elapsed_seconds": 0,
        "analysis_time": "00:00:00",
        "face_device": "--",
    }

    threading.Thread(
        target=analyze_worker,
        args=(job_id, video_path, float(sample_every)),
        daemon=True,
    ).start()
    return job_id


def _update_job(job_id: str, start_time: float, **values):
    """Keep progress responses consistent for the frontend polling loop."""
    elapsed = int(time.perf_counter() - start_time)
    JOBS[job_id].update(
        elapsed_seconds=elapsed,
        analysis_time=timecode(elapsed),
        face_device=face_recognition_engine.FACE_INFO.get("device", "--"),
        **values,
    )


def _video_info(cap, sample_every: float) -> dict[str, Any]:
    """Read video metadata and decide how frequently frames are sampled."""
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    sample_frames = max(1, int(fps * sample_every))
    return {
        "fps": fps,
        "frame_count": frame_count,
        "duration_seconds": frame_count / fps if frame_count else 0,
        "sample_frames": sample_frames,
        "total_samples": max(1, frame_count // sample_frames),
    }


def _cpu_frame_workers() -> int:
    """Return how many CPU frame-analysis workers to use.

    The Windows EXE build forces FACE_PROVIDER=cpu, so the heavy work runs on
    CPU. ONNX Runtime already uses internal CPU threads, but a small number of
    outer frame workers helps with video/frame overhead on many machines. Set
    FACE_CPU_WORKERS=1 to disable this if a low-end laptop becomes overloaded.
    """
    value = os.getenv("FACE_CPU_WORKERS", "auto").strip().lower()
    if value in {"", "auto"}:
        return DEFAULT_CPU_FRAME_WORKERS
    try:
        return max(1, min(8, int(value)))
    except ValueError:
        return DEFAULT_CPU_FRAME_WORKERS


def _face_payload(face) -> dict[str, Any]:
    """Keep only serializable per-face data needed by the sequential report step."""
    return {
        "embedding": normalize(face.embedding),
        "bbox": [float(v) for v in face.bbox],
    }


def _analyze_sample_frame(face_app, frame, frame_index: int, fps: float, sample_every: float):
    """Run face detection/embedding extraction for one sampled frame."""
    video_time = frame_index / fps if fps else frame_index * sample_every
    faces = [_face_payload(face) for face in face_app.get(frame)]
    return {"frame_index": frame_index, "video_time": video_time, "frame": frame, "faces": faces}


def _iter_sample_batches(cap, video_meta: dict[str, Any], sample_every: float, batch_size: int):
    """Yield sampled frames in chronological batches."""
    batch = []
    frame_index = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if frame_index % video_meta["sample_frames"] == 0:
            batch.append((frame_index, frame.copy()))
            if len(batch) >= batch_size:
                yield batch
                batch = []
        frame_index += 1
    if batch:
        yield batch


def _new_detection_event(person: dict[str, Any], score: float, video_time: float, event_no: int) -> dict[str, Any]:
    """Create one internal known-person detection event."""
    person_id = person["id"]
    return {
        "id": person_id,
        "event_id": f"{person_id}-{event_no}",
        "name": person.get("name", ""),
        "employee_id": person.get("employee_id", ""),
        "role": person.get("role", ""),
        "department": person.get("department", ""),
        "first_seen": video_time,
        "last_seen": video_time,
        "confidence": score,
        "device_date": datetime.now().strftime("%Y-%m-%d"),
    }


def _unknown_record(frame, bbox, filename: str, order: int, video_time: float, score: float, embedding):
    """Crop an unknown face and keep its original model embedding.

    The saved crop can be too small/side-facing for a second face-detection pass.
    Storing the embedding that produced the unknown card lets Ignore Future and
    Save to Profile work reliably, even for false positives or profile-angle faces.
    """
    crop_face(frame, bbox, UNKNOWN_DIR / filename)
    return {
        "_order": order,
        "id": f"unknown-{order}",
        "snapshot": filename,
        "snapshot_url": unknown_image_url(filename),
        "device_date": datetime.now().strftime("%Y-%m-%d"),
        "score": round(float(score), 3),
        "embedding": normalize(embedding).astype(float).tolist(),
    }


def _finish_attendance(known_sessions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return report rows without exposing internal video-time/visit columns."""
    attendance = []
    for row in known_sessions:
        attendance.append(
            {
                "id": row.get("id", ""),
                "event_id": row.get("event_id", ""),
                "name": row.get("name", ""),
                "employee_id": row.get("employee_id", ""),
                "role": row.get("role", ""),
                "department": row.get("department", ""),
                "device_date": row.get("device_date") or datetime.now().strftime("%Y-%m-%d"),
                "entry_time": timecode(float(row.get("first_seen", 0))),
                "exit_time": timecode(float(row.get("last_seen", row.get("first_seen", 0)))),
                "confidence": round(float(row["confidence"]), 3),
                "first_seen": row.get("first_seen", 0),
            }
        )
    return sorted(attendance, key=lambda x: x["first_seen"])


def _recommendations(attendance, unknown, repeated_people: int) -> list[str]:
    notes = []
    if unknown:
        notes.append("Review unknown faces and link clear snapshots to existing/new profiles.")
    if repeated_people:
        notes.append("Some people were detected more than once after leaving the frame; review repeated detection events if needed.")
    if not attendance and not unknown:
        notes.append("No faces were detected. Try a clearer video or lower the sample interval.")
    return notes


def _build_report(job_id, video_path, sample_every, video_meta, known_sessions, event_counts, unknown, start_time):
    """Build the final JSON report saved to disk and returned to the frontend."""
    attendance = _finish_attendance(known_sessions)
    repeated_people = sum(1 for count in event_counts.values() if count > 1)
    analysis_seconds = int(time.perf_counter() - start_time)

    return {
        "job_id": job_id,
        "video": video_path.name,
        "face_device": face_recognition_engine.FACE_INFO.get("device", "--"),
        "face_provider": face_recognition_engine.FACE_INFO,
        "device_date": datetime.now().strftime("%Y-%m-%d"),
        "summary": {
            "known_count": len({row["id"] for row in known_sessions}),
            "known_events": len(known_sessions),
            "repeat_visitors": repeated_people,
            "repeated_detections": repeated_people,
            "unknown_count": len(unknown),
            "analysis_seconds": analysis_seconds,
            "analysis_time": timecode(analysis_seconds),
            "sample_every": sample_every,
            "parallel_workers": MAX_SIDE_WORKERS,
            "reentry_gap_seconds": max(5.0, float(sample_every) * 3.0),
            "recommendations": _recommendations(attendance, unknown, repeated_people),
        },
        "attendance": attendance,
        "unknown": unknown[:UNKNOWN_REPORT_LIMIT],
        "created_at": int(time.time()),
    }


def analyze_worker(job_id: str, video_path: Path, sample_every: float):
    """Analyze sampled video frames and save a report.

    GPU mode is sequential to avoid CUDA session conflicts. CPU mode can use a
    small thread pool for frame-level face extraction. Matching, re-entry logic,
    unknown deduplication, and report building still run sequentially in video
    order so the report remains deterministic.
    """
    start_time = time.perf_counter()

    try:
        _update_job(job_id, start_time, status="running", step="Loading face engine", progress=2)
        face_app = get_face_app()
        match_index = build_match_index(load_people())
        ignored_index = build_match_index(load_ignored_unknown())
        current_unknown_embeddings: list[Any] = []

        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise RuntimeError("Could not open uploaded video.")

        video_meta = _video_info(cap, sample_every)
        reentry_gap_seconds = max(5.0, float(sample_every) * 3.0)
        known_sessions: list[dict[str, Any]] = []
        active_by_person: dict[str, dict[str, Any]] = {}
        event_counts: dict[str, int] = {}
        unknown_futures = []
        unknown_order = 0
        sample_index = 0

        is_cpu = face_recognition_engine.FACE_INFO.get("device") == "CPU"
        cpu_workers = _cpu_frame_workers() if is_cpu else 1
        batch_size = CPU_BATCH_SIZE if cpu_workers > 1 else 1

        def process_sample(sample: dict[str, Any], pool: ThreadPoolExecutor):
            """Apply matching/report logic for one already-detected frame."""
            nonlocal unknown_order, sample_index
            video_time = float(sample["video_time"])
            frame = sample["frame"]
            progress = min(95, int((sample_index / video_meta["total_samples"]) * 100))
            _update_job(job_id, start_time, step=f"Scanning {timecode(video_time)}", progress=progress)

            seen_known_this_sample: set[str] = set()
            for face in sample["faces"]:
                embedding = normalize(face["embedding"])
                person, score = best_match_from_index(embedding, match_index)

                if person:
                    person_id = person["id"]
                    if person_id in seen_known_this_sample:
                        continue
                    seen_known_this_sample.add(person_id)

                    active = active_by_person.get(person_id)
                    if active is None or (video_time - float(active.get("last_seen", 0))) > reentry_gap_seconds:
                        event_counts[person_id] = event_counts.get(person_id, 0) + 1
                        active = _new_detection_event(person, score, video_time, event_counts[person_id])
                        known_sessions.append(active)
                        active_by_person[person_id] = active
                    else:
                        active["last_seen"] = video_time
                        active["confidence"] = max(float(active["confidence"]), float(score))
                else:
                    ignored, _ignored_score = best_match_from_index(embedding, ignored_index, threshold=0.34)
                    if ignored:
                        continue

                    # Avoid showing the same unknown/false face over and over in one report.
                    if is_embedding_known(embedding, current_unknown_embeddings, threshold=0.56):
                        continue
                    current_unknown_embeddings.append(normalize(embedding).astype(float).tolist())

                    unknown_order += 1
                    filename = f"unknown-{job_id[:8]}-{unknown_order}.jpg"
                    unknown_futures.append(
                        pool.submit(_unknown_record, frame.copy(), face["bbox"], filename, unknown_order, video_time, score, embedding)
                    )

            sample_index += 1

        with ThreadPoolExecutor(max_workers=MAX_SIDE_WORKERS) as side_pool:
            if cpu_workers > 1:
                _update_job(
                    job_id,
                    start_time,
                    step=f"CPU parallel scan starting ({cpu_workers} workers)",
                    progress=3,
                )
                with ThreadPoolExecutor(max_workers=cpu_workers) as face_pool:
                    for batch in _iter_sample_batches(cap, video_meta, sample_every, batch_size):
                        futures = [
                            face_pool.submit(_analyze_sample_frame, face_app, frame, idx, video_meta["fps"], sample_every)
                            for idx, frame in batch
                        ]
                        samples = [future.result() for future in futures]
                        samples.sort(key=lambda item: item["frame_index"])
                        for sample in samples:
                            process_sample(sample, side_pool)
            else:
                for batch in _iter_sample_batches(cap, video_meta, sample_every, 1):
                    idx, frame = batch[0]
                    sample = _analyze_sample_frame(face_app, frame, idx, video_meta["fps"], sample_every)
                    process_sample(sample, side_pool)

            cap.release()
            unknown = [future.result() for future in as_completed(unknown_futures)]
            unknown = sorted(unknown, key=lambda item: item.pop("_order"))

        result = _build_report(job_id, video_path, sample_every, video_meta, known_sessions, event_counts, unknown, start_time)
        result["summary"]["cpu_frame_workers"] = cpu_workers if is_cpu else 0
        reports = load_reports()
        reports.insert(0, result)
        save_reports(reports[:REPORT_LIMIT])

        _update_job(job_id, start_time, status="done", step="Done", progress=100, result=result)

    except Exception as exc:
        _update_job(
            job_id,
            start_time,
            status="error",
            step="Error",
            progress=100,
            error=str(exc),
            traceback=traceback.format_exc(),
        )
        print(JOBS[job_id]["traceback"])

