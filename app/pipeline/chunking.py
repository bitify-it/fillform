from app.domain.models import DocumentChunk


def chunk_markdown(markdown: str, max_chars: int = 6000) -> list[DocumentChunk]:
    normalized = "\n".join(line.rstrip() for line in markdown.splitlines()).strip()
    if not normalized:
        return []

    chunks: list[DocumentChunk] = []
    current_lines: list[str] = []
    current_line_start: int | None = None
    current_size = 0
    section: str | None = None

    for line_number, line in enumerate(normalized.splitlines(), start=1):
        if line.startswith("#"):
            section = line.lstrip("#").strip() or section

        line_size = len(line) + 1
        if current_lines and current_size + line_size > max_chars:
            chunks.append(_build_chunk(chunks, current_lines, section, current_line_start))
            current_lines = []
            current_line_start = None
            current_size = 0

        if current_line_start is None:
            current_line_start = line_number
        current_lines.append(line)
        current_size += line_size

    if current_lines:
        chunks.append(_build_chunk(chunks, current_lines, section, current_line_start))

    return chunks


def _build_chunk(
    existing_chunks: list[DocumentChunk],
    lines: list[str],
    section: str | None,
    line_start: int | None,
) -> DocumentChunk:
    chunk_number = len(existing_chunks) + 1
    line_end = None if line_start is None else line_start + len(lines) - 1
    return DocumentChunk(
        chunk_id=f"chunk_{chunk_number:04d}",
        text="\n".join(lines).strip(),
        page=None,
        section=section,
        line_start=line_start,
        line_end=line_end,
    )
