from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import String, DateTime, Integer, Text, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column
import enum

from app.core.database import Base
from app.repo.base_repo import BaseRepository


class LogLevel(str, enum.Enum):
    """日志级别枚举。"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class OperationLog(Base):
    """操作日志模型。"""

    __tablename__ = "operation_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="日志ID")
    case_id: Mapped[Optional[str]] = mapped_column(String(50), index=True, nullable=True, comment="案件ID")
    task_id: Mapped[Optional[str]] = mapped_column(String(100), index=True, nullable=True, comment="任务ID")
    user_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="用户ID")
    operation_type: Mapped[str] = mapped_column(String(50), comment="操作类型（upload/analysis/export/delete等）")
    operation_name: Mapped[str] = mapped_column(String(100), comment="操作名称")
    level: Mapped[LogLevel] = mapped_column(SQLEnum(LogLevel), default=LogLevel.INFO, comment="日志级别")
    message: Mapped[str] = mapped_column(Text, comment="日志消息")
    details: Mapped[Optional[dict]] = mapped_column(Text, nullable=True, comment="详细信息（JSON格式）")
    ip_address: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="IP地址")
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, comment="用户代理")
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="执行时长（毫秒）")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True, comment="创建时间")


class LogRepository(BaseRepository[OperationLog]):
    """操作日志仓储。"""

    def __init__(self):
        super().__init__(OperationLog)

    def create_log(
        self,
        db,
        *,
        case_id: Optional[str] = None,
        task_id: Optional[str] = None,
        user_id: Optional[str] = None,
        operation_type: str,
        operation_name: str,
        level: LogLevel = LogLevel.INFO,
        message: str,
        details: Optional[dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        duration_ms: Optional[int] = None
    ) -> OperationLog:
        """
        创建操作日志。

        Args:
            db: 数据库会话
            case_id: 案件ID
            task_id: 任务ID
            user_id: 用户ID
            operation_type: 操作类型
            operation_name: 操作名称
            level: 日志级别
            message: 日志消息
            details: 详细信息
            ip_address: IP地址
            user_agent: 用户代理
            duration_ms: 执行时长

        Returns:
            创建的日志记录
        """
        import json
        log_data = {
            "case_id": case_id,
            "task_id": task_id,
            "user_id": user_id,
            "operation_type": operation_type,
            "operation_name": operation_name,
            "level": level,
            "message": message,
            "details": json.dumps(details) if details else None,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "duration_ms": duration_ms
        }
        return self.create(db, obj_in=log_data)

    def get_by_case_id(
        self,
        db,
        case_id: str,
        *,
        skip: int = 0,
        limit: int = 100,
        level: Optional[LogLevel] = None
    ) -> List[OperationLog]:
        """
        获取指定案件的日志。

        Args:
            db: 数据库会话
            case_id: 案件ID
            skip: 跳过的记录数
            limit: 返回的记录数限制
            level: 日志级别过滤

        Returns:
            日志记录列表
        """
        from sqlalchemy import select, desc
        query = select(OperationLog).where(OperationLog.case_id == case_id)
        
        if level:
            query = query.where(OperationLog.level == level)
        
        query = query.order_by(desc(OperationLog.created_at)).offset(skip).limit(limit)
        result = db.execute(query)
        return list(result.scalars().all())

    def get_by_task_id(self, db, task_id: str) -> List[OperationLog]:
        """
        获取指定任务的日志。

        Args:
            db: 数据库会话
            task_id: 任务ID

        Returns:
            日志记录列表
        """
        from sqlalchemy import select, desc
        query = select(OperationLog).where(
            OperationLog.task_id == task_id
        ).order_by(desc(OperationLog.created_at))
        result = db.execute(query)
        return list(result.scalars().all())

    def get_by_operation_type(
        self,
        db,
        operation_type: str,
        *,
        skip: int = 0,
        limit: int = 100
    ) -> List[OperationLog]:
        """
        获取指定操作类型的日志。

        Args:
            db: 数据库会话
            operation_type: 操作类型
            skip: 跳过的记录数
            limit: 返回的记录数限制

        Returns:
            日志记录列表
        """
        from sqlalchemy import select, desc
        query = select(OperationLog).where(
            OperationLog.operation_type == operation_type
        ).order_by(desc(OperationLog.created_at)).offset(skip).limit(limit)
        result = db.execute(query)
        return list(result.scalars().all())

    def get_error_logs(
        self,
        db,
        *,
        skip: int = 0,
        limit: int = 100,
        case_id: Optional[str] = None
    ) -> List[OperationLog]:
        """
        获取错误日志。

        Args:
            db: 数据库会话
            skip: 跳过的记录数
            limit: 返回的记录数限制
            case_id: 案件ID（可选）

        Returns:
            错误日志列表
        """
        from sqlalchemy import select, desc
        query = select(OperationLog).where(
            OperationLog.level.in_([LogLevel.ERROR, LogLevel.CRITICAL])
        )
        
        if case_id:
            query = query.where(OperationLog.case_id == case_id)
        
        query = query.order_by(desc(OperationLog.created_at)).offset(skip).limit(limit)
        result = db.execute(query)
        return list(result.scalars().all())

    def delete_old_logs(self, db, days: int = 30) -> int:
        """
        删除指定天数之前的旧日志。

        Args:
            db: 数据库会话
            days: 保留天数

        Returns:
            删除的记录数
        """
        from sqlalchemy import delete
        from datetime import timedelta
        
        cutoff_date = datetime.now() - timedelta(days=days)
        stmt = delete(OperationLog).where(OperationLog.created_at < cutoff_date)
        result = db.execute(stmt)
        db.commit()
        return result.rowcount

    def get_statistics_by_case(self, db, case_id: str) -> dict:
        """
        获取指定案件的日志统计信息。

        Args:
            db: 数据库会话
            case_id: 案件ID

        Returns:
            统计信息字典
        """
        from sqlalchemy import select, func
        
        total = self.count(db, filters={"case_id": case_id})
        
        query = select(
            OperationLog.level,
            func.count(OperationLog.id).label("count")
        ).where(
            OperationLog.case_id == case_id
        ).group_by(OperationLog.level)
        
        result = db.execute(query)
        level_counts = {row.level: row.count for row in result.all()}
        
        return {
            "total": total,
            "by_level": level_counts
        }