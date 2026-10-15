"""
BGE Reranker 实现。

和 embedding 模型的区别：
- embedding 是"双塔"：query 和 chunk 分别编码，快但粗
- reranker 是"交叉编码"：query 和 chunk 拼在一起送进模型，慢但准

所以流程是：先用 embedding 粗筛出 10 个候选，再用 reranker 精排出最相关的 3 个。
"""

from pathlib import Path

from sentence_transformers import CrossEncoder

from app.retrieval.reranker.base import BaseReranker


class BGEReranker(BaseReranker):
    def __init__(self, model_path: str, device: str = "cpu"):
        if Path(model_path).exists():
            print(f"[Reranker] 加载本地模型: {model_path}")
        else:
            print(f"[Reranker] 从 HuggingFace 下载模型: {model_path}")
        self.model = CrossEncoder(model_path, device=device)

    def rerank(self, query: str, texts: list[str], top_n: int) -> list[tuple[int, float]]:
        if not texts:
            return []
        # CrossEncoder 接受 (query, text) 对，批量打分
        pairs = [(query, t) for t in texts]
        scores = self.model.predict(pairs)
        # 按分数从高到低排序，取前 top_n
        ranked = sorted(enumerate(scores), key=lambda x: -x[1])
        return [(idx, float(score)) for idx, score in ranked[:top_n]]
