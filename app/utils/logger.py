# app/utils/logger.py
"""
统一日志配置。
所有模块通过 get_logger(__name__) 获取 logger，不直接用 logging.getLogger。
"""
from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path

from app.config_db import log as log_config


def _setup_root_logger() -> None:
    root = logging.getLogger()
    if root.handlers:
        return  # 已初始化，跳过

    fmt = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 控制台输出
    console = logging.StreamHandler()
    console.setFormatter(fmt)
    root.addHandler(console)

    # 文件输出（按大小滚动）
    file_handler = logging.handlers.RotatingFileHandler(
        filename=log_config.FILE,
        maxBytes=log_config.MAX_BYTES,
        backupCount=log_config.BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setFormatter(fmt)
    root.addHandler(file_handler)

    root.setLevel(log_config.LEVEL)


_setup_root_logger()


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)