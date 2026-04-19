from __future__ import annotations

import time
import unittest

import pandas as pd

from app.core.task_manager import TaskManager


class _DummyState:
    def __init__(self, case_id: str):
        self.case_id = case_id


class _SleepModule:
    def __init__(self, delay: float, rows: int = 1):
        self._delay = delay
        self._rows = rows

    def run(self, state, **kwargs):
        time.sleep(self._delay)
        return pd.DataFrame({'x': list(range(self._rows))})


class TestTaskManager(unittest.TestCase):
    def test_submit_is_async(self) -> None:
        manager = TaskManager(max_workers=2)
        start = time.time()
        future = manager.submit(
            task_id='t_async',
            module=_SleepModule(delay=0.3, rows=2),
            state=_DummyState('A'),
            group='g1',
        )
        submit_cost = time.time() - start
        self.assertLess(submit_cost, 0.15)
        self.assertFalse(future.done())
        result = future.result(timeout=2)
        self.assertEqual(len(result), 2)
        manager.shutdown(wait=True)

    def test_same_case_same_group_isolated(self) -> None:
        manager = TaskManager(max_workers=2)
        state = _DummyState('case_same')
        _ = manager.submit(
            task_id='t1',
            module=_SleepModule(delay=0.4),
            state=state,
            group='trajectory',
        )
        with self.assertRaises(RuntimeError):
            manager.submit(
                task_id='t2',
                module=_SleepModule(delay=0.1),
                state=state,
                group='trajectory',
            )
        manager.shutdown(wait=True)

    def test_different_case_can_run_parallel(self) -> None:
        manager = TaskManager(max_workers=2)
        f1 = manager.submit(
            task_id='t_case_a',
            module=_SleepModule(delay=0.3),
            state=_DummyState('A'),
            group='flight',
        )
        f2 = manager.submit(
            task_id='t_case_b',
            module=_SleepModule(delay=0.3),
            state=_DummyState('B'),
            group='flight',
        )
        self.assertEqual(len(f1.result(timeout=2)), 1)
        self.assertEqual(len(f2.result(timeout=2)), 1)
        manager.shutdown(wait=True)


if __name__ == '__main__':
    unittest.main()
