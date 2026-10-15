"""
RAG 流水线：离线建库 + 在线问答 + 持久化 + 多会话。
"""
from collections.abc import Iterator
from pathlib import Path

from app.core.config import get_settings
from app.ingestion.chunker.factory import get_chunker
from app.ingestion.loader.registry import get_parser
from app.llm.openai_compat import OpenAICompatClient
from app.llm.prompts import SYSTEM_PROMPT, CHAT_SYSTEM_PROMPT, build_user_prompt, build_chat_prompt
from app.retrieval.embedder.bge_embedder import BGEmbedder
from app.retrieval.fusion import rrf_fuse
from app.retrieval.keyword_store.bm25_store import BM25Store
from app.retrieval.reranker.bge_reranker import BGEReranker
from app.retrieval.vector_store.faiss_store import FaissVectorStore
from app.storage.metadata_store import MetadataStore
from app.storage.session_store import SessionStore
from app.tools.web_search import WebSearchTool


class RAGPipeline:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.settings = get_settings()
        self._loaded = False
        self.chunk_by_id = {}

    def load(self):
        if self._loaded:
            return
        data_dir = Path(self.settings.app.data_dir)
        data_dir.mkdir(exist_ok=True)

        print("[Pipeline] 加载 Embedding 模型...")
        self.embedder = BGEmbedder(
            model_path=self.settings.embedding.model_name,
            device=self.settings.embedding.device,
        )
        print("[Pipeline] 加载 Reranker 模型...")
        self.reranker = BGEReranker(
            model_path=self.settings.reranker.model_name,
            device=self.settings.reranker.device,
        )

        print("[Pipeline] 初始化存储...")
        self.vector_store = FaissVectorStore(dim=self.embedder.dimension())
        self.keyword_store = BM25Store()
        self.meta = MetadataStore(str(data_dir / "metadata.db"))
        self.sessions = SessionStore(str(data_dir / "sessions.db"))
        self.web_search = WebSearchTool(self.settings.secrets.bocha_api_key)

        self._restore_index(data_dir)

        print("[Pipeline] 连接 LLM API...")
        self.llm = OpenAICompatClient(
            api_key=self.settings.secrets.zhipu_api_key,
            base_url=self.settings.llm.base_url,
            model=self.settings.llm.model,
            temperature=self.settings.llm.temperature,
        )
        self._loaded = True
        print(f"[Pipeline] 就绪，已恢复 {len(self.chunk_by_id)} 个文本块。")

    def _restore_index(self, data_dir: Path):
        index_ok = self.vector_store.load(
            str(data_dir / "faiss.index"),
            str(data_dir / "faiss_idmap.json"),
        )
        if not index_ok:
            print("[Pipeline] 未找到已存索引，从空库开始。")
            return

        from app.core.schemas import Chunk
        all_chunks = self.meta.get_all_chunks()
        if not all_chunks:
            return
        for row in all_chunks:
            c = Chunk(
                chunk_id=row["chunk_id"],
                doc_id=row["doc_id"],
                text=row["text"],
                source=row["source"],
                chunk_index=row["chunk_index"],
            )
            self.chunk_by_id[c.chunk_id] = c
        texts = [c.text for c in self.chunk_by_id.values()]
        self.keyword_store.add(texts, list(self.chunk_by_id.keys()))
        print(f"[Pipeline] 从磁盘恢复了 {len(all_chunks)} 个文本块。")

    def _save_index(self, data_dir: Path):
        self.vector_store.save(
            str(data_dir / "faiss.index"),
            str(data_dir / "faiss_idmap.json"),
        )

    # ---------- 离线：建库 ----------

    def ingest_file(self, file_path: Path):
        self.load()
        parser = get_parser(file_path)
        docs = parser.parse(file_path)
        chunker = get_chunker()
        all_chunks = []
        for doc in docs:
            chunks = chunker.split(doc)
            all_chunks.extend(chunks)
        if not all_chunks:
            return {"chunks": 0, "message": "文件内容为空"}

        texts = [c.text for c in all_chunks]
        vectors = self.embedder.embed(texts)
        self.vector_store.add(vectors, [c.chunk_id for c in all_chunks])
        self.keyword_store.add(texts, [c.chunk_id for c in all_chunks])
        for c in all_chunks:
            self.chunk_by_id[c.chunk_id] = c

        self.meta.add_document(all_chunks[0].doc_id, file_path.name, len(all_chunks))
        self.meta.add_chunks([
            (c.chunk_id, c.doc_id, c.text, c.source, c.chunk_index)
            for c in all_chunks
        ])
        self._save_index(Path(self.settings.app.data_dir))
        return {
            "chunks": len(all_chunks),
            "doc_id": all_chunks[0].doc_id,
            "total_chunks": len(self.chunk_by_id),
        }

    # ---------- 文件管理 ----------

    def list_files(self) -> list[dict]:
        self.load()
        return self.meta.list_documents()

    def delete_file(self, doc_id: str):
        self.load()
        to_remove = [cid for cid, c in self.chunk_by_id.items() if c.doc_id == doc_id]
        for cid in to_remove:
            del self.chunk_by_id[cid]
        self.meta.delete_document(doc_id)
        self.keyword_store = BM25Store()
        if self.chunk_by_id:
            texts = [c.text for c in self.chunk_by_id.values()]
            self.keyword_store.add(texts, list(self.chunk_by_id.keys()))
        self.vector_store = FaissVectorStore(dim=self.embedder.dimension())
        if self.chunk_by_id:
            texts = [c.text for c in self.chunk_by_id.values()]
            vectors = self.embedder.embed(texts)
            self.vector_store.add(vectors, list(self.chunk_by_id.keys()))
        self._save_index(Path(self.settings.app.data_dir))
        return {"deleted": len(to_remove)}

    # ---------- 在线：检索（带调试信息） ----------

    def retrieve(self, question: str):
        """返回 top chunks 和调试详情。"""
        q_vec = self.embedder.embed([question])
        vec_hits = self.vector_store.search(q_vec, top_k=self.settings.retrieval.top_k_per_channel)
        kw_hits = self.keyword_store.search(question, top_k=self.settings.retrieval.top_k_per_channel)

        fused = rrf_fuse(
            vec_hits, kw_hits,
            k=self.settings.retrieval.rrf_k,
            top_n=self.settings.retrieval.rrf_top_candidates,
        )
        candidates = [self.chunk_by_id[cid] for cid, _ in fused if cid in self.chunk_by_id]
        if not candidates:
            return [], {}

        candidate_texts = [c.text for c in candidates]
        reranked = self.reranker.rerank(
            question, candidate_texts, top_n=self.settings.retrieval.rerank_top_n,
        )
        top_chunks = [candidates[idx] for idx, _ in reranked]

        debug = {
            "vector_hits": [
                {"score": round(s, 4), "text": self.chunk_by_id[cid].text[:100]}
                for cid, s in vec_hits if cid in self.chunk_by_id
            ],
            "keyword_hits": [
                {"score": round(s, 4), "text": self.chunk_by_id[cid].text[:100]}
                for cid, s in kw_hits if cid in self.chunk_by_id
            ],
            "rrf_candidates": [
                {"rrf_score": round(s, 4), "text": self.chunk_by_id[cid].text[:100]}
                for cid, s in fused if cid in self.chunk_by_id
            ],
            "reranked": [
                {"rerank_score": round(s, 4), "text": c.text[:100]}
                for c, (_, s) in zip(top_chunks, reranked)
            ],
        }
        return top_chunks, debug

    # ---------- 意图识别 ----------

    def _classify_intent(self, question: str) -> str:
        """判断问题类型：rag（查文档）/ web（联网搜）/ chat（闲聊）。"""
        q = question.strip()
        # 规则前置：明显闲聊直接跳过
        chat_keywords = ["你好", "您好", "hi", "hello", "谢谢", "感谢", "再见", "拜拜",
                         "你是谁", "你能做什么", "你会什么", "讲个笑话", "讲故事"]
        for kw in chat_keywords:
            if kw in q.lower():
                return "chat"

        # 交给 LLM 三分类
        prompt = f"""判断用户问题属于哪类，只回答一个词：rag、web 或 chat。

rag：问企业制度、流程、规定、报销、考勤、年假、请假等公司内部问题
web：问新闻、天气、股价、当前日期、今天星期几、最近发生什么、实时信息
chat：打招呼、闲聊、问你是谁、讲笑话

问题：{q}"""
        result = self.llm.chat("你是一个意图分类器。", prompt).strip().lower()
        if result.startswith("web"):
            return "web"
        if result.startswith("chat"):
            return "chat"
        return "rag"

    # ---------- 在线：问答 ----------

    def ask_stream(self, question: str, session_id: str) -> Iterator[tuple]:
        """流式问答，先 yield 调试信息，再 yield 文本片段。"""
        self.load()
        self.sessions.add_message(session_id, "user", question)

        if not self.chunk_by_id:
            yield ("contexts", [])
            yield ("debug", {"note": "无文档，跳过检索"})
            answer = "请先上传文件再提问。"
            yield ("text", answer)
            self.sessions.add_message(session_id, "ai", answer)
            yield ("done", None)
            return

        history = self.sessions.get_messages(session_id)
        intent = self._classify_intent(question)
        print(f"[意图] {question} → {intent}")

        if intent == "chat":
            # 闲聊：不检索，直接回答
            yield ("contexts", [])
            yield ("debug", {"note": "闲聊，跳过检索和搜索"})
            chat_prompt = build_chat_prompt(question, history)
            full_answer = ""
            for delta in self.llm.chat_stream(CHAT_SYSTEM_PROMPT, chat_prompt):
                full_answer += delta
                yield ("text", delta)
            self.sessions.add_message(session_id, "ai", full_answer)
            yield ("done", None)
            return

        if intent == "web":
            # 联网搜索
            yield ("contexts", [])
            yield ("debug", {"note": "正在联网搜索..."})
            web_results = self.web_search.search(question)
            if web_results:
                web_context = "\n".join([
                    f"[{i+1}] {r['title']}\n{r['snippet']}\n来源：{r['url']}"
                    for i, r in enumerate(web_results)
                ])
                contexts = [{"text": r["snippet"][:200], "source": r["url"]} for r in web_results]
                yield ("contexts", contexts)
                yield ("debug", {"note": f"搜索到 {len(web_results)} 条结果", "web": web_results})
            else:
                web_context = "（搜索无结果）"
                yield ("debug", {"note": "搜索无结果"})

            web_prompt = f"""【搜索结果】
{web_context}

【当前问题】
{question}

请基于以上搜索结果回答，标注来源编号。"""
            full_answer = ""
            for delta in self.llm.chat_stream(CHAT_SYSTEM_PROMPT, web_prompt):
                full_answer += delta
                yield ("text", delta)
            self.sessions.add_message(session_id, "ai", full_answer)
            yield ("done", None)
            return

        # RAG：走文档检索
        top_chunks, debug = self.retrieve(question)
        contexts = [{"text": c.text[:200], "source": c.source} for c in top_chunks]
        yield ("contexts", contexts)
        yield ("debug", debug)

        user_prompt = build_user_prompt(question, top_chunks, history)
        full_answer = ""
        for delta in self.llm.chat_stream(SYSTEM_PROMPT, user_prompt):
            full_answer += delta
            yield ("text", delta)

        self.sessions.add_message(session_id, "ai", full_answer)
        yield ("done", None)

    # ---------- 会话管理 ----------

    def create_session(self, title: str = None) -> dict:
        self.load()
        if not title:
            title = f"对话 {len(self.sessions.list_sessions()) + 1}"
        sid = self.sessions.create_session(title)
        return {"session_id": sid, "title": title}

    def list_sessions(self) -> list[dict]:
        self.load()
        return self.sessions.list_sessions()

    def get_session_messages(self, session_id: str) -> list[dict]:
        self.load()
        return self.sessions.get_messages(session_id)

    def delete_session(self, session_id: str):
        self.load()
        self.sessions.delete_session(session_id)

    def state(self):
        return {
            "chunks": len(self.chunk_by_id),
            "files": len(self.meta.list_documents()) if self._loaded else 0,
            "sessions": len(self.sessions.list_sessions()) if self._loaded else 0,
        }
