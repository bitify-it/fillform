from app.api.schemas.responses import LLMHealthResponse
from app.llm.ollama import _parse_json_object


def test_parse_json_object_accepts_plain_json() -> None:
    assert _parse_json_object('{"status": "passed"}') == {"status": "passed"}


def test_parse_json_object_extracts_json_from_text() -> None:
    raw = 'Certo, ecco il JSON:\n```json\n{"status": "passed"}\n```'

    assert _parse_json_object(raw) == {"status": "passed"}


def test_parse_json_object_rejects_non_object_json() -> None:
    assert _parse_json_object('["not", "an", "object"]') is None


def test_llm_health_response_uses_public_aliases() -> None:
    response = LLMHealthResponse(
        provider="ollama",
        model="gemma4:e4b",
        endpoint="http://localhost:11434",
        available=True,
        model_available=True,
    )

    assert response.model_dump(by_alias=True)["modelAvailable"] is True
