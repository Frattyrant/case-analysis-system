# app/modules/vehicle_module.py
import pandas as pd
from typing import Any

class PlateVerificationAnalysis:
    """车辆真伪核查模块。
    对比机动车登记库和租赁库判定车牌真伪，并设置假牌警告标记。
    """
    def __init__(self):
        pass

    def run(self, state: Any, plate: str = '') -> pd.DataFrame:
        df_vehicle = next((df for fn, df in state['uploaded_frames'].items() if '机动车' in fn), pd.DataFrame())
        df_rental = next((df for fn, df in state['uploaded_frames'].items() if '租赁' in fn), pd.DataFrame())

        if not plate:
            raise ValueError("请输入需要核查的完整车牌号！")

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

        # 设置假牌警告标记: 两个库都查不到 → 疑似假牌
        state['plate_verification_alert'] = combined.empty

        return combined
