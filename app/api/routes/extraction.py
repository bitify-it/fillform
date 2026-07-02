import json
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from pydantic import ValidationError as PydanticValidationError

from app.api.schemas.requests import FormExtractionRequest
from app.api.schemas.responses import (
    FormExtractionResponse,
    JobCreatedResponse,
    JobResponse,
    LLMHealthResponse,
)
from app.core.config import Settings, get_settings
from app.core.errors import AppError, LLMError
from app.llm.factory import create_llm_client
from app.pipeline.document_conversion import MarkItDownDocumentConverter
from app.pipeline.service import ExtractionService
from app.storage.job_store import FileSystemJobStore, JobStore

router = APIRouter()

MINIMAL_PAYLOAD_EXAMPLE = {
    "formName": "Company profile",
    "fields": [
        {
            "question": "What is the company legal name?",
            "expectedType": "string",
        }
    ],
    "options": {
        "strictEvidence": True,
        "language": "en",
    },
}

DROPDOWN_PAYLOAD_EXAMPLE = {
    "formName": "Company profile",
    "fields": [
        {
            "fieldId": "sector",
            "targetRef": "companyProfile.industrySector",
            "label": "Industry sector",
            "question": "What is the company's industry sector?",
            "expectedType": "enum",
            "validationRules": {
                "allowedValues": [
                    {"value": "IT_CONSULTING", "label": "IT consulting"},
                    {"value": "HEALTHCARE", "label": "Healthcare"},
                    {"value": "FINANCE", "label": "Finance"},
                    {"value": "MANUFACTURING", "label": "Manufacturing"},
                    {"value": "RETAIL", "label": "Retail"},
                ]
            },
        },
        {
            "fieldId": "operatingCountries",
            "targetRef": "companyProfile.operatingCountries",
            "label": "Operating countries",
            "question": "Which countries does the company operate in?",
            "expectedType": "array",
            "validationRules": {
                "multiple": True,
                "allowedValues": [
                    {"value": "IT", "label": "Italy"},
                    {"value": "DE", "label": "Germany"},
                    {"value": "FR", "label": "France"},
                ],
            },
        },
        {
            "fieldId": "hasDpo",
            "targetRef": "privacy.hasDpo",
            "label": "DPO appointed",
            "question": "Has the company appointed a DPO?",
            "expectedType": "boolean",
        },
    ],
}

PAYLOAD_OPENAPI_EXAMPLES = {
    "minimal": {
        "summary": "Minimal payload",
        "description": "Only question and expectedType are required for each field.",
        "value": json.dumps(MINIMAL_PAYLOAD_EXAMPLE),
    },
    "dropdowns": {
        "summary": "Dropdown, multi-select and boolean payload",
        "description": (
            "Use allowedValues with value/label objects when the frontend field has "
            "fixed options. normalizedValue will contain the technical value."
        ),
        "value": json.dumps(DROPDOWN_PAYLOAD_EXAMPLE),
    },
}
PAYLOAD_SCHEMA_EXAMPLES = [
    json.dumps(MINIMAL_PAYLOAD_EXAMPLE),
    json.dumps(DROPDOWN_PAYLOAD_EXAMPLE),
]

PAYLOAD_DESCRIPTION = (
    "JSON string describing the form extraction request. The API receives it as a "
    "multipart form field, so paste the JSON as text. Each field only requires "
    "`question` and `expectedType`; `fieldId`, `targetRef`, `label`, and "
    "`validationRules` are optional. For dropdown/select fields, use "
    "`validationRules.allowedValues` with `{value, label}` objects. `normalizedValue` "
    "will contain the technical `value` used to fill the frontend form."
)
FILE_DESCRIPTION = "Document to analyze. Supported formats: PDF, Word, Excel, HTML."


def get_job_store(settings: Settings = Depends(get_settings)) -> JobStore:
    return FileSystemJobStore(settings.storage_dir / "jobs")


def get_service(settings: Settings = Depends(get_settings)) -> ExtractionService:
    llm_client = create_llm_client(settings)
    converter = MarkItDownDocumentConverter()
    return ExtractionService(settings=settings, document_converter=converter, llm_client=llm_client)


