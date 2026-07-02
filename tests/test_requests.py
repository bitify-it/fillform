import pytest
from pydantic import ValidationError

from app.api.schemas.requests import FormExtractionRequest


def test_form_extraction_request_accepts_minimal_fields() -> None:
    request = FormExtractionRequest.model_validate(
        {
            "formName": "Anagrafica Azienda",
            "fields": [
                {
                    "question": "Qual e' la ragione sociale?",
                    "expectedType": "string",
                },
                {
                    "question": "Qual e' la partita IVA?",
                    "expectedType": "vat_number",
                },
            ],
        }
    )

    assert request.fields[0].field_id == "field_001"
    assert request.fields[0].target_ref is None
    assert request.fields[0].label == ""
    assert request.fields[1].field_id == "field_002"


def test_form_extraction_request_rejects_duplicate_explicit_field_ids() -> None:
    with pytest.raises(ValidationError):
        FormExtractionRequest.model_validate(
            {
                "formName": "Anagrafica Azienda",
                "fields": [
                    {
                        "fieldId": "company_name",
                        "question": "Qual e' la ragione sociale?",
                        "expectedType": "string",
                    },
                    {
                        "fieldId": "company_name",
                        "question": "Qual e' il nome azienda?",
                        "expectedType": "string",
                    },
                ],
            }
        )


def test_form_extraction_request_accepts_allowed_value_objects() -> None:
    request = FormExtractionRequest.model_validate(
        {
            "formName": "Anagrafica Azienda",
            "fields": [
                {
                    "fieldId": "sector",
                    "question": "Qual e' il settore?",
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

    allowed_values = request.fields[0].validation_rules.allowed_values
    assert allowed_values is not None
    assert allowed_values[0].value == "IT_CONSULTING"
    assert allowed_values[0].label == "Consulenza IT"
