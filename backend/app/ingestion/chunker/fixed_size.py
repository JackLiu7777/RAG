"""
固定大小 + 重叠（overlap）切块器。

核心逻辑：
- 第 1 块：从 0 取 chunk_size 个字
- 第 2 块：从 (chunk_size - overlap) 开始，再取 chunk_size 个字
  → 这样第 2 块的开头和第 1 块的结尾有 overlap 个字是重复的
- 一直循环到文本末尾

为什么用"字符"而不是"token"？
- 中文场景下，1 个汉字大约对应 0.6~1.5 个 token，按字符数粗算够用
- 后面要更精确，可以换成按 token 数切
"""

from app.core.schemas import Chunk, Document
from app.ingestion.chunker.base import BaseChunker


class FixedSizeChunker(BaseChunker):
    def __init__(self, chunk_size: int, chunk_overlap: int):
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap 必须小于 chunk_size，否则会死循环")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split(self, doc: Document) -> list[Chunk]:
        text = doc.text
        chunks: list[Chunk] = []
        start = 0
        index = 0

        while start < len(text):
            end = start + self.chunk_size
            piece = text[start:end]

            chunks.append(
                Chunk(
                    doc_id=doc.doc_id,
                    text=piece,
                    source=doc.filename,
                    chunk_index=index,
                )
            )
            index += 1
            # 步进 = 块大小 - 重叠量，下一块从"重叠量"之前开始
            start += self.chunk_size - self.chunk_overlap

        return chunks
