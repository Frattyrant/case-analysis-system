# app/core/state_manager.py
"""
AppState + SlotSpec + StateManager。

  - AppState 去掉单例模式，改为普通实例，由 StateManager 按 case_id 管理
  - StateManager 负责创建/获取/销毁/切换 AppState 实例
  - SlotSpec 和 AppState 内部逻辑与 notebook 完全一致，直接迁移
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

import pandas as pd


# ─────────────────────────────────────────────
#  SlotSpec：字段描述符（与 notebook 完全相同）
# ─────────────────────────────────────────────

@dataclass
class SlotSpec:
    key:             str
    default_factory: Callable[[], Any]
    description:     str = ""


# ─────────────────────────────────────────────
#  AppState：单个案件的数据容器（去掉单例）
# ─────────────────────────────────────────────

class AppState:
    """
    单个案件的运行时数据容器。
    不再是单例，由 StateManager 按 case_id 管理多个实例。
    """

    # 类级别注册表，所有实例共享同一份 schema
    _registry: dict[str, SlotSpec] = {}

    @classmethod
    def _register_spec(cls, spec: SlotSpec) -> None:
        """内部方法，由 StateManager.register() 调用。"""
        if spec.key not in cls._registry:
            cls._registry[spec.key] = spec

    @classmethod
    def registered_keys(cls) -> list[str]:
        return list(cls._registry.keys())

    # ── 实例初始化 ──────────────────────────────
    def __init__(self, case_id: str) -> None:
        object.__setattr__(self, '_case_id', case_id)
        object.__setattr__(self, '_store', {})
        self._init_all()

    @property
    def case_id(self) -> str:
        return object.__getattribute__(self, '_case_id')

    def _init_all(self) -> None:
        store: dict = object.__getattribute__(self, '_store')
        for key, spec in self._registry.items():
            store[key] = spec.default_factory()

    # ── 读写接口（字典风格）──────────────────────
    def __getitem__(self, key: str) -> Any:
        store: dict = object.__getattribute__(self, '_store')
        if key not in self._registry:
            raise KeyError(f"[AppState] '{key}' 未注册，请先调用 StateManager.register()。")
        return store[key]

    def __setitem__(self, key: str, value: Any) -> None:
        store: dict = object.__getattribute__(self, '_store')
        if key not in self._registry:
            raise KeyError(f"[AppState] '{key}' 未注册，请先调用 StateManager.register()。")
        store[key] = value

    # ── 读写接口（属性风格，兼容旧代码）────────────
    def __getattr__(self, key: str) -> Any:
        try:
            return self[key]
        except KeyError:
            raise AttributeError(f"[AppState] 属性 '{key}' 未注册。") from None

    def __setattr__(self, key: str, value: Any) -> None:
        if key.startswith('_'):
            object.__setattr__(self, key, value)
        else:
            self[key] = value

    # ── 工具方法 ────────────────────────────────
    def reset(self) -> None:
        """重置当前案件的所有字段为默认值。"""
        self._init_all()

    def snapshot(self) -> dict[str, Any]:
        """返回当前所有字段的浅拷贝，用于调试或序列化。"""
        store: dict = object.__getattribute__(self, '_store')
        return dict(store)

    def __repr__(self) -> str:
        store: dict = object.__getattribute__(self, '_store')
        lines = [f"AppState(case_id={self.case_id!r}, {len(self._registry)} 个字段)"]
        for key, spec in self._registry.items():
            val = store.get(key, '<未初始化>')
            preview = repr(val)[:60] + ("…" if len(repr(val)) > 60 else "")
            lines.append(f"  {key:<35} = {preview}")
            if spec.description:
                lines.append(f"  {'':35}   # {spec.description}")
        return "\n".join(lines)


# ─────────────────────────────────────────────
#  StateManager：多案件生命周期管理
# ─────────────────────────────────────────────

class StateManager:
    """
    管理所有案件的 AppState 实例。

    典型用法：
        # 启动时注册字段（main.py 里调用一次）
        StateManager.register([SlotSpec(...), ...])

        # 新建案件
        state = StateManager.create('case_001')

        # 切换到已有案件
        StateManager.switch('case_001')

        # 获取当前案件
        state = StateManager.current()

        # 关闭案件（释放内存）
        StateManager.destroy('case_001')
    """

    # 所有活跃案件的 AppState 实例
    _cases:          dict[str, AppState] = {}

    # 当前活跃案件 ID
    _current_case_id: str | None = None

    # ── 字段注册（启动时调用一次）────────────────
    @classmethod
    def register(cls, specs: list[SlotSpec]) -> None:
        """
        注册业务字段。必须在 create() 之前调用。
        已注册的 key 跳过，不报错（支持重复调用）。
        """
        for spec in specs:
            AppState._register_spec(spec)

    @classmethod
    def registered_keys(cls) -> list[str]:
        return AppState.registered_keys()

    # ── 案件生命周期 ─────────────────────────────
    @classmethod
    def create(cls, case_id: str) -> AppState:
        """
        新建一个案件的 AppState 并切换到它。
        如果 case_id 已存在则直接切换，不重新创建。
        """
        if case_id not in cls._cases:
            cls._cases[case_id] = AppState(case_id)
        cls._current_case_id = case_id
        return cls._cases[case_id]

    @classmethod
    def get(cls, case_id: str) -> AppState:
        """
        获取指定案件的 AppState（不切换当前案件）。
        案件不存在时抛出 KeyError。
        """
        if case_id not in cls._cases:
            raise KeyError(f"[StateManager] 案件 '{case_id}' 不存在，请先调用 create()。")
        return cls._cases[case_id]

    @classmethod
    def current(cls) -> AppState:
        """
        获取当前活跃案件的 AppState。
        没有活跃案件时抛出 RuntimeError。
        """
        if cls._current_case_id is None or cls._current_case_id not in cls._cases:
            raise RuntimeError("[StateManager] 当前没有活跃案件，请先调用 create()。")
        return cls._cases[cls._current_case_id]

    @classmethod
    def switch(cls, case_id: str) -> AppState:
        """切换当前活跃案件。"""
        state = cls.get(case_id)
        cls._current_case_id = case_id
        return state

    @classmethod
    def destroy(cls, case_id: str) -> None:
        """
        销毁指定案件的 AppState，释放内存中的 DataFrame 等大对象。
        如果销毁的是当前案件，current_case_id 置为 None。
        """
        cls._cases.pop(case_id, None)
        if cls._current_case_id == case_id:
            cls._current_case_id = None

    @classmethod
    def list_cases(cls) -> list[str]:
        """返回当前内存中所有活跃案件的 case_id 列表。"""
        return list(cls._cases.keys())

    @classmethod
    def current_case_id(cls) -> str | None:
        return cls._current_case_id