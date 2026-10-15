"""
OpenAI 兼容协议的 LLM 客户端。
智谱、DeepSeek、通义、豆包都兼容这个协议，换厂商只改 base_url 和 model 名。
"""

from collections.abc import Iterator

from openai import OpenAI

from app.llm.base import BaseLLMClient


class OpenAICompatClient(BaseLLMClient):
    def __init__(self, api_key: str, base_url: str, model: str, temperature: float = 0.1):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.temperature = temperature

    def chat(self, system: str, user: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=self.temperature,
        )
        return response.choices[0].message.content or ""

    def chat_stream(self, system: str, user: str) -> Iterator[str]:
        """流式调用：每 yield 一段增量文本。"""
        stream = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=self.temperature,
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta
