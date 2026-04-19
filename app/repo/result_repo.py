from __future__ import annotations

from datetime import datetime
from typing import Optional, List

from sqlalchemy import String, DateTime, Integer, Text, JSON, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column
import enum

from app.core.database import Base
from app.repo.base_repo import BaseRepository


class TaskStatus(str, enum.Enum):
    """任务状态枚举。"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class AnalysisTask(Base):
    """分析任务模型。"""

    __tablename__ = "analysis_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="任务ID")
    task_id: Mapped[str] = mapped_column(String(100), unique=True, index=True, comment="任务ID")
    case_id: Mapped[str] = mapped_column(String(50), index=True, comment="案件ID")
    analysis_type: Mapped[str] = mapped_column(String(50), comment="分析类型（flight/trajectory/rental/lodging/vehicle等）")
    status: Mapped[TaskStatus] = mapped_column(SQLEnum(TaskStatus), default=TaskStatus.PENDING, comment="任务状态")
    parameters: Mapped[dict] = mapped_column(JSON, comment="分析参数")
    result_count: Mapped[int] = mapped_column(Integer, default=0, comment="结果记录数")
    result_file: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, comment="结果文件路径")
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="错误信息")
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, comment="开始时间")
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, comment="完成时间")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="创建时间")


class AnalysisResult(Base):
    """分析结果数据模型。"""

    __tablename__ = "analysis_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="记录ID")
    task_id: Mapped[str] = mapped_column(String(100), index=True, comment="任务ID")
    case_id: Mapped[str] = mapped_column(String(50), index=True, comment="案件ID")
    result_type: Mapped[str] = mapped_column(String(50), comment="结果类型")
    data: Mapped[dict] = mapped_column(JSON, comment="结果数据")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="创建时间")


class TaskRepository(BaseRepository[AnalysisTask]):
    """分析任务仓储。"""

    def __init__(self):
        super().__init__(AnalysisTask)

    def get_by_task_id(self, db, task_id: str) -> Optional[AnalysisTask]:
        """
        根据任务ID获取任务。

        Args:
            db: 数据库会话
            task_id: 任务ID

        Returns:
            任务记录，如果不存在则返回 None
        """
        from sqlalchemy import select
        query = select(AnalysisTask).where(AnalysisTask.task_id == task_id)
        result = db.execute(query)
        return result.scalar_one_or_none()

    def get_by_case_id(self, db, case_id: str, *, skip: int = 0, limit: int = 100) -> List[AnalysisTask]:
        """
        获取指定案件的所有任务。

        Args:
            db: 数据库会话
            case_id: 案件ID
            skip: 跳过的记录数
            limit: 返回的记录数限制

        Returns:
            任务记录列表
        """
        from sqlalchemy import select, desc
        query = select(AnalysisTask).where(
            AnalysisTask.case_id == case_id
        ).order_by(desc(AnalysisTask.created_at)).offset(skip).limit(limit)
        result = db.execute(query)
        return list(result.scalars().all())

    def create_task(
        self,
        db,
        task_id: str,
        case_id: str,
        analysis_type: str,
        **kwargs
    ) -> AnalysisTask:
        """
        创建新任务。

        Args:
            db: 数据库会话
            task_id: 任务ID
            case_id: 案件ID
            analysis_type: 分析类型
            **kwargs: 其他任务字段

        Returns:
            创建的任务记录
        """
        task_data = {
            "task_id": task_id,
            "case_id": case_id,
            "analysis_type": analysis_type,
            **kwargs
        }
        return self.create(db, obj_in=task_data)

    def update_status(
        self,
        db,
        task_id: str,
        status: TaskStatus,
        *,
        result_count: int = 0,
        result_file: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> Optional[AnalysisTask]:
        """
        更新任务状态。

        Args:
            db: 数据库会话
            task_id: 任务ID
            status: 新状态
            result_count: 结果记录数
            result_file: 结果文件路径
            error_message: 错误信息

        Returns:
            更新后的任务记录，如果不存在则返回 None
        """
        task = self.get_by_task_id(db, task_id)
        if task:
            update_data = {"status": status}
            
            if status == TaskStatus.RUNNING:
                update_data["started_at"] = datetime.now()
            elif status in (TaskStatus.SUCCESS, TaskStatus.FAILED):
                update_data["completed_at"] = datetime.now()
            
            if result_count is not None:
                update_data["result_count"] = result_count
            if result_file is not None:
                update_data["result_file"] = result_file
            if error_message is not None:
                update_data["error_message"] = error_message
            
            return self.update(db, db_obj=task, obj_in=update_data)
        return None

    def get_running_tasks(self, db) -> List[AnalysisTask]:
        """
        获取所有正在运行的任务。

        Args:
            db: 数据库会话

        Returns:
            正在运行的任务列表
        """
        from sqlalchemy import select
        query = select(AnalysisTask).where(AnalysisTask.status == TaskStatus.RUNNING)
        result = db.execute(query)
        return list(result.scalars().all())


class ResultRepository(BaseRepository[AnalysisResult]):
    """分析结果仓储。"""

    def __init__(self):
        super().__init__(AnalysisResult)

    def get_by_task_id(self, db, task_id: str) -> List[AnalysisResult]:
        """
        获取指定任务的所有结果。

        Args:
            db: 数据库会话
            task_id: 任务ID

        Returns:
            结果记录列表
        """
        from sqlalchemy import select
        query = select(AnalysisResult).where(AnalysisResult.task_id == task_id)
        result = db.execute(query)
        return list(result.scalars().all())

    def get_by_case_id(self, db, case_id: str, result_type: Optional[str] = None) -> List[AnalysisResult]:
        """
        获取指定案件的结果。

        Args:
            db: 数据库会话
            case_id: 案件ID
            result_type: 结果类型（可选）

        Returns:
            结果记录列表
        """
        from sqlalchemy import select, desc
        query = select(AnalysisResult).where(AnalysisResult.case_id == case_id)
        
        if result_type:
            query = query.where(AnalysisResult.result_type == result_type)
        
        query = query.order_by(desc(AnalysisResult.created_at))
        result = db.execute(query)
        return list(result.scalars().all())

    def create_result(
        self,
        db,
        task_id: str,
        case_id: str,
        result_type: str,
        data: dict
    ) -> AnalysisResult:
        """
        创建分析结果。

        Args:
            db: 数据库会话
            task_id: 任务ID
            case_id: 案件ID
            result_type: 结果类型
            data: 结果数据

        Returns:
            创建的结果记录
        """
        result_data = {
            "task_id": task_id,
            "case_id": case_id,
            "result_type": result_type,
            "data": data
        }
        return self.create(db, obj_in=result_data)

    def delete_by_task_id(self, db, task_id: str) -> int:
        """
        删除指定任务的所有结果。

        Args:
            db: 数据库会话
            task_id: 任务ID

        Returns:
            删除的记录数
        """
        from sqlalchemy import delete
        stmt = delete(AnalysisResult).where(AnalysisResult.task_id == task_id)
        result = db.execute(stmt)
        db.commit()
        return result.rowcount