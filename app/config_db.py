# app/config_db.py
"""
全局配置。
所有路径、数据库参数、业务常量都从这里读取。
外部通过 `from app.config_db import settings` 使用。
"""
from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()  # 读取项目根目录的 .env 文件

# ─────────────────────────────────────────────
#  路径
# ─────────────────────────────────────────────
ROOT_DIR    = Path(__file__).resolve().parent.parent   # project_root/
DATA_DIR    = ROOT_DIR / "data"
UPLOAD_DIR  = DATA_DIR / "uploads"    # 原始上传文件，按 case_id 分子目录
EXPORT_DIR  = DATA_DIR / "exports"    # 导出的 CSV 结果
LOG_DIR     = ROOT_DIR / "logs"

# 确保目录存在（应用启动时自动创建）
for _d in (UPLOAD_DIR, EXPORT_DIR, LOG_DIR):
    _d.mkdir(parents=True, exist_ok=True)


# ─────────────────────────────────────────────
#  数据库（MySQL）
# ─────────────────────────────────────────────
class DatabaseConfig:
    HOST:     str = os.getenv("DB_HOST",     "localhost")
    PORT:     int = int(os.getenv("DB_PORT", "3306"))
    USER:     str = os.getenv("DB_USER",     "root")
    PASSWORD: str = os.getenv("DB_PASSWORD", "")
    NAME:     str = os.getenv("DB_NAME",     "case_analysis")

    # SQLAlchemy 连接串
    @classmethod
    def url(cls) -> str:
        return (
            f"mysql+pymysql://{cls.USER}:{cls.PASSWORD}"
            f"@{cls.HOST}:{cls.PORT}/{cls.NAME}"
            f"?charset=utf8mb4"
        )

    # 连接池参数
    POOL_RECYCLE:   int = 3600   # MySQL 默认 8h 断开，提前回收
    POOL_PRE_PING:  bool = True  # 每次取连接前先 ping，防止 "Lost connection"
    POOL_SIZE:      int = 5
    MAX_OVERFLOW:   int = 10


# ─────────────────────────────────────────────
#  业务常量
# ─────────────────────────────────────────────
class AnalysisConfig:
    # 同住关联：入住时间差阈值（小时）
    COHABIT_WINDOW_HOURS: int = 12

    # 文件上传：跳过前几行（原始表通常前两行是无效表头）
    EXCEL_SKIP_ROWS: int = 2

    # 分页表格每页默认行数
    TABLE_PAGE_SIZE: int = 10


# ─────────────────────────────────────────────
#  日志
# ─────────────────────────────────────────────
class LogConfig:
    LEVEL:      str  = os.getenv("LOG_LEVEL", "INFO")
    FILE:       Path = LOG_DIR / "app.log"
    MAX_BYTES:  int  = 10 * 1024 * 1024   # 10 MB
    BACKUP_COUNT: int = 3


# ─────────────────────────────────────────────
#  对外暴露的统一入口（按需选择粒度）
# ─────────────────────────────────────────────
db      = DatabaseConfig()
analysis = AnalysisConfig()
log     = LogConfig()