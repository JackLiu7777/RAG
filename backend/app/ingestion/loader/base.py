"""
所有文件解析器必须遵守的"接口规范"。

为什么用抽象基类（ABC）？
- 它只是一个"规定"，不写具体逻辑
- 任何新格式的解析器，只要继承 BaseParser 并实现 parse()，
  就能被系统自动识别使用，主流程一行代码都不用改
- 这就是"可扩展"在代码层面的体现
"""

from abc import ABC, abstractmethod
from pathlib import Path

from app.core.schemas import Document


class BaseParser(ABC):
    """所有解析器的统一接口。"""

    # 子类自己声明支持哪些扩展名
    SUPPORTED_EXT: set[str] = set()

    @abstractmethod
    def parse(self, file_path: Path) -> list[Document]:
        """把一个文件解析成一个或多个 Document。子类必须实现。"""
        ...
