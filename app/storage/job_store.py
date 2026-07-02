import json
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
from uuid import uuid4

from app.api.schemas.responses import FormExtractionResponse
from app.domain.statuses import JobStatus


@dataclass
class JobRecord:
    job_id: str
    status: JobStatus
    progress_percent: int = 0
    progress_message: str | None = None
    result: FormExtractionResponse | None = None
    error: str | None = None


class JobStore(Protocol):
    def create(self) -> JobRecord:
        """Create a queued job."""

    def get(self, job_id: str) -> JobRecord | None:
        """Return a job by id."""

    def mark_running(self, job_id: str) -> None:
        """Mark a job as running."""

    def update_progress(self, job_id: str, percent: int, message: str | None = None) -> None:
        """Update job progress while it is running."""

    def mark_completed(self, job_id: str, result: FormExtractionResponse) -> None:
        """Mark a job as completed."""

    def mark_failed(self, job_id: str, error: str) -> None:
        """Mark a job as failed."""


class InMemoryJobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, JobRecord] = {}

    def create(self) -> JobRecord:
        job = JobRecord(job_id=f"job_{uuid4().hex}", status=JobStatus.QUEUED)
        self._jobs[job.job_id] = job
        return job

    def get(self, job_id: str) -> JobRecord | None:
        return self._jobs.get(job_id)

    def mark_running(self, job_id: str) -> None:
        self._update(
            job_id,
            status=JobStatus.RUNNING,
            progress_percent=1,
            progress_message="Job started.",
        )

    def update_progress(self, job_id: str, percent: int, message: str | None = None) -> None:
        job = self._jobs[job_id]
        job.progress_percent = _clamp_progress(percent)
        job.progress_message = message

    def mark_completed(self, job_id: str, result: FormExtractionResponse) -> None:
        self._update(
            job_id,
            status=result.status,
            result=result,
            progress_percent=100,
            progress_message="Job completed.",
        )

    def mark_failed(self, job_id: str, error: str) -> None:
        self._update(job_id, status=JobStatus.FAILED, error=error, progress_message="Job failed.")

    def _update(
        self,
        job_id: str,
        status: JobStatus,
        result: FormExtractionResponse | None = None,
        error: str | None = None,
        progress_percent: int | None = None,
        progress_message: str | None = None,
    ) -> None:
        job = self._jobs[job_id]
        job.status = status
        job.result = result
        job.error = error
        if progress_percent is not None:
            job.progress_percent = _clamp_progress(progress_percent)
        if progress_message is not None:
            job.progress_message = progress_message


class FileSystemJobStore:
    def __init__(self, storage_dir: Path) -> None:
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def create(self) -> JobRecord:
        job = JobRecord(job_id=f"job_{uuid4().hex}", status=JobStatus.QUEUED)
        self._write(job)
        return job

    def get(self, job_id: str) -> JobRecord | None:
        path = self._path_for(job_id)
        if not path.exists():
            return None

        data = json.loads(path.read_text(encoding="utf-8"))
        result = data.get("result")
        return JobRecord(
            job_id=data["jobId"],
            status=JobStatus(data["status"]),
            progress_percent=data.get("progressPercent", 0),
            progress_message=data.get("progressMessage"),
            result=FormExtractionResponse.model_validate(result) if result else None,
            error=data.get("error"),
        )

    def mark_running(self, job_id: str) -> None:
        self._update(
            job_id,
            status=JobStatus.RUNNING,
            progress_percent=1,
            progress_message="Job started.",
        )

    def update_progress(self, job_id: str, percent: int, message: str | None = None) -> None:
        existing = self.get(job_id)
        if existing is None:
            return
        existing.progress_percent = _clamp_progress(percent)
        existing.progress_message = message
        self._write(existing)

    def mark_completed(self, job_id: str, result: FormExtractionResponse) -> None:
        self._update(
            job_id,
            status=result.status,
            result=result,
            progress_percent=100,
            progress_message="Job completed.",
        )

    def mark_failed(self, job_id: str, error: str) -> None:
        self._update(job_id, status=JobStatus.FAILED, error=error, progress_message="Job failed.")

    def _update(
        self,
        job_id: str,
        status: JobStatus,
        result: FormExtractionResponse | None = None,
        error: str | None = None,
        progress_percent: int | None = None,
        progress_message: str | None = None,
    ) -> None:
        existing = self.get(job_id)
        if existing is None:
            existing = JobRecord(job_id=job_id, status=status)

        existing.status = status
        existing.result = result
        existing.error = error
        if progress_percent is not None:
            existing.progress_percent = _clamp_progress(progress_percent)
        if progress_message is not None:
            existing.progress_message = progress_message
        self._write(existing)

    def _write(self, job: JobRecord) -> None:
        payload = {
            "jobId": job.job_id,
            "status": job.status,
            "progressPercent": job.progress_percent,
            "progressMessage": job.progress_message,
            "result": job.result.model_dump(mode="json", by_alias=True) if job.result else None,
            "error": job.error,
        }
        path = self._path_for(job.job_id)
        tmp_path = path.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp_path.replace(path)

    def _path_for(self, job_id: str) -> Path:
        return self.storage_dir / f"{job_id}.json"


def _clamp_progress(percent: int) -> int:
    return max(0, min(percent, 100))
