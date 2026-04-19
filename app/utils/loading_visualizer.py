from __future__ import annotations

import tkinter as tk
import threading
from tkinter import ttk
from typing import Optional


class _NoopLoadingDriver:
    """空实现：模块未挂载进度可视化时避免报错。"""

    def step(self, value: int, desc: Optional[str] = None) -> None:
        return

    def finish(self, desc: str = '完成') -> None:
        return

    def error(self, desc: str = '失败') -> None:
        return


class LoadingDriver:
    """加载进度驱动器，提供 step/finish/error 三个统一接口。"""

    def __init__(
        self,
        bar: ttk.Progressbar,
        text_var: tk.StringVar,
        max_steps: int = 100
    ) -> None:
        self._bar = bar
        self._text_var = text_var
        self._main_thread_id = threading.get_ident()
        self._lock = threading.Lock()
        self._pending_value: Optional[int] = 0
        self._pending_desc: Optional[str] = None
        self._bar.configure(maximum=max_steps, value=0)

    def _set_pending(self, value: Optional[int], desc: Optional[str]) -> None:
        with self._lock:
            if value is not None:
                self._pending_value = min(max(value, 0), int(self._bar['maximum']))
            if desc is not None:
                self._pending_desc = desc

    def _flush_pending(self) -> None:
        with self._lock:
            value = self._pending_value
            desc = self._pending_desc
            self._pending_value = None
            self._pending_desc = None
        if value is not None:
            self._bar['value'] = value
        if desc is not None:
            self._text_var.set(desc)
        self._bar.update_idletasks()

    def step(self, value: int, desc: Optional[str] = None) -> None:
        self._set_pending(value, desc)
        if threading.get_ident() == self._main_thread_id:
            self._flush_pending()

    def finish(self, desc: str = '完成') -> None:
        self._set_pending(int(self._bar['maximum']), desc)
        if threading.get_ident() == self._main_thread_id:
            self._flush_pending()

    def error(self, desc: str = '失败') -> None:
        self._set_pending(None, desc)
        if threading.get_ident() == self._main_thread_id:
            self._flush_pending()

    def drain(self) -> None:
        """在 UI 主线程拉取并刷新最新进度状态。"""
        self._flush_pending()

    @staticmethod
    def noop() -> _NoopLoadingDriver:
        return _NoopLoadingDriver()
