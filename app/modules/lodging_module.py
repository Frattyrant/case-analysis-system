from __future__ import annotations

from datetime import timedelta
from typing import Any

import pandas as pd

from app.modules.base import AnalysisModule
from app.utils.datetime_utils import DateTimeUtils
from app.utils.identity_utils import IdentityUtils


class LodgingQueryAnalysis(AnalysisModule):
    """住宿档案查询模块。"""

    def run(self, state: Any, id_val: str = '', name_val: str = '') -> pd.DataFrame:
        """查询住宿档案。

        Args:
            state: 应用状态对象
            id_val: 身份证号
            name_val: 姓名

        Returns:
            住宿记录 DataFrame
        """
        progress = self._progress()
        progress.step(15, '住宿查询：读取住宿库')

        df_hotel = next(
            (df for fn, df in state['uploaded_frames'].items()
             if any(k in fn for k in ['旅店', '住宿', '旅业'])),
            pd.DataFrame()
        )

        if df_hotel.empty or (not id_val and not name_val):
            progress.error('住宿查询：参数或数据缺失')
            return pd.DataFrame()

        mask = (
            df_hotel['身份证号'].astype(str) == id_val
            if id_val else df_hotel['姓名'] == name_val
        )
        res = df_hotel[mask].copy()

        if res.empty:
            state['current_lodging_res'] = pd.DataFrame()
            progress.finish('住宿查询：无匹配记录')
            return pd.DataFrame()

        progress.step(70, '住宿查询：格式化时间')
        for col in ['入住时间', '退房时间', '真入住时间', '真退房时间']:
            if col in res.columns:
                res[col] = DateTimeUtils.clean_time_format(res[col])

        state['current_lodging_res'] = res
        progress.finish('住宿查询：完成')
        return res


class CohabitAnalysis(AnalysisModule):
    """同住关联分析模块。"""

    def run(self, state: Any) -> pd.DataFrame:
        """执行同住关联分析。

        Args:
            state: 应用状态对象

        Returns:
            同住关联分析结果 DataFrame
        """
        progress = self._progress()
        progress.step(10, '同住分析：读取住宿库')

        df_hotel = next(
            (df for fn, df in state['uploaded_frames'].items()
             if any(k in fn for k in ['旅店', '住宿', '旅业'])),
            pd.DataFrame()
        )

        if df_hotel.empty or state['df_real_car'].empty:
            progress.error('同住分析：前置数据不足')
            return pd.DataFrame()

        suspect_names = state['rental_trajectory_suspects']
        if not suspect_names:
            progress.error('同住分析：缺少租赁轨迹嫌疑人')
            return pd.DataFrame()

        def _to_dt(series: pd.Series) -> pd.Series:
            s = series.astype(str).str.strip().str.replace(r'\.0$', '', regex=True)
            return pd.to_datetime(s, errors='coerce', format='%Y%m%d%H%M')

        all_results = []

        progress.step(35, '同住分析：开始循环匹配')
        for name in suspect_names:
            base = df_hotel[df_hotel['姓名'] == name].copy()
            if base.empty:
                continue

            base['dt'] = _to_dt(base['入住时间'])
            pool = df_hotel.copy()
            pool['dt'] = _to_dt(pool['入住时间'])
            pool = pool.dropna(subset=['dt', '旅馆名称'])

            hits = []
            for _, row in base.iterrows():
                window = pd.Timedelta(hours=24)
                m = (
                    (pool['旅馆名称'] == row['旅馆名称']) &
                    pool['dt'].between(row['dt'] - window, row['dt'] + window)
                )
                h = pool[m].copy()
                h['关联基准人'] = name
                h['同住关系'] = h['姓名'].apply(lambda x: '本人' if x == name else '潜在同行人')
                hits.append(h)

            if not hits:
                continue

            df_final = pd.concat(hits).drop_duplicates(
                subset=['姓名', '身份证号', '入住时间', '旅馆名称']
            )
            df_final['入住时间_标准'] = df_final['dt'].dt.strftime('%Y-%m-%d %H:%M')
            cols = ['姓名', '身份证号', '同住关系', '入住时间_标准', '旅馆名称', '房号', '旅馆地址']
            all_results.append(df_final[cols])

        if all_results:
            progress.finish('同住分析：完成')
            return pd.concat(all_results, ignore_index=True)
        progress.finish('同住分析：无同住记录')
        return pd.DataFrame()



