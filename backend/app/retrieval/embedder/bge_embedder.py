"""
BGE 本地 embedding 模型封装。

两个关键细节：
1. normalize_embeddings=True：把向量归一化成单位长度。
   这样 FAISS 用"内积"算相似度时，内积就等于余弦相似度，效果更好。
2. 离线建索引和在线查询，必须用【同一个】模型，
   否则两边向量不在同一个"数学坐标系"里，检索就是瞎猜。
"""

from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

from app.retrieval.embedder.base import BaseEmbedder


class BGEmbedder(BaseEmbedder):
    def __init__(self, model_path: str, device: str = "cpu"):
        # SentenceTransformer 会自动识别这是一个本地路径还是 HuggingFace 模型名
        if Path(model_path).exists():
            print(f"[Embedding] 加载本地模型: {model_path}")
        else:
            print(f"[Embedding] 从 HuggingFace 下载模型: {model_path}")
        self.model = SentenceTransformer(model_path, device=device)
        self._dim = self.model.get_embedding_dimension()

    def embed(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, self._dim), dtype="float32")
        emb = self.model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return emb.astype("float32")

    def dimension(self) -> int:
        return self._dim
