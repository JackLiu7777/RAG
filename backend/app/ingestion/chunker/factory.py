"""
根据配置，建出当前使用的切块器。

现在只有一种实现。以后如果加了"按段落切""按语义切"，
在这里根据 settings.ingestion.chunker_type 选不同的类即可。
"""

from app.core.config import get_settings
from app.ingestion.chunker.base import BaseChunker
from app.ingestion.chunker.fixed_size import FixedSizeChunker


def get_chunker() -> BaseChunker:
    s = get_settings()
    return FixedSizeChunker(
        chunk_size=s.ingestion.chunk_size,
        chunk_overlap=s.ingestion.chunk_overlap,
    )
