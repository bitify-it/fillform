import json

from app.api.schemas.requests import FieldRequest, FormExtractionRequest
from app.api.schemas.responses import DoubleCheckResult, Evidence, FieldAnswer, ValidationResult
from app.domain.models import DocumentChunk
from app.domain.statuses import CheckStatus, FieldStatus
from app.domain.validation import normalize_extracted_value, validate_extracted_value
from app.llm.base import LLMClient
from app.pipeline.prompts import load_prompt


class FieldExtractor:
    def __init__(self, llm_client: LLMClient) -> None:
        self.llm_client = llm_client

    async def extract(
        self,
        request: FormExtractionRequest,
        field: FieldRequest,
        chunks: list[DocumentChunk],
    ) -> FieldAnswer:
        raw = await self.llm_client.generate_json(
            system_prompt=load_prompt("extraction", request.options.language),
            user_prompt=_build_user_prompt(request, field, chunks),
        )
        return _build_field_answer(field, raw)


_LABELS = {
    "it": {
        "field": "Campo richiesto",
        "language": "Lingua",
        "context": "Contesto documento",
    },
    "en": {
        "field": "Requested field",
        "language": "Language",
        "context": "Document context",
    },
}


def _labels(language: str) -> dict[str, str]:
    return _LABELS.get((language or "en").lower(), _LABELS["en"])


def _build_user_prompt(
    request: FormExtractionRequest,
    field: FieldRequest,
    chunks: list[DocumentChunk],
) -> str:
    labels = _labels(request.options.language)
    context = "\n\n".join(
        (
            f"[{chunk.chunk_id} page={chunk.page} section={chunk.section} "
            f"lineStart={chunk.line_start} lineEnd={chunk.line_end}]\n{chunk.text}"
        )
        for chunk in chunks
    )
    field_payload = field.model_dump(by_alias=True)
    return (
        f"Form: {request.form_name}\n"
        f"{labels['language']}: {request.options.language}\n"
        f"{labels['field']}:\n{json.dumps(field_payload, ensure_ascii=False)}\n\n"
        f"{labels['context']}:\n{context}"
    )


def _build_field_answer(field: FieldRequest, raw: dict) -> FieldAnswer:
    status = _parse_field_status(raw.get("status"))
    evidence = _parse_evidence(raw.get("evidence", []))
    value = raw.get("value")
    normalized_value = normalize_extracted_value(
        value=value,
        normalized_value=raw.get("normalizedValue"),
        expected_type=field.expected_type,
        validation_rules=field.validation_rules,
    )
    confidence = _parse_confidence(raw.get("confidence"))

    if status == FieldStatus.ANSWERED and not evidence:
        status = FieldStatus.NEEDS_REVIEW

    validation = validate_extracted_value(
        value=value,
        normalized_value=normalized_value,
        expected_type=field.expected_type,
        validation_rules=field.validation_rules,
    )
    if validation.status == CheckStatus.FAILED and status == FieldStatus.ANSWERED:
        status = FieldStatus.VALIDATION_FAILED

    return FieldAnswer(
        fieldId=field.field_id,
        targetRef=field.target_ref,
        question=field.question,
        status=status,
        value=value,
        normalizedValue=normalized_value,
        confidence=confidence,
        evidence=evidence,
        validation=ValidationResult(status=validation.status, errors=validation.errors),
        doubleCheck=DoubleCheckResult(
            status=CheckStatus.SKIPPED,
            notes="Double check not executed yet.",
        ),
    )


def _parse_field_status(value: object) -> FieldStatus:
    try:
        return FieldStatus(value)
    except ValueError:
        return FieldStatus.NEEDS_REVIEW


def _parse_evidence(value: object) -> list[Evidence]:
    if not isinstance(value, list):
        return []

    evidence: list[Evidence] = []
    for item in value:
        if isinstance(item, dict):
            try:
                evidence.append(Evidence.model_validate(item))
            except ValueError:
                continue
    return evidence


def _parse_confidence(value: object) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return 0
    return max(0, min(confidence, 1))
