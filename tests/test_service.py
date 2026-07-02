from typing import Any

from app.api.schemas.requests import FormExtractionRequest
from app.core.config import Settings
from app.domain.statuses import FieldStatus, JobStatus
from app.pipeline.service import ExtractionService


class FakeConverter:
    async def convert(self, document_bytes: bytes, filename: str) -> str:
        return document_bytes.decode()


class FakeLLM:
    provider = "fake"
    model = "test-model"

    def __init__(self, extraction_response: dict[str, Any] | None = None) -> None:
        self.calls = 0
        self.extraction_response = extraction_response or {
            "status": "answered",
            "value": "ACME S.p.A.",
            "normalizedValue": "ACME S.p.A.",
            "confidence": 0.91,
            "evidence": [
                {
                    "page": 1,
                    "section": "Dati societari",
                    "lineStart": 2,
                    "lineEnd": 2,
                    "quote": "Ragione sociale: ACME S.p.A.",
                }
            ],
        }

    async def generate_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        self.calls += 1
        if self.calls == 1:
            return self.extraction_response
        return {"status": "passed", "notes": "Evidence supports the value."}


async def test_extraction_service_returns_answer_with_evidence() -> None:
    request = FormExtractionRequest.model_validate(
        {
            "formName": "Anagrafica Azienda",
            "fields": [
                {
                    "question": "Qual e' la ragione sociale?",
                    "expectedType": "string",
                }
            ],
        }
    )
    llm = FakeLLM()
    service = ExtractionService(
        settings=Settings(MAX_UPLOAD_BYTES=1024),
        document_converter=FakeConverter(),
        llm_client=llm,
    )

    progress_updates = []
    response = await service.run(
        request,
        b"# Dati societari\nRagione sociale: ACME S.p.A.",
        "sample.html",
        progress_callback=lambda percent, message: progress_updates.append((percent, message)),
    )

    assert response.status == JobStatus.COMPLETED
    assert response.answers[0].status == FieldStatus.ANSWERED
    assert response.answers[0].field_id == "field_001"
    assert response.answers[0].target_ref is None
    assert response.answers[0].question == "Qual e' la ragione sociale?"
    assert response.answers[0].value == "ACME S.p.A."
    assert response.answers[0].evidence[0].quote == "Ragione sociale: ACME S.p.A."
    assert response.answers[0].evidence[0].line_start == 2
    assert llm.calls == 1
    assert progress_updates[-1] == (95, "Processed field 1/1.")


async def test_extraction_service_skips_double_check_for_not_found() -> None:
    request = FormExtractionRequest.model_validate(
        {
            "formName": "Anagrafica Azienda",
            "fields": [
                {
                    "question": "Qual e' il paese?",
                    "expectedType": "string",
                }
            ],
        }
    )
    llm = FakeLLM(
        {
            "status": "not_found",
            "value": None,
            "normalizedValue": None,
            "confidence": 0,
            "evidence": [],
        }
    )
    service = ExtractionService(
        settings=Settings(MAX_UPLOAD_BYTES=1024),
        document_converter=FakeConverter(),
        llm_client=llm,
    )

    response = await service.run(request, b"<html></html>", "sample.html")

    assert response.status == JobStatus.COMPLETED_WITH_GAPS
    assert response.answers[0].status == FieldStatus.NOT_FOUND
    assert response.answers[0].double_check.status == "skipped"
    assert llm.calls == 1


async def test_extraction_service_double_checks_low_confidence_answer() -> None:
    request = FormExtractionRequest.model_validate(
        {
            "formName": "Anagrafica Azienda",
            "fields": [
                {
                    "question": "Qual e' la ragione sociale?",
                    "expectedType": "string",
                }
            ],
        }
    )
    llm = FakeLLM(
        {
            "status": "answered",
            "value": "ACME S.p.A.",
            "normalizedValue": "ACME S.p.A.",
            "confidence": 0.5,
            "evidence": [{"quote": "Ragione sociale: ACME S.p.A."}],
        }
    )
    service = ExtractionService(
        settings=Settings(MAX_UPLOAD_BYTES=1024, DOUBLE_CHECK_CONFIDENCE_THRESHOLD=0.6),
        document_converter=FakeConverter(),
        llm_client=llm,
    )

    response = await service.run(
        request,
        b"# Dati societari\nRagione sociale: ACME S.p.A.",
        "sample.html",
    )

    assert response.answers[0].double_check.status == "passed"
    assert llm.calls == 2


async def test_extraction_service_normalizes_dropdown_label_to_value() -> None:
    request = FormExtractionRequest.model_validate(
        {
            "formName": "Anagrafica Azienda",
            "fields": [
                {
                    "fieldId": "sector",
                    "question": "Qual e' il settore dell'azienda?",
                    "expectedType": "enum",
                    "validationRules": {
                        "allowedValues": [
                            {"value": "IT_CONSULTING", "label": "Consulenza IT"},
                            {"value": "FINANCE", "label": "Finanza"},
                        ]
                    },
                }
            ],
        }
    )
    llm = FakeLLM(
        {
            "status": "answered",
            "value": "societa' di consulenza informatica",
            "normalizedValue": "Consulenza IT",
            "confidence": 0.82,
            "evidence": [{"quote": "Settore: societa' di consulenza informatica"}],
        }
    )
    service = ExtractionService(
        settings=Settings(MAX_UPLOAD_BYTES=1024),
        document_converter=FakeConverter(),
        llm_client=llm,
    )

    response = await service.run(
        request,
        b"Settore: societa' di consulenza informatica",
        "sample.html",
    )

    assert response.status == JobStatus.COMPLETED
    assert response.answers[0].status == FieldStatus.ANSWERED
    assert response.answers[0].normalized_value == "IT_CONSULTING"
