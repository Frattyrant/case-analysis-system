from __future__ import annotations

import unittest

import pandas as pd

from app.core.state_manager import AppState, SlotSpec, StateManager


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


class TestStateManager(unittest.TestCase):
    def setUp(self) -> None:
        _reset_state_manager()
        _register_test_slots()

    def tearDown(self) -> None:
        _reset_state_manager()

    def test_case_isolation_and_switch(self) -> None:
        case_a = StateManager.create('case_A')
        case_b = StateManager.create('case_B')

        case_a['matched_plates'] = ['辽A12345']
        case_b['matched_plates'] = ['京B67890']

        self.assertEqual(StateManager.get('case_A')['matched_plates'], ['辽A12345'])
        self.assertEqual(StateManager.get('case_B')['matched_plates'], ['京B67890'])

        StateManager.switch('case_A')
        self.assertEqual(StateManager.current().case_id, 'case_A')

    def test_destroy_current_case(self) -> None:
        StateManager.create('case_A')
        StateManager.destroy('case_A')
        self.assertIsNone(StateManager.current_case_id())


if __name__ == '__main__':
    unittest.main()
