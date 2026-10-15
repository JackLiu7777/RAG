"""
Step 3 验证脚本：解析一个文件 → 切成块 → 打印每一块。
用法（在 backend 目录下）：
    python chunk_demo.py ../demo.txt
"""

import sys
from pathlib import Path

from app.core.config import get_settings
from app.ingestion.chunker.factory import get_chunker
from app.ingestion.loader.registry import get_parser


def main() -> None:
    if len(sys.argv) < 2:
        print("用法：python chunk_demo.py <文件路径>")
        return

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"文件不存在：{path}")
        return

    # 第一步：解析
    doc = get_parser(path).parse(path)[0]

    # 第二步：切块
    settings = get_settings()
    chunks = get_chunker().split(doc)

    print(f"原文总字数: {len(doc.text)}")
    print(f"配置: chunk_size={settings.ingestion.chunk_size}, "
          f"overlap={settings.ingestion.chunk_overlap}")
    print(f"切出 {len(chunks)} 块\n")

    for i, c in enumerate(chunks):
        print(f"--- Chunk {i}（{len(c.text)} 字）---")
        print(c.text.replace("\n", " ")[:120])
        print()


if __name__ == "__main__":
    main()
