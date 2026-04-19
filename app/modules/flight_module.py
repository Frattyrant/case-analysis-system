from __future__ import annotations

from typing import Any

import pandas as pd

from app.modules.base import AnalysisModule
from app.utils.geo_utils import GeoUtils
from app.utils.identity_utils import IdentityUtils


class FlightAnalysis(AnalysisModule):
    """航班嫌疑人分析模块：通过案发时间、地点锁定嫌疑人。"""

    def __init__(self):
        self._geo = GeoUtils()

    def run(self, state: Any) -> pd.DataFrame:
        """执行航班分析。

        Args:
            state: 应用状态对象

        Returns:
            嫌疑人名单 DataFrame
        """
        progress = self._progress()
        progress.step(5, '航班分析：读取数据')

        df_raw = next(
            (df.copy() for fn, df in state['uploaded_frames'].items() if '航班' in fn),
            None
        )
        
        if not state['case_points'] or df_raw is None:
            progress.error('航班分析：缺少前置数据')
            return pd.DataFrame()

        progress.step(20, '航班分析：时间窗口')
        sorted_pts = sorted(state['case_points'], key=lambda x: x[0])
        first_date = pd.to_datetime(sorted_pts[0][0])
        last_date = pd.to_datetime(sorted_pts[-1][0])

        progress.step(35, '航班分析：地理匹配')
        crime_cities = [p[1] for p in state['case_points']]
        target_provinces = {
            (self._geo.province_of(c) or '').replace('省', '')
            for c in crime_cities
        }

        progress.step(55, '航班分析：清洗数据')
        df_raw['航班日期'] = pd.to_datetime(df_raw['航班日期'], errors='coerce')
        df_raw = df_raw.dropna(subset=['航班日期', '身份证号'])

        relevant_cities = set()

        def _is_target(code):
            city = self._geo.city_of_airport(code)
            prov = (self._geo.province_of(city) or '').replace('省', '')
            match = prov in target_provinces
            if match:
                relevant_cities.add(city)
            return match

        progress.step(75, '航班分析：筛选和交叉')
        df_area = df_raw[df_raw['到达地'].apply(_is_target)].copy()

        df_t1 = IdentityUtils.apply_filters(
            df_area[df_area['航班日期'] <= first_date].copy(),
            state["profile_gender"], state["profile_region"]
        )

        df_t2 = IdentityUtils.apply_filters(
            df_raw[df_raw['航班日期'] >= last_date].copy(),
            state["profile_gender"], state["profile_region"]
        )

        if not df_t1.empty and not df_t2.empty:
            df_t3 = pd.merge(
                df_t1,
                df_t2[['姓名', '身份证号', '航班号', '航班日期']],
                on=['姓名', '身份证号'], how='inner',
                suffixes=('_进入', '_离开')
            )
        else:
            df_t3 = pd.DataFrame()

        progress.finish('航班分析：完成')
        return df_t3