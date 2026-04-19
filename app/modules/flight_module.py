from __future__ import annotations

from typing import Any

import pandas as pd

from app.modules.base import AnalysisModule
from app.utils.geo_utils import GeoUtils
from app.utils.identity_utils import IdentityUtils


def _normalize_id_series(s: pd.Series) -> pd.Series:
    """缓解 Excel 将身份证号读成 float 的问题（过长时仍可能精度丢失，以原始导出为字符串为佳）。"""
    out: list[str] = []
    for v in s:
        if pd.isna(v):
            out.append("")
            continue
        if isinstance(v, float):
            if abs(v) >= 1e15:
                out.append(f"{v:.0f}")
            else:
                t = str(int(v)) if v == int(v) else str(v)
                out.append(t)
            continue
        t = str(v).strip()
        if t.endswith(".0") and t[:-2].isdigit() and len(t) >= 16:
            t = t[:-2]
        out.append(t)
    return pd.Series(out, index=s.index)


class FlightAnalysis(AnalysisModule):
    """航班嫌疑人分析模块：通过案发时间、地点锁定嫌疑人。"""

    def __init__(self) -> None:
        self._geo = GeoUtils()
        self.last_diag = ""

    def _province_from_arrival(self, cell: object) -> str:
        """到达地可能是 IATA 三字码，也可能是中文城市/机场描述。"""
        s = str(cell).strip() if cell is not None and not (isinstance(cell, float) and pd.isna(cell)) else ""
        if not s:
            return ""
        city = self._geo.city_of_airport(s)
        p = self._geo.province_of(city)
        if p:
            return str(p).replace("省", "")
        p2 = self._geo.province_of(s)
        return (str(p2) if p2 else "").replace("省", "")

    def run(self, state: Any) -> pd.DataFrame:
        """执行航班分析。

        Args:
            state: 应用状态对象

        Returns:
            嫌疑人名单 DataFrame
        """
        self.last_diag = ""
        progress = self._progress()
        progress.step(5, "航班分析：读取数据")

        df_raw = next(
            (df.copy() for fn, df in state["uploaded_frames"].items() if "航班" in fn),
            None,
        )

        if not state["case_points"] or df_raw is None:
            state["flight_suspect_cross"] = pd.DataFrame()
            if not state["case_points"]:
                self.last_diag = (
                    "请先在「案件信息」中填写案发地点与日期，并点击「确认添加」保存至少一条记录。"
                )
            else:
                self.last_diag = (
                    "未载入文件名包含「航班」的表。请确认已导入且文件名含「航班」关键字。"
                )
            progress.error("航班分析：缺少前置数据")
            return pd.DataFrame()

        progress.step(20, "航班分析：时间窗口")
        sorted_pts = sorted(state["case_points"], key=lambda x: x[0])
        first_date = pd.to_datetime(sorted_pts[0][0])
        last_date = pd.to_datetime(sorted_pts[-1][0])

        progress.step(35, "航班分析：地理匹配")
        crime_cities = [p[1] for p in state["case_points"]]
        target_provinces: set[str] = set()
        for c in crime_cities:
            pv = self._geo.province_of(c)
            if pv:
                target_provinces.add(str(pv).replace("省", ""))
        if not target_provinces:
            self.last_diag = (
                "无法从案发城市解析出省份（请安装 cpca，并填写可识别的国内地名）。"
                "将暂时不按省份筛选「到达地」，仅按时间与画像条件分析。"
            )

        progress.step(55, "航班分析：清洗数据")
        need_cols = {"航班日期", "身份证号", "到达地", "姓名", "航班号"}
        missing = need_cols - set(df_raw.columns)
        if missing:
            state["flight_suspect_cross"] = pd.DataFrame()
            self.last_diag = f"航班表缺少列：{', '.join(sorted(missing))}（当前列：{list(df_raw.columns)}）"
            progress.finish("航班分析：列不齐")
            return pd.DataFrame()

        df_raw = df_raw.copy()
        df_raw["身份证号"] = _normalize_id_series(df_raw["身份证号"])
        df_raw["航班日期"] = pd.to_datetime(df_raw["航班日期"], errors="coerce")
        n_before = len(df_raw)
        df_raw = df_raw.dropna(subset=["航班日期", "身份证号"])
        df_raw = df_raw[df_raw["身份证号"].astype(str).str.len() >= 15]
        if df_raw.empty:
            state["flight_suspect_cross"] = pd.DataFrame()
            self.last_diag = (
                f"有效航班记录为 0 行（解析前约 {n_before} 行）。"
                "请检查「航班日期」是否为可识别日期，以及「身份证号」是否完整。"
            )
            progress.finish("航班分析：无有效行")
            return pd.DataFrame()

        progress.step(75, "航班分析：筛选和交叉")
        if not target_provinces:
            df_area = df_raw.copy()
        else:

            def _is_target(code: object) -> bool:
                prov = self._province_from_arrival(code)
                return prov in target_provinces

            df_area = df_raw[df_raw["到达地"].apply(_is_target)].copy()
            if df_area.empty:
                self.last_diag = (
                    "没有任何一条航班的「到达地」能匹配到案发省份。"
                    "请确认「到达地」列为机场三字码或国内城市/机场名称，且与案发地同属一省。"
                )

        df_t1 = IdentityUtils.apply_filters(
            df_area[df_area["航班日期"] <= first_date].copy(),
            state["profile_gender"] or None,
            state["profile_region"] or None,
        )

        df_t2 = IdentityUtils.apply_filters(
            df_raw[df_raw["航班日期"] >= last_date].copy(),
            state["profile_gender"] or None,
            state["profile_region"] or None,
        )

        if df_t1.empty:
            self.last_diag = (
                (self.last_diag + "\n" if self.last_diag else "")
                + f"「进入」侧无记录：案发首日前抵达目标省份的航班经画像筛选后为 0（首案日 {first_date.date()}）。"
            )
        if df_t2.empty:
            self.last_diag = (
                (self.last_diag + "\n" if self.last_diag else "")
                + f"「离开」侧无记录：案发末日及之后起飞的航班经筛选后为 0（末案日 {last_date.date()}）。"
            )

        if not df_t1.empty and not df_t2.empty:
            df_t3 = pd.merge(
                df_t1,
                df_t2[["姓名", "身份证号", "航班号", "航班日期"]],
                on=["姓名", "身份证号"],
                how="inner",
                suffixes=("_进入", "_离开"),
            )
        else:
            df_t3 = pd.DataFrame()

        if df_t3.empty and (not df_t1.empty) and (not df_t2.empty):
            self.last_diag = (
                (self.last_diag + "\n" if self.last_diag else "")
                + "进入侧与离开侧均有记录，但「姓名+身份证号」无交集，请核对数据是否为同人。"
            )

        # 供租赁模块：按嫌疑人「进入」案发区域航班的日期约束起租时间
        state["flight_suspect_cross"] = df_t3.copy()

        progress.finish("航班分析：完成")
        return df_t3
