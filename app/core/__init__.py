"""
Core package initialization.
"""
from __future__ import annotations

from app.core.state_manager import StateManager, SlotSpec, AppState
from app.core.database import init_db, engine, SessionLocal, Base
from app.core.cache_manager import CacheManager, get_cache
from app.core.task_manager import TaskManager, get_task_manager

__all__ = [
    'StateManager',
    'SlotSpec',
    'AppState',
    'init_db',
    'engine',
    'SessionLocal',
    'Base',
    'CacheManager',
    'get_cache',
    'TaskManager',
    'get_task_manager',
]