class HotelPreprocessor:
    """住宿数据预处理器。"""

    def preprocess(self, df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
        """预处理住宿数据。

        Args:
            df: 原始住宿数据

        Returns:
            (预处理后的 DataFrame, 警告信息列表)
        """
        warn = []
        df = df.copy()
        ci_col = DateTimeUtils.resolve_best_col(df, '真入住时间', '入住时间')
        df['_checkin_dt'] = DateTimeUtils.robust_to_datetime(df[ci_col]) if ci_col else pd.NaT
        return df, warn


class HotelPenetrationAnalysis(AnalysisModule):
    """住宿渗透分析模块。"""

    _REQUIRED_COLS = {'旅馆地址', '旅馆名称', '姓名', '身份证号'}

    def __init__(self):
        self._preprocessor = HotelPreprocessor()

    def run(self, state: Any) -> pd.DataFrame:
        """执行住宿渗透分析。

        Args:
            state: 应用状态对象

        Returns:
            共同嫌疑人住宿记录 DataFrame
        """
        progress = self._progress()
        progress.step(10, '渗透分析：读取住宿库')

        df_raw = self._get_hotel_df(state)
        if not self._validate(df_raw, state['case_points']):
            progress.error('渗透分析：前置数据不足')
            return pd.DataFrame()

        progress.step(35, '渗透分析：预处理时间字段')
        df_hotel, _ = self._preprocessor.preprocess(df_raw)
        df_valid = df_hotel[df_hotel['_checkin_dt'].notna()].copy()
        
        if state['profile_gender'] or state['profile_region']:
            df_valid = IdentityUtils.apply_filters(df_valid, state['profile_gender'], state['profile_region'])

        progress.step(70, '渗透分析：多案发点交叉')
        point_results = []
        for case_date_str, loc_keyword in state['case_points']:
            target_dt = pd.to_datetime(case_date_str)
            window_start = target_dt - timedelta(days=1)
            loc_mask = (
                df_valid['旅馆地址'].astype(str).str.contains(loc_keyword, na=False) |
                df_valid['旅馆名称'].astype(str).str.contains(loc_keyword, na=False)
            )
            time_mask = df_valid['_checkin_dt'].between(window_start, target_dt)
            hits = df_valid[loc_mask & time_mask].copy()
            hits['关联案发点'] = loc_keyword
            hits['对应案发日期'] = case_date_str
            hits['筛选时间窗口'] = f'{window_start.date()} ~ {target_dt.date()}'
            point_results.append(hits)

        if not point_results:
            return pd.DataFrame()

        intersection_ids = set(point_results[0]['身份证号'].unique())
        for res in point_results[1:]:
            intersection_ids &= set(res['身份证号'].unique())

        if not intersection_ids:
            progress.finish('渗透分析：无交集嫌疑人')
            return pd.DataFrame()

        df_all_hits = pd.concat(point_results, ignore_index=True)
        df_final = df_all_hits[df_all_hits['身份证号'].isin(intersection_ids)].copy()

        progress.finish('渗透分析：完成')
        return df_final

    def _get_hotel_df(self, state: Any) -> pd.DataFrame:
        """获取住宿数据。"""
        for fname, df in state['uploaded_frames'].items():
            if any(k in fname for k in ['旅店', '住宿', '旅业']):
                return df.copy()
        return pd.DataFrame()

    def _validate(self, df_raw: pd.DataFrame, case_points: list) -> bool:
        """验证数据是否有效。"""
        if not case_points or df_raw.empty:
            return False
        return True