"""
Embedding 模型的接口。
以后换别的 embedding 模型（比如 m3、OpenAI text-embedding-3），
只要实现这个接口，上层代码不用改。
"""

from abc import ABC, abstractmethod

import numpy as np


class BaseEmbedder(ABC):
    """把一段或多段文本，转成向量（浮点数数组）。"""

    @abstractmethod
    def embed(self, texts: list[str]) -> np.ndarray:
        """输入文本列表，输出形状为 (N, dim) 的 float32 矩阵。"""
        ...

    @abstractmethod
    def dimension(self) -> int:
        """返回向量维度，建 FAISS 索引时要用到。"""
        ...
