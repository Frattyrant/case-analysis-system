# app/modules/trajectory_module.py
import re
import pandas as pd
from typing import Any

class PlateSearchAnalysis:
    """车牌模糊查询分析模块。"""
    def __init__(self):
        pass

    def run(self, state: Any, pattern: str = '') -> pd.DataFrame:
        df_track = next((df for fn, df in state['uploaded_frames'].items() if '轨迹' in fn), None)

        if df_track is None:
            raise ValueError("未找到轨迹数据文件，请先上传！")
        if not pattern:
            raise ValueError("请输入需要查询的车牌号片段！")

        pattern_upper = pattern.upper()
        regex = '.*'.join(re.escape(c) for c in pattern_upper)
        regex = f'.*{regex}.*'

        mask = df_track['号牌号码'].str.upper().str.contains(regex, na=False, regex=True)
        result = df_track[mask].sort_values('通过时间', ascending=False).copy()

        state['matched_plates'] = list(result['号牌号码'].unique())

        return result


class SpatialPenetrationAnalysis:
    """扩展时段轨迹筛查模块（原"扩大时间搜索"）。
    用户选择起始/结束日期，对模糊匹配的车牌进行轨迹筛查。
    未指定日期时回退到案发点首末时间。
    """
    def __init__(self):
        pass

    def run(self, state: Any, start_date: str = '', end_date: str = '') -> pd.DataFrame:
        df_track = next((df for fn, df in state['uploaded_frames'].items() if '轨迹' in fn), None)

        if not state['case_points']:
            raise ValueError("请先在基础信息模块录入案发城市和日期。")
        if df_track is None:
            raise ValueError("未检测到轨迹数据库。")
        if not state['matched_plates']:
            raise ValueError("当前无锁定的嫌疑车牌，请先执行车牌模糊搜索！")

        # 未指定日期时回退到案发点首末时间；结束日期归一化到当天23:59:59
        if start_date and end_date:
            start = pd.to_datetime(start_date)
            end = pd.to_datetime(end_date) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
        else:
            dates = [pd.to_datetime(p[0]) for p in state['case_points']]
            start = min(dates)
            end = max(dates) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)

        cities = [p[1] for p in state['case_points']]
        loc_re = '|'.join(cities)

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
        return result
