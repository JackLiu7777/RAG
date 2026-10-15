"""
纯文本 / Markdown 解析器。

为什么要自动检测编码？
- Windows 上 txt 经常是 GBK 存的，Mac/Linux 一般是 UTF-8
- 直接 open(path, encoding="utf-8") 读 GBK 文件会乱码或报错
- chardet 自动猜一下编码，最稳
"""

from pathlib import Path

import chardet

from app.core.schemas import Document
from app.ingestion.loader.base import BaseParser


class TxtParser(BaseParser):
    SUPPORTED_EXT = {".txt", ".md"}

    def parse(self, file_path: Path) -> list[Document]:
        # 先按字节读进来，让 chardet 猜编码
        raw = file_path.read_bytes()
        guess = chardet.detect(raw)
        encoding = guess.get("encoding") or "utf-8"
        # errors="replace" 万一还有个别字节解不开，替换成 ? 而不是崩溃
        text = raw.decode(encoding, errors="replace")

        return [
            Document(
                filename=file_path.name,
                text=text,
                metadata={"encoding": encoding, "char_count": len(text)},
            )
        ]
