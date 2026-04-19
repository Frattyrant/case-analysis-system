from __future__ import annotations

from typing import Any

import pandas as pd

from app.modules.base import AnalysisModule


class RentalAnalysis(AnalysisModule):
    """租赁全库分析模块。"""

    def __init__(self) -> None:
        self.last_diag = ""

    def run(self, state: Any) -> pd.DataFrame:
        """执行租赁分析。

        Args:
            state: 应用状态对象

        Returns:
            符合条件的租车名单 DataFrame
        """
        self.last_diag = ""
        progress = self._progress()
        progress.step(10, '租赁分析：读取数据')

        df_rental = next(
            (df for fn, df in state['uploaded_frames'].items() if '租赁' in fn),
            pd.DataFrame()
        )
        df_track = next(
            (df for fn, df in state['uploaded_frames'].items() if '轨迹' in fn),
            pd.DataFrame()
        )

        if not state['case_points']:
            self.last_diag = '请先在「案件信息」中「确认添加」案发日期与地点。'
            progress.error('租赁分析：缺少前置数据')
            return pd.DataFrame()
        if df_rental.empty:
            self.last_diag = '未找到文件名包含「租赁」的已上传表。'
            progress.error('租赁分析：缺少前置数据')
            return pd.DataFrame()

        progress.step(35, '租赁分析：计算时间窗口')
        case_dates = sorted(pd.to_datetime(p[0]) for p in state['case_points'])
        earliest, latest = case_dates[0], case_dates[-1]

        df_rental = df_rental.copy()
        df_rental['起租时间'] = pd.to_datetime(df_rental['起租时间'], errors='coerce')
        df_rental['停租时间'] = pd.to_datetime(df_rental['停租时间'], errors='coerce')

        progress.step(60, '租赁分析：过滤租赁记录')
        mask = (df_rental['起租时间'] <= earliest) & (df_rental['停租时间'] >= latest)
        if state['rental_company']:
            mask &= df_rental['租赁公司名称'].str.contains(state['rental_company'], na=False)
        if state['car_brand']:
            mask &= df_rental['车辆品牌'].astype(str) == state['car_brand']

        df_confirmed = df_rental[mask].copy()

        if df_confirmed.empty:
            self.last_diag = (
                '无租赁记录同时满足：起租≤首案日、停租≥末案日'
                + ('，且租赁公司/品牌筛选' if (state['rental_company'] or state['car_brand']) else '')
                + '。可适当放宽「租赁公司」「车辆品牌」或核对案发时间范围。'
            )
            progress.finish('租赁分析：无匹配记录')
            return pd.DataFrame()

        state['df_real_car'] = df_confirmed

        progress.step(85, '租赁分析：碰撞轨迹')
        if not df_track.empty:
            df_track = df_track.copy()
            df_track['通过时间'] = pd.to_datetime(df_track['通过时间'], errors='coerce')
            merged = pd.merge(
                df_confirmed[['号牌号码', '租车人姓名', '租车人身份证号码', '起租时间', '停租时间']],
                df_track[['号牌号码', '通过时间', '卡口名称', '行政区域']],
                on='号牌号码', how='inner'
            )
            merged = merged[
                (merged['通过时间'] >= merged['起租时间']) &
                (merged['通过时间'] <= merged['停租时间'])
            ]
            if not merged.empty:
                state['rental_trajectory_suspects'] = list(merged['租车人姓名'].unique())

        progress.finish('租赁分析：完成')
        return df_confirmed