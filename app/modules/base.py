from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import pandas as pd


class DataSource(ABC):
    """数据源抽象基类，定义数据加载和 Schema 应用的接口。"""

    @abstractmethod
    def load(self, content: bytes, filename: str) -> pd.DataFrame:
        """加载文件内容为 DataFrame。

        Args:
            content: 文件二进制内容
            filename: 文件名

        Returns:
            解析后的 DataFrame
        """
        pass

    @abstractmethod
    def apply_schema(self, df: pd.DataFrame, filename: str) -> tuple[pd.DataFrame, bool]:
        """应用 Schema 到 DataFrame。

        Args:
            df: 原始 DataFrame
            filename: 文件名

        Returns:
            (应用 Schema 后的 DataFrame, 是否成功)
        """
        pass


class AnalysisModule(ABC):
    """分析模块抽象基类，定义分析逻辑的接口。"""

    def set_progress_driver(self, driver: Any) -> None:
        """挂载进度驱动器，兼容不同 UI 层实现。"""
        self._progress_driver = driver

    def _progress(self) -> Any:
        """获取已挂载进度驱动器；未挂载时返回空实现。"""
        from app.utils.loading_visualizer import LoadingDriver
        return getattr(self, '_progress_driver', LoadingDriver.noop())

    @abstractmethod
    def run(self, state: Any) -> pd.DataFrame:
        """执行分析逻辑。

        Args:
            state: 应用状态对象

        Returns:
            分析结果 DataFrame
        """
        pass


class UploadModule(ABC):
    """上传模块抽象基类，定义文件上传处理的接口。"""

    @abstractmethod
    def handle_upload(self, content: bytes, filename: str, state: Any) -> bool:
        """处理文件上传。

        Args:
            content: 文件二进制内容
            filename: 文件名
            state: 应用状态对象

        Returns:
            是否成功处理
        """
        pass