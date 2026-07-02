from enum import StrEnum


class FieldStatus(StrEnum):
    ANSWERED = "answered"
    NOT_FOUND = "not_found"
    AMBIGUOUS = "ambiguous"
    VALIDATION_FAILED = "validation_failed"
    NEEDS_REVIEW = "needs_review"
    ERROR = "error"


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    COMPLETED_WITH_GAPS = "completed_with_gaps"
    FAILED = "failed"


class CheckStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"

