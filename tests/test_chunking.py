from app.pipeline.chunking import chunk_markdown


def test_chunk_markdown_preserves_text_and_section() -> None:
    chunks = chunk_markdown("# Dati societari\nRagione sociale: ACME S.p.A.", max_chars=100)

    assert len(chunks) == 1
    assert chunks[0].chunk_id == "chunk_0001"
    assert chunks[0].section == "Dati societari"
    assert chunks[0].line_start == 1
    assert chunks[0].line_end == 2
    assert "ACME S.p.A." in chunks[0].text


def test_chunk_markdown_returns_empty_list_for_blank_input() -> None:
    assert chunk_markdown(" \n ") == []
