"""
Step 7 端到端验证：双路召回 → RRF 融合 → Rerank 精排 → LLM 回答。
用法（在 backend 目录下）：
    python chat_demo.py
然后输入问题，输入 quit 退出。
"""

from pathlib import Path

from app.core.config import get_settings
from app.ingestion.chunker.factory import get_chunker
from app.ingestion.loader.registry import get_parser
from app.llm.openai_compat import OpenAICompatClient
from app.llm.prompts import SYSTEM_PROMPT, build_user_prompt
from app.retrieval.embedder.bge_embedder import BGEmbedder
from app.retrieval.fusion import rrf_fuse
from app.retrieval.keyword_store.bm25_store import BM25Store
from app.retrieval.reranker.bge_reranker import BGEReranker
from app.retrieval.vector_store.faiss_store import FaissVectorStore


def main() -> None:
    settings = get_settings()

    if not settings.secrets.zhipu_api_key:
        print("请先在项目根目录的 .env 文件里填好 ZHIPU_API_KEY")
        return

    # 1. 加载所有模型
    print("[1/4] 加载 Embedding + Reranker 模型...")
    embedder = BGEmbedder(
        model_path=settings.embedding.model_name,
        device=settings.embedding.device,
    )
    reranker = BGEReranker(
        model_path=settings.reranker.model_name,
        device=settings.reranker.device,
    )

    # 2. 建索引
    print("[2/4] 建 FAISS + BM25 索引...")
    path = Path("../demo.txt")
    doc = get_parser(path).parse(path)[0]
    chunks = get_chunker().split(doc)
    chunk_texts = [c.text for c in chunks]
    chunk_by_id = {c.chunk_id: c for c in chunks}

    vectors = embedder.embed(chunk_texts)
    vector_store = FaissVectorStore(dim=embedder.dimension())
    vector_store.add(vectors, [c.chunk_id for c in chunks])

    keyword_store = BM25Store()
    keyword_store.add(chunk_texts, [c.chunk_id for c in chunks])

    # 3. 初始化 LLM
    print("[3/4] 连接 LLM API...")
    llm = OpenAICompatClient(
        api_key=settings.secrets.zhipu_api_key,
        base_url=settings.llm.base_url,
        model=settings.llm.model,
        temperature=settings.llm.temperature,
    )
    print("    就绪！输入问题开始对话（quit 退出）\n")

    # 4. 对话循环
    while True:
        question = input("你: ").strip()
        if not question or question.lower() == "quit":
            break

        # 双路召回
        q_vec = embedder.embed([question])
        vec_hits = vector_store.search(q_vec, top_k=settings.retrieval.top_k_per_channel)
        kw_hits = keyword_store.search(question, top_k=settings.retrieval.top_k_per_channel)

        # RRF 融合，取候选
        fused = rrf_fuse(
            vec_hits, kw_hits,
            k=settings.retrieval.rrf_k,
            top_n=settings.retrieval.rrf_top_candidates,
        )
        # 取出候选 chunk 的文本，给 reranker 打分
        candidate_chunks = [chunk_by_id[cid] for cid, _ in fused]
        candidate_texts = [c.text for c in candidate_chunks]

        # Rerank 精排，取 top3
        reranked = reranker.rerank(question, candidate_texts, top_n=settings.retrieval.rerank_top_n)
        retrieved_chunks = [candidate_chunks[idx] for idx, _ in reranked]

        # 组装 Prompt + 调 LLM
        user_prompt = build_user_prompt(question, retrieved_chunks)
        answer = llm.chat(SYSTEM_PROMPT, user_prompt)
        print(f"AI: {answer}\n")


if __name__ == "__main__":
    main()
