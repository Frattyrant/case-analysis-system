# app/modules/rental_module.py
import pandas as pd
from typing import Any

class RentalAnalysis:
    """租赁全库分析模块。
    支持两种时间窗来源：
      1. 来自航班交叉表 (time_window_start / time_window_end)
      2. 来自案发时间 case_points (回退方案)
    结果存储司机嫌疑人列表供住宿查询下拉框使用。
    """
    def __init__(self):
        pass

    def run(self, state: Any, time_window_start: str | None = None,
            time_window_end: str | None = None) -> pd.DataFrame:
        df_rental = next((df for fn, df in state['uploaded_frames'].items() if '租赁' in fn), pd.DataFrame())
        df_track = next((df for fn, df in state['uploaded_frames'].items() if '轨迹' in fn), pd.DataFrame())

        if df_rental.empty:
            raise ValueError("未发现租赁数据库，请先导入文件。")

        # 时间窗来源: 优先使用传入参数 → 航班交叉表时间 → 案发时间回退
        if time_window_start and time_window_end:
            earliest = pd.to_datetime(time_window_start)
            latest = pd.to_datetime(time_window_end)
        elif state.get('flight_earliest_arrival') and state.get('flight_latest_departure'):
            earliest = pd.to_datetime(state['flight_earliest_arrival'])
            latest = pd.to_datetime(state['flight_latest_departure'])
        elif state['case_points']:
            case_dates = sorted(pd.to_datetime(p[0]) for p in state['case_points'])
            earliest, latest = case_dates[0], case_dates[-1]
        else:
            raise ValueError("未检测到案发时间或航班时间窗，请先录入案发信息或执行航班查询。")

        df_rental = df_rental.copy()
        df_rental['起租时间'] = pd.to_datetime(df_rental['起租时间'], errors='coerce')
        df_rental['停租时间'] = pd.to_datetime(df_rental['停租时间'], errors='coerce')

        mask = (df_rental['起租时间'] <= earliest) & (df_rental['停租时间'] >= latest)
        if state['rental_company']:
            mask &= df_rental['租赁公司名称'].str.contains(state['rental_company'], na=False)
        if state['car_brand']:
            mask &= df_rental['车辆品牌'].astype(str) == state['car_brand']

        df_confirmed = df_rental[mask].copy()

        # 存储司机嫌疑人列表 [(姓名, 身份证号), ...] 供住宿查询下拉框使用
        if not df_confirmed.empty and '租车人姓名' in df_confirmed.columns and '租车人身份证号码' in df_confirmed.columns:
            state['rental_driver_suspects'] = list(
                zip(df_confirmed['租车人姓名'].astype(str), df_confirmed['租车人身份证号码'].astype(str))
            )
        else:
            state['rental_driver_suspects'] = []

        if df_confirmed.empty:
            return pd.DataFrame()

        state['df_real_car'] = df_confirmed

        # 交叉轨迹数据，找出租赁期内有轨迹的嫌疑人
        if not df_track.empty:
            df_track = df_track.copy()
            df_track['通过时间'] = pd.to_datetime(df_track['通过时间'], errors='coerce')
            merged = pd.merge(
                df_confirmed[['号牌号码','租车人姓名','租车人身份证号码','起租时间','停租时间']],
                df_track[['号牌号码','通过时间','卡口名称','行政区域']],
                on='号牌号码', how='inner'
            )
            merged = merged[
                (merged['通过时间'] >= merged['起租时间']) &
                (merged['通过时间'] <= merged['停租时间'])
            ]
            if not merged.empty:
                state['rental_trajectory_suspects'] = list(merged['租车人姓名'].unique())

        return df_confirmed
