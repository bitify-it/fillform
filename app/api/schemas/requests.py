import re
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)

ExpectedType = Literal[
    "string",
    "number",
    "integer",
    "boolean",
    "date",
    "email",
    "phone",
    "vat_number",
    "tax_code",
    "iban",
    "address",
    "enum",
    "array",
]

AllowedValue = bool | int | float | str


class AllowedValueOption(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "examples": [
                {
                    "value": "IT_CONSULTING",
                    "label": "Consulenza IT",
                }
            ]
        },
    )

    value: AllowedValue = Field(
        description="Technical value to return in normalizedValue and use for form filling.",
        examples=["IT_CONSULTING"],
    )
    label: str = Field(
        min_length=1,
        description="Human-readable option label used by UI and LLM matching.",
        examples=["Consulenza IT"],
    )


class ValidationRules(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "examples": [
                {"pattern": "^[0-9]{11}$"},
                {
                    "allowedValues": [
                        {"value": "IT_CONSULTING", "label": "Consulenza IT"},
                        {"value": "FINANCE", "label": "Finanza"},
                    ]
                },
                {
                    "multiple": True,
                    "allowedValues": [
                        {"value": "IT", "label": "Italia"},
                        {"value": "DE", "label": "Germania"},
                    ],
                },
            ]
        },
    )

    pattern: str | None = Field(
        default=None,
        description="Optional regex that the normalized extracted value must match.",
        examples=["^[0-9]{11}$"],
    )
    allowed_values: list[AllowedValueOption | AllowedValue] | None = Field(
        default=None,
        alias="allowedValues",
        description=(
            "Optional allowed values for enum, array and custom boolean fields. Prefer "
            "objects with value and label so normalizedValue can use the technical value."
        ),
        examples=[
            [
                {"value": "IT_CONSULTING", "label": "Consulenza IT"},
                {"value": "FINANCE", "label": "Finanza"},
            ]
        ],
    )
    multiple: bool = Field(
        default=False,
        description="When true, normalizedValue is expected to be a list of allowed values.",
    )
    case_sensitive: bool = Field(
        default=False,
        alias="caseSensitive",
        description="When false, string allowed value matching is case-insensitive.",
    )


class FieldRequest(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "examples": [
                {
                    "question": "Qual e' la ragione sociale?",
                    "expectedType": "string",
                },
                {
                    "fieldId": "sector",
                    "targetRef": "companyProfile.industrySector",
                    "label": "Settore",
                    "question": "Qual e' il settore dell'azienda?",
                    "expectedType": "enum",
                    "validationRules": {
                        "allowedValues": [
                            {"value": "IT_CONSULTING", "label": "Consulenza IT"},
                            {"value": "FINANCE", "label": "Finanza"},
                        ]
                    },
                },
            ]
        },
    )

    field_id: str | None = Field(
        default=None,
        alias="fieldId",
        min_length=1,
        description=(
            "Optional stable field identifier. Generated as field_001, field_002, "
            "... if omitted."
        ),
        examples=["company_name"],
    )
    target_ref: str | None = Field(
        default=None,
        alias="targetRef",
        min_length=1,
        description="Optional UI or HTML target reference used by the caller to fill a form.",
        examples=["html:company_name"],
    )
    label: str = Field(
        default="",
        description="Optional human-readable field label. Kept empty if omitted.",
        examples=["Company name"],
    )
    question: str = Field(
        min_length=1,
        description="Question the service must answer using only document evidence.",
        examples=["What is the company legal name?"],
    )
    expected_type: ExpectedType = Field(
        alias="expectedType",
        description="Expected answer type used for deterministic validation.",
        examples=["string"],
    )
    validation_rules: ValidationRules | None = Field(
        default=None,
        alias="validationRules",
        description=(
            "Optional deterministic validation rules, for example a regex pattern or "
            "allowed dropdown values."
        ),
        examples=[{"pattern": "^[0-9]{11}$"}],
    )


class ExtractionOptions(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "examples": [
                {
                    "strictEvidence": True,
                    "language": "it",
                }
            ]
        },
    )

    strict_evidence: bool = Field(
        default=True,
        alias="strictEvidence",
        description="When true, answers require explicit evidence from the document.",
    )
    language: str = Field(
        default="it",
        description="Preferred language for prompts and short explanatory notes.",
        examples=["it"],
    )


class FormExtractionRequest(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "examples": [
                {
                    "formName": "Anagrafica Azienda",
                    "fields": [
                        {
                            "question": "Qual e' la ragione sociale?",
                            "expectedType": "string",
                        }
                    ],
                    "options": {
                        "strictEvidence": True,
                        "language": "it",
                    },
                },
                {
                    "formName": "Anagrafica Azienda",
                    "fields": [
                        {
                            "fieldId": "sector",
                            "targetRef": "companyProfile.industrySector",
                            "label": "Settore",
                            "question": "Qual e' il settore dell'azienda?",
                            "expectedType": "enum",
                            "validationRules": {
                                "allowedValues": [
                                    {
                                        "value": "IT_CONSULTING",
                                        "label": "Consulenza IT",
                                    },
                                    {"value": "FINANCE", "label": "Finanza"},
                                ]
                            },
                        }
                    ],
                    "options": {
                        "strictEvidence": True,
                        "language": "it",
                    },
                },
            ]
        },
    )

    form_name: str = Field(
        alias="formName",
        min_length=1,
        description="Logical name of the form being filled.",
        examples=["Company profile update"],
    )
    fields: list[FieldRequest] = Field(
        min_length=1,
        description="Fields to extract. Each item only requires question and expectedType.",
    )
    options: ExtractionOptions = Field(default_factory=ExtractionOptions)

    @model_validator(mode="after")
    def normalize_fields(self) -> "FormExtractionRequest":
        normalized_fields = []
        for index, field in enumerate(self.fields, start=1):
            field_id = field.field_id or f"field_{index:03d}"
            normalized_fields.append(field.model_copy(update={"field_id": field_id}))

        field_ids = [field.field_id for field in normalized_fields]
        duplicated = {field_id for field_id in field_ids if field_ids.count(field_id) > 1}
        if duplicated:
            raise ValueError(f"Duplicated fieldId values: {', '.join(sorted(duplicated))}")

        self.fields = normalized_fields
        return self

    @model_validator(mode="after")
    def validate_regex_patterns(self) -> "FormExtractionRequest":
        for field in self.fields:
            pattern = field.validation_rules.pattern if field.validation_rules else None
            if pattern is None:
                continue
            try:
                re.compile(pattern)
            except re.error as exc:
                raise ValueError(
                    f"validationRules.pattern is not a valid regex for {field.field_id}: {exc}"
                ) from exc
        return self
