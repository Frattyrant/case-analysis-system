from __future__ import annotations

import warnings
from typing import Optional

import pandas as pd


class DateTimeUtils:
    """日期时间工具类，提供多种日期格式的解析和转换功能。"""

    _FORMATS = ('%Y%m%d%H%M%S', '%Y%m%d%H%M', '%Y%m%d', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d')

    @classmethod
    def robust_to_datetime(cls, series: pd.Series) -> pd.Series:
        """日期转换，兼容各种格式。

        Args:
            series: 包含日期字符串的 Series

        Returns:
            转换后的 datetime Series
        """
        warnings.filterwarnings('ignore', category=UserWarning)
        if pd.api.types.is_datetime64_any_dtype(series):
            return series

        def _parse(v):
            s = str(v).strip().replace('.0', '')
            if not s or s == 'nan':
                return pd.NaT
            for fmt in cls._FORMATS:
                try:
                    res = pd.to_datetime(s, format=fmt)
                    if not pd.isna(res):
                        return res
                except:
                    continue
            return pd.to_datetime(s, errors='coerce')

        return series.apply(_parse)

    @classmethod
    def clean_time_format(cls, series: pd.Series) -> pd.Series:
        """统一格式化为 YYYY-MM-DD HH:MM。

        Args:
            series: 包含日期字符串的 Series

        Returns:
            格式化后的字符串 Series
        """
        s = series.astype(str).str.strip().str.replace(r'\.0$', '', regex=True)
        for fmt in cls._FORMATS:
            parsed = pd.to_datetime(s, format=fmt, errors='coerce')
            if parsed.notna().sum() > 0:
                return parsed.dt.strftime('%Y-%m-%d %H:%M')
        return pd.to_datetime(s, errors='coerce').dt.strftime('%Y-%m-%d %H:%M')

    @classmethod
    def fmt_date(cls, series: pd.Series) -> pd.Series:
        """格式化为 YYYY-MM-DD 日期字符串。

        Args:
            series: 包含日期的 Series

        Returns:
            格式化后的日期字符串 Series
        """
        return pd.to_datetime(series, errors='coerce').dt.strftime('%Y-%m-%d').fillna('')

    @classmethod
    def resolve_best_col(cls, df: pd.DataFrame, preferred: str, fallback: str) -> Optional[str]:
        """从两个候选列中选出日期数据质量更好的那个。

        Args:
            df: 数据框
            preferred: 优先选择的列名
            fallback: 备选列名

        Returns:
            数据质量更好的列名，如果没有则返回 None
        """
        for col in (preferred, fallback):
            if col in df.columns:
                if cls.robust_to_datetime(df[col]).notna().sum() > len(df) * 0.3:
                    return col
        return None