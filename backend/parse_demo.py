"""
Step 2 验证脚本：给它一个文件路径，看解析结果对不对。
用法（在 backend 目录下）：
    python parse_demo.py ../demo.txt
"""

import sys
from pathlib import Path

from app.ingestion.loader.registry import get_parser


def main() -> None:
    if len(sys.argv) < 2:
        print("用法：python parse_demo.py <文件路径>")
        return

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"文件不存在：{path}")
        return

    parser = get_parser(path)
    print(f"[使用解析器] {type(parser).__name__}")

    docs = parser.parse(path)
    print(f"[解析出 {len(docs)} 个 Document]\n")

    for d in docs:
        print(f"文件名:    {d.filename}")
        print(f"doc_id:    {d.doc_id}")
        print(f"元数据:    {d.metadata}")
        print(f"总字数:    {len(d.text)}")
        print("--- 前 200 字预览 ---")
        print(d.text[:200])
        print("-" * 40)


if __name__ == "__main__":
    main()