@router.get(
    "/llm/health",
    response_model=LLMHealthResponse,
    summary="Check LLM provider health",
    description=(
        "Checks whether the configured LLM provider endpoint responds and whether the "
        "configured model is available. For Ollama, this calls `/api/tags`."
    ),
)
async def check_llm_health(settings: Settings = Depends(get_settings)) -> LLMHealthResponse:
    llm_client = create_llm_client(settings)
    return await llm_client.health_check()


@router.post(
    "/run",
    response_model=FormExtractionResponse,
    summary="Run extraction synchronously",
    description=(
        "Uploads a document and a JSON payload, runs the full extraction pipeline in the "
        "same HTTP request, and returns the final structured result. Use this endpoint for "
        "small documents, local testing, and interactive Swagger experiments."
    ),
)
async def run_extraction(
    payload: Annotated[
        str,
        Form(
            description=PAYLOAD_DESCRIPTION,
            examples=PAYLOAD_SCHEMA_EXAMPLES,
            openapi_examples=PAYLOAD_OPENAPI_EXAMPLES,
        ),
    ],
    file: Annotated[UploadFile, File(description=FILE_DESCRIPTION)],
    service: ExtractionService = Depends(get_service),
) -> FormExtractionResponse:
    request = _parse_payload(payload)
    document_bytes = await file.read()
    try:
        return await service.run(request, document_bytes, file.filename or "document")
    except LLMError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except AppError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/jobs",
    response_model=JobCreatedResponse,
    summary="Create an extraction job",
    description=(
        "Uploads a document and a JSON payload, creates a background extraction job, and "
        "immediately returns a `jobId`. Use this endpoint when extraction may take longer "
        "than a normal HTTP request should stay open. Job status is persisted under "
        "`STORAGE_DIR/jobs`."
    ),
)
async def create_job(
    background_tasks: BackgroundTasks,
    payload: Annotated[
        str,
        Form(
            description=PAYLOAD_DESCRIPTION,
            examples=PAYLOAD_SCHEMA_EXAMPLES,
            openapi_examples=PAYLOAD_OPENAPI_EXAMPLES,
        ),
    ],
    file: Annotated[UploadFile, File(description=FILE_DESCRIPTION)],
    service: ExtractionService = Depends(get_service),
    store: JobStore = Depends(get_job_store),
) -> JobCreatedResponse:
    request = _parse_payload(payload)
    document_bytes = await file.read()
    job = store.create()
    background_tasks.add_task(
        _run_job,
        store,
        service,
        job.job_id,
        request,
        document_bytes,
        file.filename or "document",
    )
    return JobCreatedResponse(
        jobId=job.job_id,
        status=job.status,
        progressPercent=job.progress_percent,
        progressMessage=job.progress_message,
    )


@router.get(
    "/jobs/{job_id}",
    response_model=JobResponse,
    summary="Get extraction job status",
    description=(
        "Returns the current status of a previously created extraction job. When the job is "
        "running, the response includes `progressPercent` and `progressMessage`. When the "
        "job is finished, the response includes the same extraction result returned by `/run`."
    ),
)
async def get_job(job_id: str, store: JobStore = Depends(get_job_store)) -> JobResponse:
    job = store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    return JobResponse(
        jobId=job.job_id,
        status=job.status,
        progressPercent=job.progress_percent,
        progressMessage=job.progress_message,
        result=job.result,
        error=job.error,
    )


async def _run_job(
    store: JobStore,
    service: ExtractionService,
    job_id: str,
    request: FormExtractionRequest,
    document_bytes: bytes,
    filename: str,
) -> None:
    store.mark_running(job_id)
    try:
        result = await service.run(
            request,
            document_bytes,
            filename,
            progress_callback=lambda percent, message: store.update_progress(
                job_id,
                percent,
                message,
            ),
        )
        store.mark_completed(job_id, result)
    except Exception as exc:
        store.mark_failed(job_id, str(exc))


def _parse_payload(payload: str) -> FormExtractionRequest:
    try:
        return FormExtractionRequest.model_validate(json.loads(payload))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=422, detail="Payload must be valid JSON.") from exc
    except PydanticValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc
