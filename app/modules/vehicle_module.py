from __future__ import annotations

from typing import Any

import pandas as pd

from app.modules.base import AnalysisModule


class PlateVerificationAnalysis(AnalysisModule):
    """车辆真伪核查模块。"""

    def run(self, state: Any, plate: str = '') -> pd.DataFrame:
        """执行车辆真伪核查。

        Args:
            state: 应用状态对象
            plate: 车牌号

        Returns:
            核查结果 DataFrame
        """
        progress = self._progress()
        progress.step(15, '车辆核查：读取库数据')

        df_vehicle = next(
            (df for fn, df in state['uploaded_frames'].items() if '机动车' in fn),
            pd.DataFrame()
        )
        df_rental = next(
            (df for fn, df in state['uploaded_frames'].items() if '租赁' in fn),
            pd.DataFrame()
        )

        if not plate:
            progress.error('车辆核查：车牌不能为空')
            return pd.DataFrame()

        progress.step(60, '车辆核查：比对备案记录')
        plate_upper = plate.upper()
        parts = []

        if not df_vehicle.empty:
            res_v = df_vehicle[df_vehicle['号牌号码'] == plate_upper].copy()
            if not res_v.empty:
                res_v['备案来源'] = '机动车登记库'
                res_v['身份结论'] = '真牌 (个人/单位)'
                parts.append(res_v)

        if not df_rental.empty:
            res_r = df_rental[df_rental['号牌号码'] == plate_upper].copy()
            if not res_r.empty:
                res_r['备案来源'] = '汽车租赁库'
                res_r['身份结论'] = '真牌 (租赁车辆)'
                res_r = res_r.rename(columns={'租车人姓名': '所有人'})
                parts.append(res_r)

        combined = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
        state['current_lodging_res'] = combined

        progress.finish('车辆核查：完成')
        return combined