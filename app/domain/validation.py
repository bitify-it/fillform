import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

from app.domain.statuses import CheckStatus


@dataclass(frozen=True)
class DomainValidationResult:
    status: CheckStatus
    errors: list[str]


def validate_extracted_value(
    value: Any,
    normalized_value: Any,
    expected_type: str,
    validation_rules: Mapping[str, Any] | BaseModel | None,
) -> DomainValidationResult:
    rules = _rules_to_mapping(validation_rules)
    candidate = normalized_value if normalized_value is not None else value

    if candidate is None:
        return DomainValidationResult(status=CheckStatus.SKIPPED, errors=[])

    errors: list[str] = []
    if not _matches_expected_type(candidate, expected_type, rules):
        errors.append(f"Value does not match expected type '{expected_type}'.")

    pattern = rules.get("pattern")
    if pattern and not re.fullmatch(str(pattern), str(candidate)):
        errors.append("Value does not match configured pattern.")

    allowed_values = _allowed_values(rules)
    if allowed_values is not None:
        invalid_values = _find_values_not_allowed(candidate, allowed_values, rules)
        if invalid_values:
            errors.append(
                "Value is not in configured allowedValues: "
                + ", ".join(str(value) for value in invalid_values)
            )

    status = CheckStatus.FAILED if errors else CheckStatus.PASSED
    return DomainValidationResult(status=status, errors=errors)


def normalize_extracted_value(
    value: Any,
    normalized_value: Any,
    expected_type: str,
    validation_rules: Mapping[str, Any] | BaseModel | None,
) -> Any:
    if normalized_value is not None:
        source = normalized_value
    else:
        source = value

    rules = _rules_to_mapping(validation_rules)

    if expected_type == "boolean":
        return _normalize_boolean(source, rules)

    allowed_values = _allowed_values(rules)
    if allowed_values is None:
        return source

    if expected_type == "array" or rules.get("multiple") is True:
        if source is None:
            return None
        values = source if isinstance(source, list) else [source]
        return [_normalize_allowed_item(item, allowed_values, rules) for item in values]

    return _match_allowed_value(source, allowed_values, rules) if source is not None else None


def _normalize_allowed_item(
    value: Any,
    allowed_values: list[Any],
    validation_rules: Mapping[str, Any],
) -> Any:
    matched = _match_allowed_value(value, allowed_values, validation_rules)
    return matched if matched is not None else value


def _matches_expected_type(
    value: Any,
    expected_type: str,
    validation_rules: Mapping[str, Any],
) -> bool:
    string_like_types = {
        "string",
        "email",
        "phone",
        "vat_number",
        "tax_code",
        "iban",
        "address",
        "date",
    }
    if expected_type in string_like_types:
        return isinstance(value, str)
    if expected_type == "enum":
        return _allowed_values(validation_rules) is not None or isinstance(value, str)
    if expected_type == "number":
        return isinstance(value, int | float) and not isinstance(value, bool)
    if expected_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected_type == "boolean":
        return isinstance(value, bool)
    if expected_type == "array":
        return isinstance(value, list)
    return False


def _rules_to_mapping(validation_rules: Mapping[str, Any] | BaseModel | None) -> dict[str, Any]:
    if validation_rules is None:
        return {}
    if isinstance(validation_rules, BaseModel):
        return validation_rules.model_dump(by_alias=True, exclude_none=True)
    return dict(validation_rules)


def _allowed_values(validation_rules: Mapping[str, Any]) -> list[Any] | None:
    raw_values = validation_rules.get("allowedValues")
    if raw_values is None:
        raw_values = validation_rules.get("allowed_values")
    if raw_values is None:
        return None
    if not isinstance(raw_values, list):
        return []
    return [_option_value(item) for item in raw_values]


def _option_value(option: Any) -> Any:
    if isinstance(option, BaseModel):
        return option.model_dump().get("value")
    if isinstance(option, Mapping):
        return option.get("value")
    return option


def _option_labels(option: Any) -> list[Any]:
    if isinstance(option, BaseModel):
        item = option.model_dump()
    elif isinstance(option, Mapping):
        item = option
    else:
        return [option]

    labels = [item.get("value")]
    if item.get("label") is not None:
        labels.append(item.get("label"))
    return labels


def _find_values_not_allowed(
    value: Any,
    allowed_values: list[Any],
    validation_rules: Mapping[str, Any],
) -> list[Any]:
    values = value if isinstance(value, list) else [value]
    return [
        item
        for item in values
        if _match_allowed_value(item, allowed_values, validation_rules) is None
    ]


def _match_allowed_value(
    value: Any,
    allowed_values: list[Any],
    validation_rules: Mapping[str, Any],
) -> Any:
    raw_values = (
        validation_rules.get("allowedValues")
        or validation_rules.get("allowed_values")
        or []
    )
    for raw_option, option_value in zip(raw_values, allowed_values, strict=False):
        candidates = _option_labels(raw_option)
        if any(_values_equal(value, candidate, validation_rules) for candidate in candidates):
            return option_value
    return None


def _values_equal(left: Any, right: Any, validation_rules: Mapping[str, Any]) -> bool:
    if (
        isinstance(left, str)
        and isinstance(right, str)
        and not validation_rules.get("caseSensitive")
    ):
        return left.casefold() == right.casefold()
    return left == right


def _normalize_boolean(value: Any, validation_rules: Mapping[str, Any]) -> bool | Any:
    allowed_values = _allowed_values(validation_rules)
    if allowed_values is not None:
        matched = _match_allowed_value(value, allowed_values, validation_rules)
        if isinstance(matched, bool):
            return matched
        return value

    if isinstance(value, bool) or value is None:
        return value
    if not isinstance(value, str):
        return value

    normalized = value.strip().casefold()
    true_values = {"true", "yes", "y", "si", "sì", "1", "vero", "presente", "attivo"}
    false_values = {"false", "no", "n", "0", "falso", "assente", "non presente", "disattivo"}
    if normalized in true_values:
        return True
    if normalized in false_values:
        return False
    return value
