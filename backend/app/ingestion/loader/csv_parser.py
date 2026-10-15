"""
CSV 解析器：把每一行转成一条文本，保留列名。
"""
from pathlib import Path

import pandas as pd

from app.core.schemas import Document
from app.ingestion.loader.base import BaseParser


class CsvParser(BaseParser):
    SUPPORTED_EXT = {".csv"}

    def parse(self, file_path: Path) -> list[Document]:
        df = pd.read_csv(file_path)
        lines = []
        for _, row in df.iterrows():
            parts = [f"{col}: {val}" for col, val in row.items() if pd.notna(val)]
            if parts:
                lines.append(" | ".join(parts))
        text = "\n".join(lines)
        return [
            Document(
                filename=file_path.name,
                text=text,
                metadata={"row_count": len(df), "columns": list(df.columns)},
            )
        ]
