from __future__ import annotations

import unittest

import pandas as pd

from app.core.state_manager import AppState, SlotSpec, StateManager
from app.modules.flight_module import FlightAnalysis
from app.modules.lodging_module import CohabitAnalysis, HotelPenetrationAnalysis, LodgingQueryAnalysis
from app.modules.rental_module import RentalAnalysis
from app.modules.trajectory_module import PlateSearchAnalysis, SpatialPenetrationAnalysis
from app.modules.vehicle_module import PlateVerificationAnalysis


def _reset_state_manager() -> None:
    AppState._registry.clear()
    StateManager._cases.clear()
    StateManager._current_case_id = None


def _register_test_slots() -> None:
    StateManager.register([
        # --- 原有 ---
        SlotSpec('uploaded_frames', dict),
        SlotSpec('case_points', list),
        SlotSpec('profile_gender', str),
        SlotSpec('profile_region', str),
        SlotSpec('rental_company', str),
        SlotSpec('car_brand', str),
        SlotSpec('matched_plates', list),
        SlotSpec('matched_trajectories', pd.DataFrame),
        SlotSpec('flight_enter_candidates', pd.DataFrame),
        SlotSpec('flight_leave_candidates', pd.DataFrame),
        SlotSpec('flight_suspect_cross', pd.DataFrame),
        SlotSpec('df_real_car', pd.DataFrame),
        SlotSpec('rental_trajectory_suspects', list),
        SlotSpec('current_lodging_res', pd.DataFrame),
        # --- 链式侦查+车辆轨迹 ---
        SlotSpec('flight_earliest_arrival', str),
        SlotSpec('flight_latest_departure', str),
        SlotSpec('rental_driver_suspects', list),
        SlotSpec('lodging_driver_result_by_name', pd.DataFrame),
        SlotSpec('lodging_driver_result_by_id', pd.DataFrame),
        SlotSpec('spatial_expanded_result', pd.DataFrame),
        SlotSpec('plate_verification_alert', bool),
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

    def build_airport_province_map(self, airport_codes, target_provinces):
        """测试用：将SHE→辽宁→匹配目标省份"""
        result = {}
        mapping = {'SHE': '沈阳', 'PEK': '北京'}
        city_to_prov = {'沈阳': '辽宁省', '北京': '北京市'}
        for code in airport_codes:
            city = mapping.get(code, code)
            prov = city_to_prov.get(city, '辽宁省').replace('省', '')
            result[code] = prov in target_provinces
        return result


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
            },
            {
                '姓名': '李四',
                '身份证号': '110101199001010022',
                '入住时间': '201311180900',
                '退房时间': '201311191100',
                '旅馆名称': '沈阳宾馆',
                '房号': '102',
                '旅馆地址': '沈阳市和平区',
            },
        ])
        self.state['uploaded_frames']['航班_test.csv'] = pd.DataFrame([
            {'航班日期': '2013-11-17', '航班号': 'CZ1234', '姓名': '李四', '身份证号': '110101199001010022', '到达地': 'SHE'},
            {'航班日期': '2013-11-19', '航班号': 'CZ5678', '姓名': '李四', '身份证号': '110101199001010022', '到达地': 'SHE'},
        ])

    # ── 原有测试（保持兼容）──────────────────────

    def test_trajectory_rental_lodging_vehicle_flow(self) -> None:
        """原有端到端流程测试"""
        plate_result = PlateSearchAnalysis().run(self.state, pattern='A123')
        self.assertEqual(len(plate_result), 2)
        self.assertIn('辽A12345', self.state['matched_plates'])

        spatial_result = SpatialPenetrationAnalysis().run(self.state, start_date='2013-11-17', end_date='2013-11-20')
        self.assertGreaterEqual(len(spatial_result), 1)

        rental_result = RentalAnalysis().run(self.state)
        self.assertEqual(len(rental_result), 1)
        self.assertIn('张三', self.state['rental_trajectory_suspects'])

        lodging_result = LodgingQueryAnalysis().run(self.state, id_val='110101199001010011')
        self.assertEqual(len(lodging_result), 1)

        vehicle_result = PlateVerificationAnalysis().run(self.state, plate='辽A12345')
        self.assertEqual(len(vehicle_result), 2)

    def test_flight_module_with_fake_geo(self) -> None:
        """航班模块基本功能测试"""
        module = FlightAnalysis()
        module._geo = _FakeGeo()
        result = module.run(self.state)
        self.assertEqual(len(result), 1)
        self.assertIn('姓名', result.columns)

    def test_rental_ignores_flight_cross_and_uses_case_window(self) -> None:
        """向后兼容: 无航班时间窗时回退到案发时间"""
        self.state['flight_suspect_cross'] = pd.DataFrame([
            {
                '姓名': '张三',
                '身份证号': '110101199001010011',
                '航班日期_进入': pd.Timestamp('2013-11-17'),
                '航班日期_离开': pd.Timestamp('2013-11-19'),
            }
        ])
        rental_result = RentalAnalysis().run(self.state)
        self.assertEqual(len(rental_result), 1)
        self.assertIn('张三', rental_result['租车人姓名'].values)

    def test_rental_still_matches_when_flight_cross_stricter(self) -> None:
        """向后兼容: flight_suspect_cross不影响默认行为"""
        self.state['flight_suspect_cross'] = pd.DataFrame([
            {
                '姓名': '张三',
                '身份证号': '110101199001010011',
                '航班日期_进入': pd.Timestamp('2013-11-14'),
                '航班日期_离开': pd.Timestamp('2013-11-19'),
            }
        ])
        rental_result = RentalAnalysis().run(self.state)
        self.assertEqual(len(rental_result), 1)

    # ── 新增测试 ─────────────────────────────────

    def test_flight_stores_time_window(self) -> None:
        """航班模块存储时间窗"""
        module = FlightAnalysis()
        module._geo = _FakeGeo()
        module.run(self.state)
        earliest = self.state.get('flight_earliest_arrival', '')
        latest = self.state.get('flight_latest_departure', '')
        self.assertTrue(bool(earliest), "应存储最早到达时间")
        self.assertTrue(bool(latest), "应存储最晚离开时间")

    def test_rental_uses_flight_time_window(self) -> None:
        """租车使用航班时间窗"""
        self.state['flight_earliest_arrival'] = '2013-11-17 00:00:00'
        self.state['flight_latest_departure'] = '2013-11-19 00:00:00'
        result = RentalAnalysis().run(self.state)
        self.assertEqual(len(result), 1)

    def test_rental_stores_driver_suspects(self) -> None:
        """租车存储司机嫌疑人列表供下拉框使用"""
        RentalAnalysis().run(self.state)
        suspects = self.state.get('rental_driver_suspects', [])
        self.assertGreater(len(suspects), 0, "应有司机嫌疑人")
        name, id_ = suspects[0]
        self.assertIsInstance(name, str)
        self.assertIsInstance(id_, str)
        self.assertIn('张三', name)

    def test_lodging_dual_result_storage(self) -> None:
        """住宿查询分别存储姓名和身份证结果"""
        # 先按姓名查
        LodgingQueryAnalysis().run(self.state, name_val='张三')
        by_name = self.state.get('lodging_driver_result_by_name', pd.DataFrame())
        self.assertFalse(by_name.empty, "应存储姓名查询结果")

        # 再按身份证查
        LodgingQueryAnalysis().run(self.state, id_val='110101199001010011')
        by_id = self.state.get('lodging_driver_result_by_id', pd.DataFrame())
        self.assertFalse(by_id.empty, "应存储身份证查询结果")

    def test_vehicle_alert_flag(self) -> None:
        """车辆真伪查询设置假牌警告标记"""
        # 真牌
        PlateVerificationAnalysis().run(self.state, plate='辽A12345')
        self.assertFalse(self.state.get('plate_verification_alert', True),
                         "辽A12345在机动车库中，不应标记为假牌")

        # 假牌
        PlateVerificationAnalysis().run(self.state, plate='粤Z99999')
        self.assertTrue(self.state.get('plate_verification_alert', False),
                        "粤Z99999不在任何库中，应标记为假牌")

    def test_spatial_stores_expanded_result(self) -> None:
        """扩展时段轨迹筛查存储结果（使用起止日期）"""
        self.state['matched_plates'] = ['辽A12345']
        result = SpatialPenetrationAnalysis().run(self.state, start_date='2013-11-17', end_date='2013-11-20')
        self.assertGreaterEqual(len(result), 1)
        stored = self.state.get('spatial_expanded_result', pd.DataFrame())
        self.assertFalse(stored.empty, "应存储扩展时段结果")

    def test_spatial_defaults_to_case_points(self) -> None:
        """扩展时段轨迹筛查：未指定日期时回退到案发点首末时间"""
        self.state['matched_plates'] = ['辽A12345']
        result = SpatialPenetrationAnalysis().run(self.state)
        self.assertGreaterEqual(len(result), 1)

    def test_cohabit_with_lodging_base(self) -> None:
        """基于住宿查询结果做同住分析"""
        LodgingQueryAnalysis().run(self.state, name_val='张三')
        result = CohabitAnalysis().run(self.state, use_lodging_base=True)
        # 验证有结果返回即可（同住关联成功）
        self.assertIsNotNone(result)

    def test_hotel_penetration_returns_result(self) -> None:
        """住宿渗透返回结果"""
        result = HotelPenetrationAnalysis().run(self.state)
        self.assertIsInstance(result, pd.DataFrame)


if __name__ == '__main__':
    unittest.main()
