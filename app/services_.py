from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from app.core.state_manager import StateManager
from app.data_paths import DataPaths, persist_upload_bytes
from app.modules.flight_module import FlightAnalysis
from app.modules.lodging_module import CohabitAnalysis, HotelPenetrationAnalysis, LodgingQueryAnalysis
from app.modules.rental_module import RentalAnalysis
from app.modules.trajectory_module import PlateSearchAnalysis, SpatialPenetrationAnalysis
from app.modules.upload_module import FileDataSource
from app.modules.vehicle_module import PlateVerificationAnalysis


class AppServices:
    """前端调用的最小服务层，封装案件、上传、分析三个流程。"""

    def __init__(self, paths: DataPaths):
        self._paths = paths
        self._uploader = FileDataSource()
        self._flight = FlightAnalysis()
        self._plate = PlateSearchAnalysis()
        self._spatial = SpatialPenetrationAnalysis()
        self._rental = RentalAnalysis()
        self._lodging_query = LodgingQueryAnalysis()
        self._cohabit = CohabitAnalysis()
        self._hotel = HotelPenetrationAnalysis()
        self._vehicle = PlateVerificationAnalysis()

    # ── 案件管理 ─────────────────────────────────

    def list_cases(self) -> list[str]:
        return StateManager.list_cases()

    def create_case(self, case_id: str):
        return StateManager.create(case_id.strip())

    def switch_case(self, case_id: str):
        return StateManager.switch(case_id.strip())

    def current_state(self):
        return StateManager.current()

    # ── 案发信息 ─────────────────────────────────

    def add_case_point(self, date_str: str, city: str) -> None:
        state = self.current_state()
        points = list(state["case_points"])
        points.append((date_str, city.strip()))
        state["case_points"] = points

    def remove_case_point(self, index: int) -> None:
        state = self.current_state()
        points = list(state["case_points"])
        if 0 <= index < len(points):
            points.pop(index)
            state["case_points"] = points

    def clear_case_points(self) -> None:
        self.current_state()["case_points"] = []

    def set_profiles(self, gender: str, region: str, rental_company: str, car_brand: str) -> None:
        state = self.current_state()
        state["profile_gender"] = gender.strip()
        state["profile_region"] = region.strip()
        state["rental_company"] = rental_company.strip()
        state["car_brand"] = car_brand.strip()

    # ── 文件上传 ─────────────────────────────────

    def upload_files(self, file_paths: list[str]) -> dict[str, Any]:
        state = self.current_state()
        payload: dict[str, bytes] = {}
        for fp in file_paths:
            p = Path(fp)
            payload[p.name] = p.read_bytes()
            persist_upload_bytes(self._paths, state.case_id, p.name, payload[p.name])
        return self._uploader.process_files(payload, state)

    def upload_files_with_progress(self, file_paths: list[str], on_step) -> dict[str, Any]:
        """带进度回调的上传封装。"""
        state = self.current_state()
        payload: dict[str, bytes] = {}
        total = len(file_paths)
        for idx, fp in enumerate(file_paths, start=1):
            p = Path(fp)
            payload[p.name] = p.read_bytes()
            persist_upload_bytes(self._paths, state.case_id, p.name, payload[p.name])
            on_step(idx, total, p.name)
        return self._uploader.process_files(payload, state)

    # ── Area 1: 链式侦查流程 ─────────────────────

    def run_flight(self) -> pd.DataFrame:
        """航班嫌疑人查询 → 输出三张表 + 时间窗。"""
        return self._flight.run(self.current_state())

    def get_flight_tables(self) -> dict[str, pd.DataFrame]:
        """获取航班三张表。"""
        state = self.current_state()
        return {
            "到达乘客（案发前）": state["flight_enter_candidates"],
            "离开乘客（案发后）": state["flight_leave_candidates"],
            "交叉比对嫌疑人": state["flight_suspect_cross"],
        }

    def get_flight_earliest_latest(self) -> tuple[str, str]:
        """获取航班交叉表时间窗。"""
        state = self.current_state()
        return (
            state.get('flight_earliest_arrival', ''),
            state.get('flight_latest_departure', ''),
        )

    def get_case_point_date_range(self) -> tuple[str, str]:
        """获取案发点的首末日期，用于航班结果描述。"""
        try:
            state = self.current_state()
            points = state['case_points']
            if points:
                dates = sorted(p[0] for p in points)
                return (dates[0], dates[-1])
        except (RuntimeError, KeyError):
            pass
        return ('', '')

    def run_rental(self) -> pd.DataFrame:
        """租车查询：自动使用航班交叉表时间窗（如有），否则回退案发时间。"""
        state = self.current_state()
        earliest = state.get('flight_earliest_arrival', '')
        latest = state.get('flight_latest_departure', '')
        if earliest and latest:
            return self._rental.run(state, time_window_start=earliest, time_window_end=latest)
        return self._rental.run(state)

    def get_rental_driver_suspects(self) -> list:
        """获取租车司机嫌疑人列表 [(姓名, 身份证号), ...] 供下拉框使用。"""
        return self.current_state().get('rental_driver_suspects', [])

    def run_lodging_query(self, id_val: str, name_val: str) -> pd.DataFrame:
        """司机住宿查询（支持姓名/身份证单查或联合查询）。"""
        return self._lodging_query.run(self.current_state(), id_val=id_val, name_val=name_val)

    def get_lodging_dual_results(self) -> dict[str, pd.DataFrame]:
        """获取司机住宿双路查询结果。"""
        state = self.current_state()
        return {
            "按姓名查询": state.get('lodging_driver_result_by_name', pd.DataFrame()),
            "按身份证查询": state.get('lodging_driver_result_by_id', pd.DataFrame()),
        }

    def run_cohabit_from_lodging(self) -> pd.DataFrame:
        """司机关联人员同住查询。"""
        return self._cohabit.run(self.current_state(), use_lodging_base=True)

    def run_cohabit(self) -> pd.DataFrame:
        """原有同住查询（租赁轨迹基准）。"""
        return self._cohabit.run(self.current_state())

    # ── Area 2: 团伙分析 ─────────────────────────

    def run_hotel(self) -> pd.DataFrame:
        """嫌疑团伙住宿渗透查询。"""
        return self._hotel.run(self.current_state())

    # ── Area 3: 车辆与轨迹侦查 ───────────────────

    def run_plate_search(self, pattern: str) -> pd.DataFrame:
        """嫌疑车牌模糊查询。"""
        return self._plate.run(self.current_state(), pattern=pattern)

    def run_spatial(self, start_date: str = '', end_date: str = '') -> pd.DataFrame:
        """案发相邻时间段筛查。"""
        return self._spatial.run(self.current_state(), start_date=start_date, end_date=end_date)

    def run_vehicle(self, plate: str) -> pd.DataFrame:
        """嫌疑车辆真伪查询。"""
        return self._vehicle.run(self.current_state(), plate=plate)

    def get_plate_verification_alert(self) -> bool:
        """获取假牌警告标记。"""
        return self.current_state().get('plate_verification_alert', False)

    # ── 工具 ─────────────────────────────────────

    def current_case_cache_dir(self) -> Path:
        state = self.current_state()
        return self._paths.case_cache_dir(state.case_id)
