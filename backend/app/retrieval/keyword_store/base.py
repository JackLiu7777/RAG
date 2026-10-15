"""
关键词检索库的接口。
以后换 Elasticsearch/MeiliSearch，只要实现这个接口。
"""

from abc import ABC, abstractmethod


class BaseKeywordStore(ABC):
    @abstractmethod
    def add(self, texts: list[str], chunk_ids: list[str]) -> None:
        """把一批文本和对应的 chunk_id 建索引。"""
        ...

    @abstractmethod
    def search(self, query: str, top_k: int) -> list[tuple[str, float]]:
        """按关键词检索，返回 [(chunk_id, score), ...]。"""
        ...
