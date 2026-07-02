import asyncio
import tempfile
from pathlib import Path
from typing import Protocol

from app.core.errors import DocumentConversionError


class DocumentConverter(Protocol):
    async def convert(self, document_bytes: bytes, filename: str) -> str:
        """Convert supported document bytes to markdown text."""


class MarkItDownDocumentConverter:
    async def convert(self, document_bytes: bytes, filename: str) -> str:
        suffix = Path(filename).suffix or ".bin"
        try:
            # MarkItDown is blocking; run it off the event loop so concurrent
            # requests are not stalled during conversion.
            result = await asyncio.to_thread(self._convert_sync, document_bytes, suffix)
        except Exception as exc:
            raise DocumentConversionError(f"Unable to convert document '{filename}'.") from exc

        markdown = getattr(result, "text_content", None)
        if not isinstance(markdown, str) or not markdown.strip():
            raise DocumentConversionError(f"Document '{filename}' produced empty markdown.")
        return markdown

    @staticmethod
    def _convert_sync(document_bytes: bytes, suffix: str) -> object:
        from markitdown import MarkItDown

        with tempfile.NamedTemporaryFile(suffix=suffix) as tmp:
            tmp.write(document_bytes)
            tmp.flush()
            return MarkItDown().convert(tmp.name)

