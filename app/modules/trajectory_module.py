from __future__ import annotations

import re
from datetime import timedelta
from typing import Any

import pandas as pd

from app.modules.base import AnalysisModule


class PlateSearchAnalysis(AnalysisModule):
    """车牌模糊查询分析模块。"""

    def run(self, state: Any, pattern: str = '') -> pd.DataFrame:
        """执行车牌模糊查询。

        Args:
            state: 应用状态对象
            pattern: 车牌号片段

        Returns:
            匹配的轨迹记录 DataFrame
        """
        progress = self._progress()
        progress.step(10, '车牌搜索：读取轨迹库')

        df_track = next(
            (df for fn, df in state['uploaded_frames'].items() if '轨迹' in fn),
            None
        )
        
        if df_track is None or not pattern:
            progress.error('车牌搜索：参数或数据缺失')
            return pd.DataFrame()

        progress.step(45, '车牌搜索：执行模糊匹配')
        pattern_upper = pattern.upper()
        regex = '.*'.join(re.escape(c) for c in pattern_upper)
        regex = f'.*{regex}.*'

        mask = df_track['号牌号码'].str.upper().str.contains(regex, na=False, regex=True)
        result = df_track[mask].sort_values('通过时间', ascending=False).copy()

        state['matched_trajectories'] = result
        state['matched_plates'] = list(result['号牌号码'].unique())

        progress.finish('车牌搜索：完成')
        return result


class SpatialPenetrationAnalysis(AnalysisModule):
    """时空分析模块。"""

    def run(self, state: Any, buffer_days: int = 0) -> pd.DataFrame:
        """执行时空分析。

        Args:
            state: 应用状态对象
            buffer_days: 扩大搜索时间（案发前后增加的天数）

        Returns:
            关联轨迹记录 DataFrame
        """
        progress = self._progress()
        progress.step(10, '时空分析：读取轨迹库')

        df_track = next(
            (df for fn, df in state['uploaded_frames'].items() if '轨迹' in fn),
            None
        )
        
        if not state['case_points'] or df_track is None or not state['matched_plates']:
            progress.error('时空分析：前置数据不足')
            return pd.DataFrame()

        progress.step(40, '时空分析：计算时间窗口')
        dates = [pd.to_datetime(p[0]) for p in state['case_points']]
        start = min(dates) - timedelta(days=buffer_days)
        end = max(dates) + timedelta(days=buffer_days)

        cities = [p[1] for p in state['case_points']]
        loc_re = '|'.join(cities)

        progress.step(75, '时空分析：筛选轨迹')
        df_track = df_track.copy()
        df_track['通过时间'] = pd.to_datetime(df_track['通过时间'])
        mask = (
            df_track['号牌号码'].isin(state['matched_plates']) &
            df_track['通过时间'].between(start, end) &
            (
                df_track['卡口名称'].str.contains(loc_re, na=False) |
                df_track['行政区域'].str.contains(loc_re, na=False)
            )
        )
        result = df_track[mask].sort_values('通过时间').copy()

        progress.finish('时空分析：完成')
        return result