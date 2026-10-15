"""
PDF 解析器。
"""
from pathlib import Path

from pypdf import PdfReader

from app.core.schemas import Document
from app.ingestion.loader.base import BaseParser


class PdfParser(BaseParser):
    SUPPORTED_EXT = {".pdf"}

    def parse(self, file_path: Path) -> list[Document]:
        reader = PdfReader(str(file_path))
        pages = []
        for i, page in enumerate(reader.pages):
            t = page.extract_text() or ""
            if t.strip():
                pages.append(f"[第{i+1}页]\n{t}")
        text = "\n\n".join(pages)
        return [
            Document(
                filename=file_path.name,
                text=text,
                metadata={"page_count": len(reader.pages)},
            )
        ]
