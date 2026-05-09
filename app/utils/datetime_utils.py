from __future__ import annotations

from typing import Optional

import pandas as pd


class DateTimeUtils:
    """日期时间工具类，提供多种日期格式的解析和转换功能。
    全部使用向量化操作，避免逐行 .apply() 性能瓶颈。
    """

    _FORMATS = ('%Y%m%d%H%M%S', '%Y%m%d%H%M', '%Y%m%d', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d')

    @classmethod
    def robust_to_datetime(cls, series: pd.Series) -> pd.Series:
        """向量化日期转换：逐格式尝试 pd.to_datetime(series, format=fmt)，
        每个格式在整个Series上做一次C级向量化解析，比逐行 .apply() 快 50-100x。

        Args:
            series: 包含日期字符串的 Series

        Returns:
            转换后的 datetime Series
        """
        if pd.api.types.is_datetime64_any_dtype(series):
            return series

        # 预处理: 去 .0 后缀
        s = series.astype(str).str.strip().str.replace(r'\.0$', '', regex=True)

        result = pd.Series(pd.NaT, index=s.index, dtype='datetime64[ns]')
        remaining = pd.Series(True, index=s.index)  # 尚未解析的行

        # 逐个格式尝试，只处理剩余未解析的行（越来越快）
        for fmt in cls._FORMATS:
            if not remaining.any():
                break
            idx = remaining[remaining].index
            parsed = pd.to_datetime(s.loc[idx], format=fmt, errors='coerce')
            resolved = parsed.notna()
            result.loc[parsed[resolved].index] = parsed[resolved]
            remaining.loc[parsed[resolved].index] = False

        # 兜底: pandas 自动推断
        if remaining.any():
            idx = remaining[remaining].index
            result.loc[idx] = pd.to_datetime(s.loc[idx], errors='coerce')

        return result

    @classmethod
    def clean_time_format(cls, series: pd.Series) -> pd.Series:
        """统一格式化为 YYYY-MM-DD HH:MM。"""
        s = series.astype(str).str.strip().str.replace(r'\.0$', '', regex=True)
        for fmt in cls._FORMATS:
            parsed = pd.to_datetime(s, format=fmt, errors='coerce')
            if parsed.notna().sum() > 0:
                return parsed.dt.strftime('%Y-%m-%d %H:%M')
        return pd.to_datetime(s, errors='coerce').dt.strftime('%Y-%m-%d %H:%M')

    @classmethod
    def fmt_date(cls, series: pd.Series) -> pd.Series:
        """格式化为 YYYY-MM-DD 日期字符串。"""
        return pd.to_datetime(series, errors='coerce').dt.strftime('%Y-%m-%d').fillna('')

    @classmethod
    def resolve_best_col(cls, df: pd.DataFrame, preferred: str, fallback: str) -> Optional[str]:
        """从两个候选列中选出日期数据质量更好的那个。
        用向量化解析做质量检查，避免调用 robust_to_datetime（省掉额外全表扫描）。
        """
        for col in (preferred, fallback):
            if col in df.columns:
                s = df[col].astype(str).str.strip().str.replace(r'\.0$', '', regex=True)
                valid = pd.to_datetime(s, errors='coerce').notna().sum()
                if valid > len(df) * 0.3:
                    return col
        return None
