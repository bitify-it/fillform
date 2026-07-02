from dataclasses import dataclass


@dataclass(frozen=True)
class DocumentChunk:
    chunk_id: str
    text: str
    page: int | None = None
    section: str | None = None
    line_start: int | None = None
    line_end: int | None = None
