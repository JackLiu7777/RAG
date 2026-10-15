"""
SQLite 元数据存储：记录文档和 chunk 的信息。

为什么用 SQLite？
- 零配置，一个文件就是一个数据库
- 支持 SQL 查询，后续可以按文档、按标签过滤
- FAISS 只存向量不存文本，文本和元数据必须有个地方存
"""
import sqlite3
from datetime import datetime


class MetadataStore:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                doc_id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                chunk_count INTEGER DEFAULT 0,
                uploaded_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chunks (
                chunk_id TEXT PRIMARY KEY,
                doc_id TEXT NOT NULL,
                text TEXT NOT NULL,
                source TEXT NOT NULL,
                chunk_index INTEGER DEFAULT 0,
                FOREIGN KEY (doc_id) REFERENCES documents(doc_id)
            )
        """)
        conn.commit()
        conn.close()

    def add_document(self, doc_id: str, filename: str, chunk_count: int):
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT OR REPLACE INTO documents (doc_id, filename, chunk_count, uploaded_at) VALUES (?, ?, ?, ?)",
            (doc_id, filename, chunk_count, datetime.now().isoformat()),
        )
        conn.commit()
        conn.close()

    def add_chunks(self, chunks: list[tuple]):
        """chunks: [(chunk_id, doc_id, text, source, chunk_index), ...]"""
        conn = sqlite3.connect(self.db_path)
        conn.executemany(
            "INSERT OR REPLACE INTO chunks (chunk_id, doc_id, text, source, chunk_index) VALUES (?, ?, ?, ?, ?)",
            chunks,
        )
        conn.commit()
        conn.close()

    def list_documents(self) -> list[dict]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM documents ORDER BY uploaded_at DESC").fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_all_chunks(self) -> list[dict]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM chunks").fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def delete_document(self, doc_id: str):
        conn = sqlite3.connect(self.db_path)
        conn.execute("DELETE FROM chunks WHERE doc_id = ?", (doc_id,))
        conn.execute("DELETE FROM documents WHERE doc_id = ?", (doc_id,))
        conn.commit()
        conn.close()
