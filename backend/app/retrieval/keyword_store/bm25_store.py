"""
BM25 关键词检索实现。

中文要先用 jieba 分词，因为 BM25 是按"词"匹配的。
英文不需要分词（空格已经分开了），中文必须切词。
"""

import jieba
from rank_bm25 import BM25Okapi

from app.retrieval.keyword_store.base import BaseKeywordStore


class BM25Store(BaseKeywordStore):
    def __init__(self):
        self._chunk_ids: list[str] = []
        self._bm25: BM25Okapi | None = None

    def add(self, texts: list[str], chunk_ids: list[str]) -> None:
        if len(texts) != len(chunk_ids):
            raise ValueError("文本数量和 chunk_id 数量不一致")
        self._chunk_ids = chunk_ids
        # 对每段文本做分词，建倒排索引
        tokenized = [list(jieba.cut(t)) for t in texts]
        self._bm25 = BM25Okapi(tokenized)

    def search(self, query: str, top_k: int) -> list[tuple[str, float]]:
        if self._bm25 is None:
            return []
        query_tokens = list(jieba.cut(query))
        scores = self._bm25.get_scores(query_tokens)
        # 按分数从高到低排序，取 top_k，过滤掉 0 分
        ranked = sorted(enumerate(scores), key=lambda x: -x[1])
        results = []
        for idx, score in ranked:
            if score <= 0:
                continue
            results.append((self._chunk_ids[idx], float(score)))
            if len(results) >= top_k:
                break
        return results
