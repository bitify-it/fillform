from app.domain.statuses import JobStatus
from app.storage.job_store import FileSystemJobStore


def test_file_system_job_store_reads_job_created_by_another_instance(tmp_path) -> None:
    first_store = FileSystemJobStore(tmp_path)
    job = first_store.create()
    first_store.mark_running(job.job_id)
    first_store.update_progress(job.job_id, 42, "Processing fields.")

    second_store = FileSystemJobStore(tmp_path)
    reloaded_job = second_store.get(job.job_id)

    assert reloaded_job is not None
    assert reloaded_job.job_id == job.job_id
    assert reloaded_job.status == JobStatus.RUNNING
    assert reloaded_job.progress_percent == 42
    assert reloaded_job.progress_message == "Processing fields."


def test_file_system_job_store_clamps_progress(tmp_path) -> None:
    store = FileSystemJobStore(tmp_path)
    job = store.create()

    store.update_progress(job.job_id, 200, "Too much.")

    reloaded_job = store.get(job.job_id)
    assert reloaded_job is not None
    assert reloaded_job.progress_percent == 100
