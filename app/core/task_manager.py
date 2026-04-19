# app/core/task_manager.py
"""
后台任务管理。
分析任务在子线程中执行，防止阻塞主线程。
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, Future
from threading import Lock
from typing import Any, Callable, Optional

import pandas as pd

from app.utils.logger import get_logger

logger = get_logger(__name__)


class TaskManager:
    """任务管理器，使用线程池执行后台任务。"""

    def __init__(self, max_workers: int = 4):
        """
        初始化任务管理器。

        Args:
            max_workers: 最大线程数
        """
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._tasks: dict[str, Future] = {}
        self._case_group_tasks: dict[tuple[str, str], str] = {}
        self._lock = Lock()

    def submit(
        self,
        task_id: str,
        module: Any,
        state: Any,
        group: str = 'default',
        on_done: Optional[Callable[[pd.DataFrame], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
        **kwargs
    ) -> Future:
        """
        提交分析任务。

        Args:
            task_id: 任务ID
            module: 分析模块实例
            state: 应用状态
            group: 任务分组（同案件同分组串行，避免状态互相覆盖）
            on_done: 完成回调
            on_error: 错误回调
            **kwargs: 传递给 module.run() 的参数

        Returns:
            Future 对象
        """
        case_id = str(getattr(state, 'case_id', 'global'))
        case_group_key = (case_id, group)

        with self._lock:
            running_task_id = self._case_group_tasks.get(case_group_key)
            if running_task_id:
                running_future = self._tasks.get(running_task_id)
                if running_future and not running_future.done():
                    raise RuntimeError(f"案件 {case_id} 的任务组 {group} 正在执行中")
            self._case_group_tasks[case_group_key] = task_id

        def _cleanup() -> None:
            with self._lock:
                self._tasks.pop(task_id, None)
                if self._case_group_tasks.get(case_group_key) == task_id:
                    self._case_group_tasks.pop(case_group_key, None)

        def _run():
            try:
                logger.info("开始执行任务：%s（case=%s group=%s）", task_id, case_id, group)
                result = module.run(state, **kwargs)
                logger.info("任务完成：%s，结果 %d 行", task_id, len(result))
                if on_done:
                    on_done(result)
                return result
            except Exception as e:
                logger.exception("任务异常：%s", e)
                if on_error:
                    on_error(str(e))
                raise
            finally:
                _cleanup()

        future = self._executor.submit(_run)
        with self._lock:
            self._tasks[task_id] = future
        return future

    def cancel(self, task_id: str) -> bool:
        """
        取消任务。

        Args:
            task_id: 任务ID

        Returns:
            是否成功取消
        """
        future = self._tasks.get(task_id)
        if future and not future.done():
            return future.cancel()
        return False

    def is_running(self, task_id: str) -> bool:
        """
        检查任务是否正在运行。

        Args:
            task_id: 任务ID

        Returns:
            是否正在运行
        """
        future = self._tasks.get(task_id)
        return future is not None and not future.done()

    def shutdown(self, wait: bool = True) -> None:
        """
        关闭任务管理器。

        Args:
            wait: 是否等待所有任务完成
        """
        self._executor.shutdown(wait=wait)


# 全局单例
_global_task_manager = TaskManager()


def get_task_manager() -> TaskManager:
    """获取全局任务管理器实例。"""
    return _global_task_manager