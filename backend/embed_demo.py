"""
Step 4 验证脚本：
  解析文件 → 切块 → 每块转向量 → 存进 FAISS → 用一个问题检索最像的 3 块
用法（在 backend 目录下）：
    python embed_demo.py ../demo.txt
"""

import sys
from pathlib import Path

import numpy as np

from app.core.config import get_settings
from app.core.schemas import Chunk
from app.ingestion.chunker.factory import get_chunker
from app.ingestion.loader.registry import get_parser
from app.retrieval.embedder.bge_embedder import BGEmbedder
from app.retrieval.vector_store.faiss_store import FaissVectorStore


def main() -> None:
    if len(sys.argv) < 2:
        print("用法：python embed_demo.py <文件路径>")
        return

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"文件不存在：{path}")
        return

    settings = get_settings()

    # 1) 加载 Embedding 模型（第一次会加载 390MB 到内存，等几秒）
    print("[1/5] 加载 Embedding 模型...")
    embedder = BGEmbedder(
        model_path=settings.embedding.model_name,
        device=settings.embedding.device,
    )
    print(f"      向量维度: {embedder.dimension()}")

    # 2) 解析 + 切块
    print("[2/5] 解析文件并切块...")
    doc = get_parser(path).parse(path)[0]
    chunks: list[Chunk] = get_chunker().split(doc)
    print(f"      共 {len(chunks)} 块")

    # 3) 把每块转成向量
    print("[3/5] 文本向量化...")
    chunk_texts = [c.text for c in chunks]
    vectors = embedder.embed(chunk_texts)
    print(f"      向量矩阵形状: {vectors.shape}")

    # 4) 存进 FAISS
    print("[4/5] 写入 FAISS 向量库...")
    store = FaissVectorStore(dim=embedder.dimension())
    store.add(vectors, [c.chunk_id for c in chunks])
    print(f"      FAISS 中现有 {store.count()} 条向量")

    # 5) 用一个真实问题检索
    print("[5/5] 用问题检索 top3...\n")
    questions = [
        "年假可以休几天？",
        "出差住宿标准是多少？",
        "迟到怎么扣钱？",
    ]
    # 把 chunk_id -> chunk 对象的映射准备好，方便打印原文
    chunk_by_id = {c.chunk_id: c for c in chunks}

    for q in questions:
        q_vec = embedder.embed([q])
        hits = store.search(q_vec, top_k=3)
        print(f"问: {q}")
        for rank, (cid, score) in enumerate(hits, 1):
            c = chunk_by_id[cid]
            preview = c.text.replace("\n", " ")[:80]
            print(f"  Top{rank}  相似度={score:.4f}  Chunk#{c.chunk_index}  {preview}...")
        print()


if __name__ == "__main__":
    main()
