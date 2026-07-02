from app.domain.statuses import CheckStatus
from app.domain.validation import normalize_extracted_value, validate_extracted_value


def test_validate_extracted_value_accepts_matching_pattern() -> None:
    result = validate_extracted_value(
        value="12345678901",
        normalized_value="12345678901",
        expected_type="vat_number",
        validation_rules={"pattern": "^[0-9]{11}$"},
    )

    assert result.status == CheckStatus.PASSED
    assert result.errors == []


def test_validate_extracted_value_rejects_wrong_type() -> None:
    result = validate_extracted_value(
        value="42",
        normalized_value="42",
        expected_type="integer",
        validation_rules=None,
    )

    assert result.status == CheckStatus.FAILED
    assert "expected type" in result.errors[0]


def test_validate_extracted_value_skips_missing_value() -> None:
    result = validate_extracted_value(
        value=None,
        normalized_value=None,
        expected_type="string",
        validation_rules=None,
    )

    assert result.status == CheckStatus.SKIPPED
    assert result.errors == []


def test_normalize_extracted_value_maps_boolean_text() -> None:
    result = normalize_extracted_value(
        value="Sì",
        normalized_value=None,
        expected_type="boolean",
        validation_rules=None,
    )

    assert result is True


def test_normalize_extracted_value_maps_enum_label_to_technical_value() -> None:
    rules = {
        "allowedValues": [
            {"value": "IT_CONSULTING", "label": "Consulenza IT"},
            {"value": "FINANCE", "label": "Finanza"},
        ]
    }

    result = normalize_extracted_value(
        value="societa' di consulenza informatica",
        normalized_value="Consulenza IT",
        expected_type="enum",
        validation_rules=rules,
    )

    assert result == "IT_CONSULTING"


def test_validate_extracted_value_rejects_enum_outside_allowed_values() -> None:
    rules = {
        "allowedValues": [
            {"value": "IT_CONSULTING", "label": "Consulenza IT"},
            {"value": "FINANCE", "label": "Finanza"},
        ]
    }

    result = validate_extracted_value(
        value="Altro",
        normalized_value="OTHER",
        expected_type="enum",
        validation_rules=rules,
    )

    assert result.status == CheckStatus.FAILED
    assert "allowedValues" in result.errors[0]


def test_normalize_extracted_value_maps_multiple_allowed_values() -> None:
    rules = {
        "multiple": True,
        "allowedValues": [
            {"value": "IT", "label": "Italia"},
            {"value": "DE", "label": "Germania"},
        ],
    }

    result = normalize_extracted_value(
        value="Italia e Germania",
        normalized_value=["Italia", "Germania"],
        expected_type="array",
        validation_rules=rules,
    )

    assert result == ["IT", "DE"]
