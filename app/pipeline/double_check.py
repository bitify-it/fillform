import json

from app.api.schemas.requests import FieldRequest, FormExtractionRequest
from app.api.schemas.responses import DoubleCheckResult, FieldAnswer
from app.domain.models import DocumentChunk
from app.domain.statuses import CheckStatus, FieldStatus
from app.llm.base import LLMClient
from app.pipeline.prompts import load_prompt


class DoubleChecker:
    def __init__(self, llm_client: LLMClient) -> None:
        self.llm_client = llm_client

    async def check(
        self,
        request: FormExtractionRequest,
        field: FieldRequest,
        answer: FieldAnswer,
        chunks: list[DocumentChunk],
    ) -> FieldAnswer:
        raw = await self.llm_client.generate_json(
            system_prompt=load_prompt("double_check", request.options.language),
            user_prompt=_build_user_prompt(request, field, answer, chunks),
        )
        double_check = DoubleCheckResult.model_validate(raw)
        status = answer.status

        if double_check.status == CheckStatus.FAILED and status == FieldStatus.ANSWERED:
            status = FieldStatus.NEEDS_REVIEW

        return answer.model_copy(update={"status": status, "double_check": double_check})


_LABELS = {
    "it": {"field": "Campo", "candidate": "Risposta candidata", "context": "Contesto documento"},
    "en": {"field": "Field", "candidate": "Candidate answer", "context": "Document context"},
}


def _build_user_prompt(
    request: FormExtractionRequest,
    field: FieldRequest,
    answer: FieldAnswer,
    chunks: list[DocumentChunk],
) -> str:
    labels = _LABELS.get((request.options.language or "en").lower(), _LABELS["en"])
    context = "\n\n".join(
        (
            f"[{chunk.chunk_id} page={chunk.page} section={chunk.section} "
            f"lineStart={chunk.line_start} lineEnd={chunk.line_end}]\n{chunk.text}"
        )
        for chunk in chunks
    )
    return (
        f"Form: {request.form_name}\n"
        f"{labels['field']}:\n{json.dumps(field.model_dump(by_alias=True), ensure_ascii=False)}\n\n"
        f"{labels['candidate']}:\n{answer.model_dump_json(by_alias=True)}\n\n"
        f"{labels['context']}:\n{context}"
    )
