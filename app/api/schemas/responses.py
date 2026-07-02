from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.domain.statuses import CheckStatus, FieldStatus, JobStatus


class Evidence(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "examples": [
                {
                    "page": 1,
                    "section": "Company data",
                    "lineStart": 4,
                    "lineEnd": 4,
                    "quote": "Company legal name: ACME S.p.A.",
                }
            ]
        },
    )

    page: int | None = Field(default=None, description="Source page when available.")
    section: str | None = Field(default=None, description="Source section when available.")
    line_start: int | None = Field(
        default=None,
        alias="lineStart",
        description="Start line in the converted internal text when available.",
    )
    line_end: int | None = Field(
        default=None,
        alias="lineEnd",
        description="End line in the converted internal text when available.",
    )
    quote: str = Field(description="Short quote from the document supporting the answer.")


class ValidationResult(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "examples": [
                {
                    "status": "passed",
                    "errors": [],
                }
            ]
        },
    )

    status: CheckStatus
    errors: list[str] = Field(default_factory=list)


class DoubleCheckResult(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "examples": [
                {
                    "status": "passed",
                    "notes": "Evidence supports the extracted value.",
                }
            ]
        },
    )

    status: CheckStatus
    notes: str


class FieldAnswer(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "examples": [
                {
                    "fieldId": "sector",
                    "targetRef": "companyProfile.industrySector",
                    "question": "What is the company's industry sector?",
                    "status": "answered",
                    "value": "IT consulting company",
                    "normalizedValue": "IT_CONSULTING",
                    "confidence": 0.82,
                    "evidence": [
                        {
                            "page": 1,
                            "section": "Company profile",
                            "lineStart": 8,
                            "lineEnd": 8,
                            "quote": "The company provides IT consulting services.",
                        }
                    ],
                    "validation": {
                        "status": "passed",
                        "errors": [],
                    },
                    "doubleCheck": {
                        "status": "passed",
                        "notes": "Evidence supports the selected option.",
                    },
                }
            ]
        },
    )

    field_id: str = Field(alias="fieldId", description="Input fieldId or generated identifier.")
    target_ref: str | None = Field(
        default=None,
        alias="targetRef",
        description="Optional caller-provided target reference.",
    )
    question: str = Field(description="Original question associated with this answer.")
    status: FieldStatus = Field(description="Final extraction status for this field.")
    value: Any = Field(default=None, description="Extracted value, or null when not found.")
    normalized_value: Any = Field(
        default=None,
        alias="normalizedValue",
        description="Normalized value when applicable.",
    )
    confidence: float = Field(ge=0, le=1, description="Model confidence score from 0 to 1.")
    evidence: list[Evidence] = Field(default_factory=list)
    validation: ValidationResult
    double_check: DoubleCheckResult = Field(alias="doubleCheck")


class ExtractionMetadata(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "examples": [
                {
                    "llmProvider": "ollama",
                    "llmModel": "gemma4:e4b",
                    "strictEvidence": True,
                }
            ]
        },
    )

    llm_provider: str = Field(alias="llmProvider")
    llm_model: str = Field(alias="llmModel")
    strict_evidence: bool = Field(alias="strictEvidence")


class FormExtractionResponse(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "examples": [
                {
                    "formName": "Company profile",
                    "status": "completed_with_gaps",
                    "answers": [
                        {
                            "fieldId": "sector",
                            "targetRef": "companyProfile.industrySector",
                            "question": "What is the company's industry sector?",
                            "status": "answered",
                            "value": "IT consulting company",
                            "normalizedValue": "IT_CONSULTING",
                            "confidence": 0.82,
                            "evidence": [
                                {
                                    "page": 1,
                                    "section": "Company profile",
                                    "lineStart": 8,
                                    "lineEnd": 8,
                                    "quote": "The company provides IT consulting services.",
                                }
                            ],
                            "validation": {
                                "status": "passed",
                                "errors": [],
                            },
                            "doubleCheck": {
                                "status": "passed",
                                "notes": "Evidence supports the selected option.",
                            },
                        },
                        {
                            "fieldId": "pec",
                            "targetRef": "companyProfile.pec",
                            "question": "What is the company's PEC address?",
                            "status": "not_found",
                            "value": None,
                            "normalizedValue": None,
                            "confidence": 0,
                            "evidence": [],
                            "validation": {
                                "status": "skipped",
                                "errors": [],
                            },
                            "doubleCheck": {
                                "status": "skipped",
                                "notes": "Double check skipped for not_found field.",
                            },
                        },
                    ],
                    "metadata": {
                        "llmProvider": "ollama",
                        "llmModel": "gemma4:e4b",
                        "strictEvidence": True,
                    },
                }
            ]
        },
    )

    form_name: str = Field(alias="formName")
    status: JobStatus
    answers: list[FieldAnswer]
    metadata: ExtractionMetadata


class LLMHealthResponse(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "examples": [
                {
                    "provider": "ollama",
                    "model": "gemma4:e4b",
                    "endpoint": "http://localhost:11434",
                    "available": True,
                    "modelAvailable": True,
                    "error": None,
                }
            ]
        },
    )

    provider: str = Field(description="Configured LLM provider.")
    model: str = Field(description="Configured LLM model.")
    endpoint: str = Field(description="Configured provider endpoint.")
    available: bool = Field(description="Whether the provider endpoint responded successfully.")
    model_available: bool = Field(
        alias="modelAvailable",
        description="Whether the configured model is available on the provider.",
    )
    error: str | None = Field(default=None, description="Health check error, when available.")


class JobCreatedResponse(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "examples": [
                {
                    "jobId": "job_90823b8a4c4449969bbfc252049aa811",
                    "status": "queued",
                    "progressPercent": 0,
                    "progressMessage": None,
                }
            ]
        },
    )

    job_id: str = Field(alias="jobId")
    status: JobStatus
    progress_percent: int = Field(
        default=0,
        alias="progressPercent",
        ge=0,
        le=100,
        description="Current job progress percentage.",
    )
    progress_message: str | None = Field(
        default=None,
        alias="progressMessage",
        description="Short human-readable progress message.",
    )


class JobResponse(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "examples": [
                {
                    "jobId": "job_90823b8a4c4449969bbfc252049aa811",
                    "status": "running",
                    "progressPercent": 45,
                    "progressMessage": "Processing field 3/8.",
                    "result": None,
                    "error": None,
                }
            ]
        },
    )

    job_id: str = Field(alias="jobId")
    status: JobStatus
    progress_percent: int = Field(
        default=0,
        alias="progressPercent",
        ge=0,
        le=100,
        description="Current job progress percentage.",
    )
    progress_message: str | None = Field(
        default=None,
        alias="progressMessage",
        description="Short human-readable progress message.",
    )
    result: FormExtractionResponse | None = None
    error: str | None = None
