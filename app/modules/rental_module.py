from __future__ import annotations

from typing import Any

import pandas as pd

from app.modules.base import AnalysisModule


def _id_key(s: Any) -> str:
    if pd.isna(s):
        return ""
    if isinstance(s, float):
        if abs(s) >= 1e15:
            return f"{s:.0f}"
        if s == int(s):
            return str(int(s))
    t = str(s).strip()
    if t.endswith(".0") and len(t) > 2 and t[:-2].isdigit():
        return t[:-2]
    return t


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
        if state['rental_company']:
            df_rental = df_rental[
                df_rental['租赁公司名称'].str.contains(state['rental_company'], na=False)
            ].copy()
        if state['car_brand']:
            df_rental = df_rental[
                df_rental['车辆品牌'].astype(str) == state['car_brand']
            ].copy()

        if df_rental.empty:
            self.last_diag = '无租赁记录通过当前「租赁公司」「车辆品牌」筛选。'
            progress.finish('租赁分析：无匹配记录')
            return pd.DataFrame()

        flight_x = state['flight_suspect_cross']
        use_flight = (
            isinstance(flight_x, pd.DataFrame)
            and not flight_x.empty
            and '航班日期_进入' in flight_x.columns
            and '身份证号' in flight_x.columns
        )

        if use_flight:
            # 业务规则：起租须在航班「进入」案发区域日期之前或当日（不晚于抵达日）；停租仍须覆盖末案日。
            # 与 demo 中仅用案发 earliest 不同，此处以航班碰撞表为准。
            fk = flight_x[['身份证号', '航班日期_进入']].copy()
            fk['身份证号'] = fk['身份证号'].map(_id_key)
            fk['航班日期_进入'] = pd.to_datetime(fk['航班日期_进入'], errors='coerce')
            fk = fk.dropna(subset=['身份证号', '航班日期_进入'])
            fk = fk.groupby('身份证号', as_index=False)['航班日期_进入'].min()

            df_rental['_rid'] = df_rental['租车人身份证号码'].map(_id_key)
            merged = df_rental.merge(fk, left_on='_rid', right_on='身份证号', how='inner')
            merged = merged.drop(columns=['身份证号'], errors='ignore')

            if merged.empty:
                self.last_diag = (
                    '已有航班碰撞结果，但租车人身份证号与航班嫌疑人表无交集；'
                    '请确认租赁表与航班分析为同一批嫌疑人。'
                )
                progress.finish('租赁分析：无匹配记录')
                return pd.DataFrame()

            t_enter = pd.to_datetime(merged['航班日期_进入'], errors='coerce').dt.normalize()
            t_start = pd.to_datetime(merged['起租时间'], errors='coerce').dt.normalize()
            mask_ok = (t_start <= t_enter) & (merged['停租时间'] >= latest)
            df_confirmed = merged.loc[mask_ok].copy()
            df_confirmed = df_confirmed.drop(columns=['_rid', '航班日期_进入'], errors='ignore')
        else:
            mask = (df_rental['起租时间'] <= earliest) & (df_rental['停租时间'] >= latest)
            df_confirmed = df_rental[mask].copy()

        if df_confirmed.empty:
            if use_flight:
                self.last_diag = (
                    '租车人与航班嫌疑人已关联，但无记录同时满足：'
                    '起租日期不晚于航班「进入」日期，且停租不早于末案日。'
                    '请核对起租/停租与航班抵达、案发时间。'
                )
            else:
                self.last_diag = (
                    '无航班碰撞结果时按案发窗口筛选：起租≤首案日、停租≥末案日。'
                    '当前无满足条件的记录；可先执行「航班分析」生成嫌疑人表再重试租赁。'
                    + (
                        '（已应用租赁公司/品牌筛选）'
                        if (state['rental_company'] or state['car_brand'])
                        else ''
                    )
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