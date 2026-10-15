"""
FAISS 向量库实现。

为什么用 IndexFlatIP（内积索引）？
- 我们 embedding 时已经做了归一化，向量长度都是 1
- 两个单位向量的内积 = 余弦相似度，正好是我们想要的
- Flat 表示暴力搜索，数据量小（几千几万块）时最快最准
- 数据量上百万时再换 IVF/HNSW，现在不用提前优化

FAISS 只存"数字编号 → 向量"，不存业务信息。
所以我们自己维护一个 id_map：FAISS 编号 → chunk_id。
"""

import faiss
import numpy as np

from app.retrieval.vector_store.base import BaseVectorStore


class FaissVectorStore(BaseVectorStore):
    def __init__(self, dim: int):
        self.index = faiss.IndexFlatIP(dim)
        # FAISS 分配的数字 ID -> 我们的 chunk_id
        self._id_map: dict[int, str] = {}

    def add(self, vectors: np.ndarray, chunk_ids: list[str]) -> None:
        if len(vectors) != len(chunk_ids):
            raise ValueError("向量数量和 chunk_id 数量不一致")
        start_id = self.index.ntotal
        self.index.add(vectors)
        for i, cid in enumerate(chunk_ids):
            self._id_map[start_id + i] = cid

    def search(self, query_vector: np.ndarray, top_k: int) -> list[tuple[str, float]]:
        if self.index.ntotal == 0:
            return []
        if query_vector.ndim == 1:
            query_vector = query_vector.reshape(1, -1)
        scores, ids = self.index.search(query_vector, top_k)
        results = []
        for score, faiss_id in zip(scores[0], ids[0]):
            if faiss_id == -1:
                continue
            results.append((self._id_map[int(faiss_id)], float(score)))
        return results

    def count(self) -> int:
        return self.index.ntotal

    def save(self, index_path: str, id_map_path: str) -> None:
        """把 FAISS 索引和 id_map 存到磁盘。"""
        faiss.write_index(self.index, index_path)
        import json
        with open(id_map_path, "w", encoding="utf-8") as f:
            json.dump({str(k): v for k, v in self._id_map.items()}, f, ensure_ascii=False)

    def load(self, index_path: str, id_map_path: str) -> bool:
        """从磁盘加载。文件不存在返回 False。"""
        import json
        import os
        if not (os.path.exists(index_path) and os.path.exists(id_map_path)):
            return False
        self.index = faiss.read_index(index_path)
        with open(id_map_path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        self._id_map = {int(k): v for k, v in raw.items()}
        return True
