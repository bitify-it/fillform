import json
from typing import Any


def parse_json_object(raw_response: str) -> dict[str, Any] | None:
    """Return the first valid JSON object found in ``raw_response`` or None."""
    candidates = [raw_response.strip()]
    extracted = extract_first_json_object(raw_response)
    if extracted is not None:
        candidates.append(extracted)

    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    return None


def extract_first_json_object(text: str) -> str | None:
    """Extract the first balanced ``{...}`` block from ``text`` (string-aware)."""
    start = text.find("{")
    if start == -1:
        return None

    depth = 0
    in_string = False
    escape = False
    for index, char in enumerate(text[start:], start=start):
        if escape:
            escape = False
            continue
        if char == "\\":
            escape = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    return None


def repair_system_prompt() -> str:
    return (
        "You are a JSON fixer. Turn the given response into a single valid JSON object. "
        "Do not add explanations, markdown or any text outside the JSON."
    )


def repair_user_prompt(raw_response: str) -> str:
    return (
        "The following response is not valid JSON. Return only a valid JSON object, "
        "preserving the original fields and meaning when possible.\n\n"
        f"INVALID RESPONSE:\n{raw_response}"
    )
