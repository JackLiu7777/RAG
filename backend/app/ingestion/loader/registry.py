"""
根据文件扩展名，自动挑对应的解析器。
"""
from pathlib import Path

from app.ingestion.loader.base import BaseParser
from app.ingestion.loader.csv_parser import CsvParser
from app.ingestion.loader.docx_parser import DocxParser
from app.ingestion.loader.pdf_parser import PdfParser
from app.ingestion.loader.txt_parser import TxtParser

_PARSERS: dict[str, type[BaseParser]] = {
    ".txt": TxtParser,
    ".md": TxtParser,
    ".docx": DocxParser,
    ".pdf": PdfParser,
    ".csv": CsvParser,
}


def get_parser(file_path: Path) -> BaseParser:
    ext = file_path.suffix.lower()
    if ext not in _PARSERS:
        supported = ", ".join(sorted(_PARSERS.keys()))
        raise ValueError(f"暂不支持的文件格式：{ext}（当前支持：{supported}）")
    return _PARSERS[ext]()
