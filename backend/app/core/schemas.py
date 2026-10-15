"""
全系统统一的数据结构。
所有模块之间只通过这两个东西传数据，不互相关心对方内部怎么实现。
"""

from uuid import uuid4
from pydantic import BaseModel, Field


class Document(BaseModel):
    """一个原始文件解析后的整体结构。"""

    doc_id: str = Field(default_factory=lambda: uuid4().hex[:12])
    filename: str                       # 原始文件名，如"员工手册.pdf"
    text: str                           # 解析出的全文
    metadata: dict = Field(default_factory=dict)
    # 额外信息，如 pdf 总页数、检测到的编码等


class Chunk(BaseModel):
    """文本切分后的一块。下游 embedding 和检索都以它为单位。"""

    chunk_id: str = Field(default_factory=lambda: uuid4().hex[:12])
    doc_id: str                         # 属于哪个文档（外键）
    text: str                           # 这一块的文字
    source: str                         # 人类可读来源："员工手册.pdf 第12页"
    chunk_index: int = 0                # 在文档里是第几块
