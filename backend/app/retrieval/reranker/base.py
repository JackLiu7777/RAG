"""
Rerank 模型接口。
"""

from abc import ABC, abstractmethod


class BaseReranker(ABC):
    @abstractmethod
    def rerank(self, query: str, texts: list[str], top_n: int) -> list[tuple[int, float]]:
        """
        对候选文本精排。
        返回 [(原始下标, score), ...]，按 score 从高到低，只取前 top_n 个。
        """
        ...
