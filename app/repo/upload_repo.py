from __future__ import annotations

from datetime import datetime
from typing import Optional, List

from sqlalchemy import String, DateTime, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.repo.base_repo import BaseRepository


class UploadRecord(Base):
    """文件上传记录模型。"""

    __tablename__ = "upload_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="记录ID")
    case_id: Mapped[str] = mapped_column(String(50), index=True, comment="案件ID")
    filename: Mapped[str] = mapped_column(String(255), comment="文件名")
    file_type: Mapped[str] = mapped_column(String(50), comment="文件类型（航班/轨迹/租赁/住宿/机动车等）")
    file_size: Mapped[int] = mapped_column(Integer, comment="文件大小（字节）")
    row_count: Mapped[int] = mapped_column(Integer, comment="数据行数")
    upload_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="上传时间")
    status: Mapped[str] = mapped_column(String(20), default="success", comment="上传状态")
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="错误信息")


class UploadRepository(BaseRepository[UploadRecord]):
    """文件上传记录仓储。"""

    def __init__(self):
        super().__init__(UploadRecord)

    def get_by_case_id(
        self,
        db,
        case_id: str,
        *,
        skip: int = 0,
        limit: int = 100
    ) -> List[UploadRecord]:
        """
        获取指定案件的上传记录。

        Args:
            db: 数据库会话
            case_id: 案件ID
            skip: 跳过的记录数
            limit: 返回的记录数限制

        Returns:
            上传记录列表
        """
        from sqlalchemy import select, desc
        query = select(UploadRecord).where(
            UploadRecord.case_id == case_id
        ).order_by(desc(UploadRecord.upload_time)).offset(skip).limit(limit)
        result = db.execute(query)
        return list(result.scalars().all())

    def get_by_filename(self, db, case_id: str, filename: str) -> Optional[UploadRecord]:
        """
        根据案件ID和文件名获取记录。

        Args:
            db: 数据库会话
            case_id: 案件ID
            filename: 文件名

        Returns:
            上传记录，如果不存在则返回 None
        """
        from sqlalchemy import select
        query = select(UploadRecord).where(
            UploadRecord.case_id == case_id,
            UploadRecord.filename == filename
        )
        result = db.execute(query)
        return result.scalar_one_or_none()

    def create_record(
        self,
        db,
        case_id: str,
        filename: str,
        file_type: str,
        file_size: int,
        row_count: int,
        status: str = "success",
        error_message: Optional[str] = None
    ) -> UploadRecord:
        """
        创建上传记录。

        Args:
            db: 数据库会话
            case_id: 案件ID
            filename: 文件名
            file_type: 文件类型
            file_size: 文件大小
            row_count: 数据行数
            status: 上传状态
            error_message: 错误信息

        Returns:
            创建的上传记录
        """
        record_data = {
            "case_id": case_id,
            "filename": filename,
            "file_type": file_type,
            "file_size": file_size,
            "row_count": row_count,
            "status": status,
            "error_message": error_message
        }
        return self.create(db, obj_in=record_data)

    def delete_by_case_id(self, db, case_id: str) -> int:
        """
        删除指定案件的所有上传记录。

        Args:
            db: 数据库会话
            case_id: 案件ID

        Returns:
            删除的记录数
        """
        from sqlalchemy import delete
        stmt = delete(UploadRecord).where(UploadRecord.case_id == case_id)
        result = db.execute(stmt)
        db.commit()
        return result.rowcount