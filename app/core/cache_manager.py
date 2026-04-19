# app/core/cache_manager.py
"""
DataFrame 内存缓存（LRU）。

背景：
  轨迹、租赁等大文件上传后解析成 DataFrame，每次分析都从磁盘重新读
  会很慢。CacheManager 把解析结果缓存在内存里，相同文件直接命中。

用法：
    cache = CacheManager(max_size=10)
    df = cache.get('轨迹_case001')
    if df is None:
        df = parse_file(...)
        cache.set('轨迹_case001', df)
"""
from __future__ import annotations

from collections import OrderedDict

import pandas as pd

from app.utils.logger import get_logger

logger = get_logger(__name__)


class CacheManager:
    """
    简单的 LRU 缓存，专门用于 DataFrame。
    key 建议格式：'{文件类型}_{case_id}'，如 '轨迹_case001'
    """

    def __init__(self, max_size: int = 20) -> None:
        self._max_size = max_size
        self._store: OrderedDict[str, pd.DataFrame] = OrderedDict()

    def get(self, key: str) -> pd.DataFrame | None:
        """命中返回 DataFrame，未命中返回 None。"""
        if key not in self._store:
            return None
        # 访问后移到末尾（最近使用）
        self._store.move_to_end(key)
        logger.debug("缓存命中：%s", key)
        return self._store[key]

    def set(self, key: str, df: pd.DataFrame) -> None:
        """写入缓存，超出容量时淘汰最久未使用的条目。"""
        if key in self._store:
            self._store.move_to_end(key)
        self._store[key] = df
        if len(self._store) > self._max_size:
            evicted, _ = self._store.popitem(last=False)
            logger.debug("缓存淘汰：%s（已达上限 %d）", evicted, self._max_size)

    def delete(self, key: str) -> None:
        """主动删除某个缓存条目（如案件关闭时清理）。"""
        self._store.pop(key, None)

    def clear_by_case(self, case_id: str) -> None:
        """清除某个案件的所有缓存条目（key 中包含 case_id 的都删）。"""
        keys = [k for k in self._store if case_id in k]
        for k in keys:
            del self._store[k]
        logger.debug("已清除案件 %s 的 %d 条缓存", case_id, len(keys))

    def clear(self) -> None:
        """清空所有缓存。"""
        self._store.clear()

    def __len__(self) -> int:
        return len(self._store)

    def __repr__(self) -> str:
        return f"CacheManager(size={len(self._store)}/{self._max_size})"


# ─────────────────────────────────────────────
#  全局单例（应用内共享一个缓存）
# ─────────────────────────────────────────────

_global_cache = CacheManager(max_size=20)


def get_cache() -> CacheManager:
    """获取全局缓存实例。"""
    return _global_cache