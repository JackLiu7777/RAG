"""
Step 5 验证脚本：双路召回 + RRF 融合。
对比看：向量路、BM25 路、RRF 融合后，各自命中了什么。

用法（在 backend 目录下）：
    python retrieve_demo.py ../demo.txt
"""

from pathlib import Path

from app.core.config import get_settings
from app.ingestion.chunker.factory import get_chunker
from app.ingestion.loader.registry import get_parser
from app.retrieval.embedder.bge_embedder import BGEmbedder
from app.retrieval.fusion import rrf_fuse
from app.retrieval.keyword_store.bm25_store import BM25Store
from app.retrieval.vector_store.faiss_store import FaissVectorStore


def main() -> None:
    path = Path("../demo.txt")
    settings = get_settings()

    # 1. 加载模型
    print("[1/4] 加载 Embedding 模型...")
    embedder = BGEmbedder(
        model_path=settings.embedding.model_name,
        device=settings.embedding.device,
    )

    # 2. 解析 + 切块
    print("[2/4] 解析文件并切块...")
    doc = get_parser(path).parse(path)[0]
    chunks = get_chunker().split(doc)
    chunk_texts = [c.text for c in chunks]
    chunk_by_id = {c.chunk_id: c for c in chunks}
    print(f"      共 {len(chunks)} 块")

    # 3. 同时建两个索引
    print("[3/4] 建 FAISS 向量库 + BM25 关键词库...")
    vectors = embedder.embed(chunk_texts)
    vector_store = FaissVectorStore(dim=embedder.dimension())
    vector_store.add(vectors, [c.chunk_id for c in chunks])

    keyword_store = BM25Store()
    keyword_store.add(chunk_texts, [c.chunk_id for c in chunks])

    # 4. 对每个问题，对比三路结果
    print("[4/4] 双路召回 + RRF 融合\n")
    questions = [
        "年假可以休几天？",
        "出差住宿标准是多少？",
        "迟到怎么扣钱？",
        "病假需要什么证明？",
    ]
    top_k = settings.retrieval.top_k_per_channel  # 5

    for q in questions:
        print(f"=== 问: {q} ===")

        # 向量路
        q_vec = embedder.embed([q])
        vec_hits = vector_store.search(q_vec, top_k=top_k)
        print("  [向量路 BGE]")
        for rank, (cid, score) in enumerate(vec_hits, 1):
            c = chunk_by_id[cid]
            print(f"    {rank}. score={score:.4f} Chunk#{c.chunk_index}  {c.text[:50].strip()}...")

        # 关键词路
        kw_hits = keyword_store.search(q, top_k=top_k)
        print("  [关键词路 BM25]")
        for rank, (cid, score) in enumerate(kw_hits, 1):
            c = chunk_by_id[cid]
            print(f"    {rank}. score={score:.4f} Chunk#{c.chunk_index}  {c.text[:50].strip()}...")

        # RRF 融合
        fused = rrf_fuse(vec_hits, kw_hits, k=settings.retrieval.rrf_k, top_n=3)
        print("  [RRF 融合后 Top3]")
        for rank, (cid, score) in enumerate(fused, 1):
            c = chunk_by_id[cid]
            print(f"    {rank}. rrf={score:.5f} Chunk#{c.chunk_index}  {c.text[:50].strip()}...")
        print()


if __name__ == "__main__":
    main()
