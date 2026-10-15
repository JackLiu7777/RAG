"""
LLM 客户端接口。
以后换 DeepSeek、通义、私有部署模型，只要实现这个接口。
"""

from abc import ABC, abstractmethod
from collections.abc import Iterator


class BaseLLMClient(ABC):
    @abstractmethod
    def chat(self, system: str, user: str) -> str:
        """给定 system 和 user 消息，返回完整回答。"""
        ...

    @abstractmethod
    def chat_stream(self, system: str, user: str) -> Iterator[str]:
        """流式版本：逐段 yield 回答内容。"""
        ...
