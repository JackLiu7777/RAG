"""
FastAPI 入口：文件管理 + 会话管理 + 流式问答。
"""
import json
import shutil
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app.core.config import get_settings
from app.pipeline import RAGPipeline

settings = get_settings()
app = FastAPI(title=settings.app.name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

pipeline = RAGPipeline()
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


@app.on_event("startup")
def startup():
    pipeline.load()


@app.get("/health")
def health():
    return {"status": "ok", "app": settings.app.name}


# ---------- 文件管理 ----------

@app.post("/api/upload")
async def upload(file: UploadFile = File(...)):
    save_path = UPLOAD_DIR / file.filename
    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return pipeline.ingest_file(save_path)


@app.get("/api/files")
def list_files():
    return pipeline.list_files()


@app.delete("/api/files/{doc_id}")
def delete_file(doc_id: str):
    return pipeline.delete_file(doc_id)


# ---------- 会话管理 ----------

@app.get("/api/sessions")
def list_sessions():
    return pipeline.list_sessions()


@app.post("/api/sessions")
def create_session(req: dict = None):
    title = (req or {}).get("title")
    return pipeline.create_session(title)


@app.get("/api/sessions/{session_id}/messages")
def get_messages(session_id: str):
    return pipeline.get_session_messages(session_id)


@app.delete("/api/sessions/{session_id}")
def delete_session(session_id: str):
    pipeline.delete_session(session_id)
    return {"deleted": True}


@app.put("/api/sessions/{session_id}")
def rename_session(session_id: str, req: dict):
    title = req.get("title", "").strip()
    if title:
        pipeline.sessions.rename_session(session_id, title)
    return {"ok": True}


# ---------- 问答 ----------

@app.post("/api/chat/stream")
async def chat_stream(req: dict):
    question = req.get("question", "")
    session_id = req.get("session_id", "")
    if not question or not session_id:
        return StreamingResponse(iter([]), media_type="text/event-stream")

    def event_generator():
        for evt_type, data in pipeline.ask_stream(question, session_id):
            yield f"data: {json.dumps({'type': evt_type, 'data': data}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/state")
def state():
    return pipeline.state()
