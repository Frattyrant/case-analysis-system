from __future__ import annotations

import unittest

import pandas as pd

from app.core.state_manager import AppState, SlotSpec, StateManager
from app.modules.flight_module import FlightAnalysis
from app.modules.lodging_module import LodgingQueryAnalysis
from app.modules.rental_module import RentalAnalysis
from app.modules.trajectory_module import PlateSearchAnalysis, SpatialPenetrationAnalysis
from app.modules.vehicle_module import PlateVerificationAnalysis


def _reset_state_manager() -> None:
    AppState._registry.clear()
    StateManager._cases.clear()
    StateManager._current_case_id = None


def _register_test_slots() -> None:
    StateManager.register([
        SlotSpec('uploaded_frames', dict),
        SlotSpec('case_points', list),
        SlotSpec('profile_gender', str),
        SlotSpec('profile_region', str),
        SlotSpec('rental_company', str),
        SlotSpec('car_brand', str),
        SlotSpec('matched_plates', list),
        SlotSpec('matched_trajectories', pd.DataFrame),
        SlotSpec('df_real_car', pd.DataFrame),
        SlotSpec('rental_trajectory_suspects', list),
        SlotSpec('current_lodging_res', pd.DataFrame),
    ])


class _FakeGeo:
    def province_of(self, location: str):
        if not location:
            return None
        mapping = {'沈阳': '辽宁省', '北京': '北京市'}
        return mapping.get(location, '辽宁省')

    def city_of_airport(self, iata_code: str) -> str:
        mapping = {'SHE': '沈阳', 'PEK': '北京'}
        return mapping.get(iata_code, iata_code)


class TestModulesPipeline(unittest.TestCase):
    def setUp(self) -> None:
        _reset_state_manager()
        _register_test_slots()
        self.state = StateManager.create('case_pipeline')
        self.state['case_points'] = [('2013-11-18', '沈阳')]
        self.state['profile_gender'] = ''
        self.state['profile_region'] = ''
        self.state['rental_company'] = ''
        self.state['car_brand'] = ''
        self._load_test_frames()

    def tearDown(self) -> None:
        _reset_state_manager()

    def _load_test_frames(self) -> None:
        self.state['uploaded_frames']['轨迹_test.csv'] = pd.DataFrame([
            {'号牌号码': '辽A12345', '通过时间': '2013-11-18 08:00:00', '卡口名称': '沈阳北', '行政区域': '沈阳'},
            {'号牌号码': '辽A12345', '通过时间': '2013-11-19 10:00:00', '卡口名称': '沈阳南', '行政区域': '沈阳'},
            {'号牌号码': '京B99999', '通过时间': '2013-11-19 10:00:00', '卡口名称': '北京东', '行政区域': '北京'},
        ])
        self.state['uploaded_frames']['租赁_test.csv'] = pd.DataFrame([
            {
                '号牌号码': '辽A12345',
                '租车人姓名': '张三',
                '租车人身份证号码': '110101199001010011',
                '起租时间': '2013-11-15 00:00:00',
                '停租时间': '2013-11-20 00:00:00',
                '租赁公司名称': '神州',
                '车辆品牌': '捷达',
            }
        ])
        self.state['uploaded_frames']['机动车_test.csv'] = pd.DataFrame([
            {'号牌号码': '辽A12345', '所有人': '张三', '身份证号': '110101199001010011', '车辆品牌': '捷达'}
        ])
        self.state['uploaded_frames']['住宿_test.csv'] = pd.DataFrame([
            {
                '姓名': '张三',
                '身份证号': '110101199001010011',
                '入住时间': '201311180800',
                '退房时间': '201311191000',
                '旅馆名称': '沈阳宾馆',
                '房号': '101',
                '旅馆地址': '沈阳市和平区',
            }
        ])
        self.state['uploaded_frames']['航班_test.csv'] = pd.DataFrame([
            {'航班日期': '2013-11-17', '航班号': 'CZ1234', '姓名': '李四', '身份证号': '110101199001010022', '到达地': 'SHE'},
            {'航班日期': '2013-11-19', '航班号': 'CZ5678', '姓名': '李四', '身份证号': '110101199001010022', '到达地': 'PEK'},
        ])

    def test_trajectory_rental_lodging_vehicle_flow(self) -> None:
        plate_result = PlateSearchAnalysis().run(self.state, pattern='A123')
        self.assertEqual(len(plate_result), 2)
        self.assertIn('辽A12345', self.state['matched_plates'])

        spatial_result = SpatialPenetrationAnalysis().run(self.state, buffer_days=1)
        self.assertGreaterEqual(len(spatial_result), 1)

        rental_result = RentalAnalysis().run(self.state)
        self.assertEqual(len(rental_result), 1)
        self.assertIn('张三', self.state['rental_trajectory_suspects'])

        lodging_result = LodgingQueryAnalysis().run(self.state, id_val='110101199001010011')
        self.assertEqual(len(lodging_result), 1)

        vehicle_result = PlateVerificationAnalysis().run(self.state, plate='辽A12345')
        self.assertEqual(len(vehicle_result), 2)

    def test_flight_module_with_fake_geo(self) -> None:
        module = FlightAnalysis()
        module._geo = _FakeGeo()
        result = module.run(self.state)
        self.assertEqual(len(result), 1)
        self.assertIn('姓名', result.columns)


if __name__ == '__main__':
    unittest.main()
