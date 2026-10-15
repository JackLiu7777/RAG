"""
所有切块器必须遵守的接口。
"""

from abc import ABC, abstractmethod

from app.core.schemas import Chunk, Document


class BaseChunker(ABC):
    """切块器统一接口：输入一个 Document，输出一串 Chunk。"""

    @abstractmethod
    def split(self, doc: Document) -> list[Chunk]:
        ...
