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

    def list_cases(self) -> list[str]:
        return StateManager.list_cases()

    def create_case(self, case_id: str):
        return StateManager.create(case_id.strip())

    def switch_case(self, case_id: str):
        return StateManager.switch(case_id.strip())

    def current_state(self):
        return StateManager.current()

    def add_case_point(self, date_str: str, city: str) -> None:
        state = self.current_state()
        points = list(state["case_points"])
        points.append((date_str, city.strip()))
        state["case_points"] = points

    def clear_case_points(self) -> None:
        self.current_state()["case_points"] = []

    def set_profiles(self, gender: str, region: str, rental_company: str, car_brand: str) -> None:
        state = self.current_state()
        state["profile_gender"] = gender.strip()
        state["profile_region"] = region.strip()
        state["rental_company"] = rental_company.strip()
        state["car_brand"] = car_brand.strip()

    def upload_files(self, file_paths: list[str]) -> dict[str, Any]:
        state = self.current_state()
        payload: dict[str, bytes] = {}
        for fp in file_paths:
            p = Path(fp)
            payload[p.name] = p.read_bytes()
            persist_upload_bytes(self._paths, state.case_id, p.name, payload[p.name])
        return self._uploader.process_files(payload, state)

    def run_flight(self) -> pd.DataFrame:
        return self._flight.run(self.current_state())

    def run_plate_search(self, pattern: str) -> pd.DataFrame:
        return self._plate.run(self.current_state(), pattern=pattern)

    def run_spatial(self, buffer_days: int) -> pd.DataFrame:
        return self._spatial.run(self.current_state(), buffer_days=buffer_days)

    def run_rental(self) -> pd.DataFrame:
        return self._rental.run(self.current_state())

    def run_lodging_query(self, id_val: str, name_val: str) -> pd.DataFrame:
        return self._lodging_query.run(self.current_state(), id_val=id_val, name_val=name_val)

    def run_cohabit(self) -> pd.DataFrame:
        return self._cohabit.run(self.current_state())

    def run_hotel(self) -> pd.DataFrame:
        return self._hotel.run(self.current_state())

    def run_vehicle(self, plate: str) -> pd.DataFrame:
        return self._vehicle.run(self.current_state(), plate=plate)
