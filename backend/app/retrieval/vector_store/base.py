"""
向量库的接口。
以后想换 pgvector、Milvus、Chroma，只要实现这个接口。
"""

from abc import ABC, abstractmethod

import numpy as np


class BaseVectorStore(ABC):
    @abstractmethod
    def add(self, vectors: np.ndarray, chunk_ids: list[str]) -> None:
        """把一批向量和对应的 chunk_id 存进去。"""
        ...

    @abstractmethod
    def search(self, query_vector: np.ndarray, top_k: int) -> list[tuple[str, float]]:
        """查询向量，返回 [(chunk_id, score), ...]，按分数从高到低。"""
        ...

    @abstractmethod
    def count(self) -> int:
        """当前存了多少条向量。"""
        ...
