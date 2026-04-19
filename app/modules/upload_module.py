from __future__ import annotations

import io
from typing import Any

import pandas as pd

from app.modules.base import DataSource


def _is_ooxml_zip(content: bytes) -> bool:
    """是否为 Office Open XML（.xlsx 内核）；部分系统误用 .xls 扩展名。"""
    return len(content) >= 2 and content[:2] == b"PK"


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
            lower = filename.lower()
            if lower.endswith(".xlsx"):
                df = pd.read_excel(io.BytesIO(content), engine="openpyxl")
            elif lower.endswith(".xls"):
                df = self._load_xls(content, filename)
            elif lower.endswith(".csv"):
                last_err: Exception | None = None
                for enc in ('utf-8-sig', 'utf-8', 'gb18030', 'gbk', 'cp936'):
                    try:
                        df = pd.read_csv(io.BytesIO(content), encoding=enc)
                        break
                    except Exception as e:
                        last_err = e
                else:
                    raise ValueError(
                        f"CSV 编码无法识别（已尝试 utf-8/gb18030/gbk 等）: {last_err}"
                    ) from last_err
            else:
                raise ValueError(f"不支持的文件格式: {filename}")
            
            return df
        except Exception as e:
            raise ValueError(f"解析文件 {filename} 失败: {str(e)}") from e

    def _load_xls_as_html(self, content: bytes, filename: str) -> pd.DataFrame:
        """公安/政务系统常见：扩展名为 .xls，实为 HTML/XML 表格。"""
        last: Exception | None = None
        for enc in ("gb18030", "gbk", "utf-8-sig", "utf-8", "cp936"):
            try:
                text = content.decode(enc)
            except UnicodeDecodeError as e:
                last = e
                continue
            stripped = text.lstrip("\ufeff").lstrip()
            low = stripped[:8000].lower()
            if "<table" not in low and "<html" not in low:
                continue
            try:
                tables = pd.read_html(
                    io.StringIO(text),
                    displayed_only=False,
                    flavor="lxml",
                )
            except ImportError as e:
                raise ValueError(
                    "解析 HTML 型 .xls 需要安装 lxml：pip install lxml"
                ) from e
            except Exception as e:
                last = e
                continue
            if not tables:
                continue
            return max(tables, key=lambda d: d.shape[0] * max(d.shape[1], 1))
        if last:
            raise ValueError(f"按 HTML 表格解析 {filename} 失败: {last}") from last
        raise ValueError(
            f"{filename} 不是 xlrd 可读的二进制 .xls，也未检测到 HTML 表格内容"
        )

    def _load_xls(self, content: bytes, filename: str) -> pd.DataFrame:
        if _is_ooxml_zip(content):
            return pd.read_excel(io.BytesIO(content), engine="openpyxl")
        try:
            return pd.read_excel(io.BytesIO(content), engine="xlrd")
        except Exception as e_xlrd:
            try:
                return self._load_xls_as_html(content, filename)
            except Exception as e_html:
                raise ValueError(
                    f".xls 读取失败（已尝试二进制表与 HTML 表）：xlrd: {e_xlrd}; html: {e_html}"
                ) from e_html

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
                n = len(cols)
                if len(result.columns) > n:
                    result = result.iloc[:, :n].copy()
                elif len(result.columns) < n:
                    return df, False
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
            处理结果统计：succeeded、failed、total_files（本批文件数）、errors（失败明细）、
            frames_in_state（当前案件中已载入的表格数）。
        """
        succeeded = 0
        failed = 0
        errors: list[str] = []
        per_file_rows: dict[str, int] = {}

        for filename, content in files.items():
            try:
                raw_df = self.load(content, filename)
                df, matched = self.apply_schema(raw_df, filename)
                state["uploaded_frames"][filename] = df
                per_file_rows[filename] = len(df)
                succeeded += 1
            except Exception as e:
                failed += 1
                errors.append(f"{filename}: {e}")

        return {
            'succeeded': succeeded,
            'failed': failed,
            'total_files': len(files),
            'errors': errors,
            'frames_in_state': len(state["uploaded_frames"]),
            'per_file_rows': per_file_rows,
        }