# app/modules/lodging_module.py
import pandas as pd
from datetime import timedelta
from typing import Any
from app.utils.datetime_utils import DateTimeUtils
from app.utils.identity_utils import IdentityUtils

class LodgingQueryAnalysis:
    """住宿档案查询模块。
    支持按姓名或身份证号单独查询，结果分别存储到不同slot中。
    """
    def __init__(self):
        pass

    def run(self, state: Any, id_val: str = '', name_val: str = '') -> pd.DataFrame:
        df_hotel = next((df for fn, df in state['uploaded_frames'].items() if any(k in fn for k in ['旅店','住宿','旅业'])), pd.DataFrame())

        if df_hotel.empty:
            raise ValueError("未检测到住宿数据库，请先上传包含'旅店/住宿/旅业'关键字的数据。")
        if not id_val and not name_val:
            raise ValueError("请输入身份证号或姓名进行查询。")

        # 按身份证或姓名分别查询
        if id_val and name_val:
            # 两者都提供: 合并查询
            mask = (df_hotel['身份证号'].astype(str) == id_val) | (df_hotel['姓名'] == name_val)
        elif id_val:
            mask = df_hotel['身份证号'].astype(str) == id_val
        else:
            mask = df_hotel['姓名'] == name_val

        res = df_hotel[mask].copy()

        if res.empty:
            state['current_lodging_res'] = pd.DataFrame()
            state['lodging_driver_result_by_name'] = pd.DataFrame()
            state['lodging_driver_result_by_id'] = pd.DataFrame()
            return pd.DataFrame()

        for col in['入住时间','退房时间','真入住时间','真退房时间']:
            if col in res.columns:
                res[col] = DateTimeUtils.clean_time_format(res[col])

        state['current_lodging_res'] = res

        # 分别存储按姓名和按身份证的查询结果
        if name_val and not id_val:
            state['lodging_driver_result_by_name'] = res.copy()
        elif id_val and not name_val:
            state['lodging_driver_result_by_id'] = res.copy()
        else:
            # 两者都有: 分别存储
            name_res = df_hotel[df_hotel['姓名'] == name_val].copy()
            id_res = df_hotel[df_hotel['身份证号'].astype(str) == id_val].copy()
            for col in['入住时间','退房时间','真入住时间','真退房时间']:
                if col in name_res.columns:
                    name_res[col] = DateTimeUtils.clean_time_format(name_res[col])
                if col in id_res.columns:
                    id_res[col] = DateTimeUtils.clean_time_format(id_res[col])
            state['lodging_driver_result_by_name'] = name_res if not name_res.empty else pd.DataFrame()
            state['lodging_driver_result_by_id'] = id_res if not id_res.empty else pd.DataFrame()

        return res


class CohabitAnalysis:
    """同住关联分析模块。
    支持两种基准数据来源:
      1. 租赁轨迹嫌疑人 (默认) → use_lodging_base=False
      2. 住宿查询结果 (链式) → use_lodging_base=True → 同住分析
    """
    def __init__(self):
        pass

    def _get_hotel_df(self, state: Any) -> pd.DataFrame:
        for fname, df in state['uploaded_frames'].items():
            if any(k in fname for k in ['旅店', '住宿', '旅业']):
                return df.copy()
        return pd.DataFrame()

    def run(self, state: Any, use_lodging_base: bool = False) -> pd.DataFrame:
        df_hotel = self._get_hotel_df(state)

        if df_hotel.empty:
            raise ValueError("未检测到住宿数据库，请先上传数据。")

        if use_lodging_base:
            # 基于住宿查询结果做同住分析
            base_df = state.get('current_lodging_res', pd.DataFrame())
            if base_df.empty:
                raise ValueError("请先执行司机住宿查询，再进行司机关联人员同住查询！")
            suspect_names = list(base_df['姓名'].dropna().unique())
            if not suspect_names:
                raise ValueError("司机住宿查询结果中未找到有效姓名。")
        else:
            # 原有的租赁轨迹嫌疑人逻辑
            try:
                real_car = state['df_real_car']
            except KeyError:
                real_car = pd.DataFrame()

            if real_car.empty:
                raise ValueError("未检测到已锁定的租赁嫌疑人，请先执行「嫌疑人租赁车辆分析」。")

            suspect_names = state.get('rental_trajectory_suspects', [])
            if not suspect_names:
                raise ValueError("未在租赁期内查到关联轨迹的嫌疑人！无法进行同住关联分析。")

        def _to_dt(series: pd.Series) -> pd.Series:
            s = series.astype(str).str.strip().str.replace(r'\.0$', '', regex=True)
            return pd.to_datetime(s, errors='coerce', format='%Y%m%d%H%M')

        all_results = []
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

            df_final = pd.concat(hits).drop_duplicates(subset=['姓名', '身份证号', '入住时间', '旅馆名称'])
            df_final['入住时间_标准'] = df_final['dt'].dt.strftime('%Y-%m-%d %H:%M')
            cols = ['姓名', '身份证号', '同住关系', '入住时间_标准', '旅馆名称', '房号', '旅馆地址']
            all_results.append(df_final[cols])

        result = pd.concat(all_results, ignore_index=True) if all_results else pd.DataFrame()
        return result


class HotelPreprocessor:
    def preprocess(self, df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
        df = df.copy()
        ci_col = DateTimeUtils.resolve_best_col(df, '真入住时间', '入住时间')
        df['_checkin_dt']  = DateTimeUtils.robust_to_datetime(df[ci_col]) if ci_col else pd.NaT
        co_col = DateTimeUtils.resolve_best_col(df, '真退房时间', '退房时间')
        df['_checkout_dt'] = DateTimeUtils.robust_to_datetime(df[co_col]) if co_col else pd.NaT
        df['入住日期'] = DateTimeUtils.fmt_date(df['_checkin_dt'])
        df['退房日期'] = DateTimeUtils.fmt_date(df['_checkout_dt'])
        return df, []


class HotelPenetrationAnalysis:
    """住宿渗透（案发点交集）分析模块。"""
    def __init__(self):
        self._preprocessor = HotelPreprocessor()

    def run(self, state: Any) -> pd.DataFrame:
        df_raw = self._get_hotel_df(state)
        if not state['case_points'] or df_raw.empty:
            raise ValueError("缺少案发信息或住宿数据，请先补全！")

        df_hotel, _ = self._preprocessor.preprocess(df_raw)
        df_valid = df_hotel[df_hotel['_checkin_dt'].notna()].copy()

        # 应用身份画像过滤
        if state['profile_gender'] or state['profile_region']:
            df_valid = IdentityUtils.apply_filters(df_valid, state['profile_gender'], state['profile_region'])

        point_results = []
        for case_date_str, loc_keyword in state['case_points']:
            target_dt = pd.to_datetime(case_date_str)
            window_start = target_dt - timedelta(days=1)
            loc_mask = (df_valid['旅馆地址'].astype(str).str.contains(loc_keyword, na=False) |
                        df_valid['旅馆名称'].astype(str).str.contains(loc_keyword, na=False))
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
            return pd.DataFrame()

        df_all_hits = pd.concat(point_results, ignore_index=True)
        return df_all_hits[df_all_hits['身份证号'].isin(intersection_ids)].copy()

    def _get_hotel_df(self, state: Any) -> pd.DataFrame:
        for fname, df in state['uploaded_frames'].items():
            if any(k in fname for k in ['旅店', '住宿', '旅业']):
                return df.copy()
        return pd.DataFrame()
