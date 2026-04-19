from __future__ import annotations

import io
from typing import Any

import pandas as pd

from app.modules.base import DataSource


class FileDataSource(DataSource):
    """文件数据源，提供 Excel/CSV 文件的加载和 Schema 映射功能。"""

    _SCHEMAS = {
        '航班': ['航班日期', '航班号', '姓名', '身份证号', '到达地'],
        '轨迹': ['号牌号码', '通过时间', '卡口名称', '行政区域'],
        '机动车': ['号牌号码', '所有人', '身份证号', '车辆品牌'],
        '租赁': ['号牌号码', '租车人姓名', '租车人身份证号码', '起租时间', '停租时间', '租赁公司名称', '车辆品牌'],
        '旅店': ['姓名', '身份证号', '入住时间', '退房时间', '旅馆名称', '房号', '旅馆地址'],
        '住宿': ['姓名', '身份证号', '入住时间', '退房时间', '旅馆名称', '房号', '旅馆地址'],
        '旅业': ['姓名', '身份证号', '入住时间', '退房时间', '旅馆名称', '房号', '旅馆地址'],
    }

    _KEEP_COLUMNS = {
        '航班': ['航班日期', '航班号', '姓名', '身份证号', '到达地'],
        '轨迹': ['号牌号码', '通过时间', '卡口名称', '行政区域'],
        '机动车': ['号牌号码', '所有人', '身份证号', '车辆品牌'],
        '租赁': ['号牌号码', '租车人姓名', '租车人身份证号码', '起租时间', '停租时间', '租赁公司名称', '车辆品牌'],
    }

    def load(self, content: bytes, filename: str) -> pd.DataFrame:
        """加载文件内容为 DataFrame。

        Args:
            content: 文件二进制内容
            filename: 文件名

        Returns:
            解析后的 DataFrame

        Raises:
            ValueError: 如果文件格式不支持或解析失败
        """
        try:
            file_stream = io.BytesIO(content)
            
            if filename.lower().endswith(('.xls', '.xlsx')):
                df = pd.read_excel(file_stream, engine='openpyxl' if filename.lower().endswith('.xlsx') else 'xlrd')
            elif filename.lower().endswith('.csv'):
                df = pd.read_csv(file_stream, encoding='utf-8-sig')
            else:
                raise ValueError(f"不支持的文件格式: {filename}")
            
            return df
        except Exception as e:
            raise ValueError(f"解析文件 {filename} 失败: {str(e)}") from e

    def apply_schema(self, df: pd.DataFrame, filename: str) -> tuple[pd.DataFrame, bool]:
        """应用 Schema 映射到 DataFrame。

        Args:
            df: 原始 DataFrame
            filename: 文件名

        Returns:
            (应用 Schema 后的 DataFrame, 是否匹配到 Schema)
        """
        for key, cols in self._SCHEMAS.items():
            if key in filename:
                result = df.copy()
                result.columns = cols
                if key in self._KEEP_COLUMNS:
                    result = result[self._KEEP_COLUMNS[key]]
                return result, True
        return df, False

    def process_files(self, files: dict[str, bytes], state: Any) -> dict[str, Any]:
        """处理多个文件并更新状态。

        Args:
            files: 文件字典 {filename: content}
            state: 应用状态对象

        Returns:
            处理结果统计 {'succeeded': int, 'failed': int, 'total_files': int}
        """
        succeeded = 0
        failed = 0

        for filename, content in files.items():
            try:
                raw_df = self.load(content, filename)
                df, matched = self.apply_schema(raw_df, filename)
                state["uploaded_frames"][filename] = df
                succeeded += 1
            except Exception:
                failed += 1

        return {
            'succeeded': succeeded,
            'failed': failed,
            'total_files': len(state["uploaded_frames"])
        }