# app/core/database.py
"""
MySQL 数据库连接管理（SQLAlchemy 2.x + PyMySQL）。
对外暴露：engine、SessionLocal、Base、init_db()

持久化边界（与业务分析解耦）：
  - 运行时分析结果默认在 ``AppState`` 内存中，GUI 侧通过 CSV 导出落盘（见 ``ResultPanel``）。
  - ORM / ``app.repo`` 用于任务、上传记录等表结构；后续将「分析结果快照」写入 MySQL 时，
    建议新增专用 Repository 与 Service，在 ``TaskManager`` 回调或显式「归档」动作中调用，
    避免在 GUI 控件内直接写 SQL。
"""
from __future__ import annotations

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.config_db import db as db_config
from app.utils.logger import get_logger

logger = get_logger(__name__)


# ─────────────────────────────────────────────
#  Engine（全局唯一）
# ─────────────────────────────────────────────

engine = create_engine(
    db_config.url(),
    pool_recycle=db_config.POOL_RECYCLE,
    pool_pre_ping=db_config.POOL_PRE_PING,
    pool_size=db_config.POOL_SIZE,
    max_overflow=db_config.MAX_OVERFLOW,
    echo=False,   # 改为 True 可在控制台打印所有 SQL，调试时用
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


# ─────────────────────────────────────────────
#  ORM 基类（所有 Model 继承这个）
# ─────────────────────────────────────────────

class Base(DeclarativeBase):
    pass


# ─────────────────────────────────────────────
#  初始化：建表 + 连接检查
# ─────────────────────────────────────────────

def init_db() -> None:
    """
    应用启动时调用。
    - 检查数据库连接是否正常
    - 按 ORM Model 定义自动建表（已存在的表不会重建）
    """
    # 连接检查
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    logger.info("MySQL 连接正常：%s:%s/%s", db_config.HOST, db_config.PORT, db_config.NAME)

    # 导入所有 Model，确保 Base.metadata 能感知到它们
    # 每新增一个 Model 文件，在这里加一行 import
    from app.repo import upload_repo, case_repo, result_repo, log_repo  # noqa: F401

    Base.metadata.create_all(bind=engine)
    logger.info("数据库表结构同步完成")