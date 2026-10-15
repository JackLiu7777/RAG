"""
全局配置加载中心。

两件事：
1. 从 .env 读敏感信息（API Key）——这文件不进 git，Key 不泄露
2. 从 configs/settings.yaml 读业务参数——模型名、召回数、切块大小

设计原则：代码里任何地方需要配置，都来这里拿，不写死。
"""

from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

# config.py 位于 backend/app/core/，往上数三层就是项目根目录
PROJECT_ROOT = Path(__file__).resolve().parents[3]


class _Secrets(BaseSettings):
    """从 .env 读取的敏感信息。"""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    zhipu_api_key: str = ""
    bocha_api_key: str = ""


class AppConfig(BaseModel):
    name: str = "Local RAG Demo"
    host: str = "127.0.0.1"
    port: int = 8000
    data_dir: str = "data"


class IngestionConfig(BaseModel):
    chunk_size: int = 500
    chunk_overlap: int = 80


class RetrievalConfig(BaseModel):
    top_k_per_channel: int = 5
    rerank_top_n: int = 3
    mode: str = "rrf"
    rrf_k: int = 60
    rrf_top_candidates: int = 10


class EmbeddingConfig(BaseModel):
    model_name: str = "BAAI/bge-large-zh-v1.5"
    device: str = "cpu"


class RerankerConfig(BaseModel):
    model_name: str = "BAAI/bge-reranker-v2-m3"
    device: str = "cpu"


class LLMConfig(BaseModel):
    provider: str = "zhipu"
    model: str = "glm-4-flash"
    base_url: str = "https://open.bigmodel.cn/api/paas/v4"
    temperature: float = 0.1


class Settings(BaseModel):
    app: AppConfig = AppConfig()
    ingestion: IngestionConfig = IngestionConfig()
    retrieval: RetrievalConfig = RetrievalConfig()
    embedding: EmbeddingConfig = EmbeddingConfig()
    reranker: RerankerConfig = RerankerConfig()
    llm: LLMConfig = LLMConfig()
    secrets: _Secrets = _Secrets()


@lru_cache
def get_settings() -> Settings:
    """读取配置并缓存。整个应用生命周期只加载一次。"""
    yaml_path = PROJECT_ROOT / "configs" / "settings.yaml"
    raw = {}
    if yaml_path.exists():
        raw = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
    return Settings(**raw)
