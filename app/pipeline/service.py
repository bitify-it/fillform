import logging
from collections.abc import Callable

from app.api.schemas.requests import FormExtractionRequest
from app.api.schemas.responses import (
    DoubleCheckResult,
    ExtractionMetadata,
    FieldAnswer,
    FormExtractionResponse,
)
from app.core.config import Settings
from app.core.errors import ValidationError
from app.domain.statuses import CheckStatus, FieldStatus, JobStatus
from app.llm.base import LLMClient
from app.pipeline.chunking import chunk_markdown
from app.pipeline.document_conversion import DocumentConverter
from app.pipeline.double_check import DoubleChecker
from app.pipeline.extraction import FieldExtractor

SUPPORTED_DOCUMENT_SUFFIXES = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".html", ".htm"}
logger = logging.getLogger(__name__)


class ExtractionService:
    def __init__(
        self,
        settings: Settings,
        document_converter: DocumentConverter,
        llm_client: LLMClient,
    ) -> None:
        self.settings = settings
        self.document_converter = document_converter
        self.extractor = FieldExtractor(llm_client)
        self.double_checker = DoubleChecker(llm_client)

    async def run(
        self,
        request: FormExtractionRequest,
        document_bytes: bytes,
        filename: str,
        progress_callback: Callable[[int, str], None] | None = None,
    ) -> FormExtractionResponse:
        logger.info(
            "extraction.start form=%s filename=%s fields=%s bytes=%s",
            request.form_name,
            filename,
            len(request.fields),
            len(document_bytes),
        )
        if not document_bytes:
            raise ValidationError("Document file is empty.")
        if len(document_bytes) > self.settings.max_upload_bytes:
            raise ValidationError("Document file exceeds configured upload limit.")
        if not _has_supported_suffix(filename):
            raise ValidationError("Unsupported document format.")

        _report_progress(progress_callback, 5, "Validating input.")
        logger.info("extraction.conversion.start filename=%s", filename)
        markdown = await self.document_converter.convert(document_bytes, filename)
        logger.info(
            "extraction.conversion.done filename=%s markdown_chars=%s",
            filename,
            len(markdown),
        )
        _report_progress(progress_callback, 15, "Document converted.")

        chunks = chunk_markdown(markdown)
        if not chunks:
            raise ValidationError("Document conversion produced no usable chunks.")
        logger.info("extraction.chunking.done filename=%s chunks=%s", filename, len(chunks))
        _report_progress(progress_callback, 20, "Document chunked.")

        answers = []
        total_fields = len(request.fields)
        for index, field in enumerate(request.fields, start=1):
            logger.info(
                "extraction.field.start form=%s field=%s index=%s/%s",
                request.form_name,
                field.field_id,
                index,
                len(request.fields),
            )
            answer = await self.extractor.extract(request, field, chunks)
            logger.info(
                "extraction.field.extracted field=%s status=%s confidence=%.2f evidence=%s",
                field.field_id,
                answer.status,
                answer.confidence,
                len(answer.evidence),
            )
            if _should_double_check(answer, self.settings):
                checked_answer = await self.double_checker.check(request, field, answer, chunks)
                logger.info(
                    "extraction.field.double_checked field=%s status=%s double_check=%s",
                    field.field_id,
                    checked_answer.status,
                    checked_answer.double_check.status,
                )
            else:
                checked_answer = _mark_double_check_skipped(answer, self.settings.double_check_mode)
                logger.info(
                    "extraction.field.double_check_skipped field=%s status=%s mode=%s",
                    field.field_id,
                    checked_answer.status,
                    self.settings.double_check_mode,
            )
            answers.append(checked_answer)
            percent = 20 + round((index / total_fields) * 75)
            _report_progress(
                progress_callback,
                percent,
                f"Processed field {index}/{total_fields}.",
            )

        status = _resolve_job_status(answers)
        logger.info(
            "extraction.done form=%s status=%s answers=%s",
            request.form_name,
            status,
            len(answers),
        )

        return FormExtractionResponse(
            formName=request.form_name,
            status=status,
            answers=answers,
            metadata=ExtractionMetadata(
                documentPages=None,
                processedPages=None,
                llmProvider=self.extractor.llm_client.provider,
                llmModel=self.extractor.llm_client.model,
                strictEvidence=request.options.strict_evidence,
            ),
        )


def _resolve_job_status(answers) -> JobStatus:
    gap_statuses = {
        FieldStatus.NOT_FOUND,
        FieldStatus.AMBIGUOUS,
        FieldStatus.VALIDATION_FAILED,
        FieldStatus.NEEDS_REVIEW,
        FieldStatus.ERROR,
    }
    if any(answer.status in gap_statuses for answer in answers):
        return JobStatus.COMPLETED_WITH_GAPS
    return JobStatus.COMPLETED


def _has_supported_suffix(filename: str) -> bool:
    lower_filename = filename.lower()
    return any(lower_filename.endswith(suffix) for suffix in SUPPORTED_DOCUMENT_SUFFIXES)


def _should_double_check(answer: FieldAnswer, settings: Settings) -> bool:
    mode = settings.double_check_mode.lower()
    if mode == "disabled":
        return False
    if mode == "always":
        return True
    if answer.status != FieldStatus.ANSWERED:
        return False
    if mode == "answered":
        return True
    if mode == "low_confidence":
        return answer.confidence < settings.double_check_confidence_threshold
    logger.warning("Unknown DOUBLE_CHECK_MODE=%s. Falling back to low_confidence.", mode)
    return answer.confidence < settings.double_check_confidence_threshold


def _mark_double_check_skipped(answer: FieldAnswer, mode: str) -> FieldAnswer:
    return answer.model_copy(
        update={
            "double_check": DoubleCheckResult(
                status=CheckStatus.SKIPPED,
                notes=f"Double check skipped by policy '{mode}'.",
            )
        }
    )


def _report_progress(
    progress_callback: Callable[[int, str], None] | None,
    percent: int,
    message: str,
) -> None:
    if progress_callback is not None:
        progress_callback(percent, message)
