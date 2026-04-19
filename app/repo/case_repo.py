from __future__ import annotations

from datetime import datetime
from typing import Optional, List

from sqlalchemy import String, DateTime, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.repo.base_repo import BaseRepository


class CaseInfo(Base):
    """案件信息模型。"""

    __tablename__ = "case_info"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="案件ID")
    case_id: Mapped[str] = mapped_column(String(50), unique=True, index=True, comment="案件ID")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="案件描述")
    profile_gender: Mapped[Optional[str]] = mapped_column(String(10), nullable=True, comment="嫌疑人性别")
    profile_region: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, comment="嫌疑人户籍")
    rental_company: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="租赁公司名称")
    car_brand: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="车辆品牌")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")


class CaseRepository(BaseRepository[CaseInfo]):
    """案件信息仓储。"""

    def __init__(self):
        super().__init__(CaseInfo)

    def get_by_case_id(self, db, case_id: str) -> Optional[CaseInfo]:
        """
        根据案件ID获取案件信息。

        Args:
            db: 数据库会话
            case_id: 案件ID

        Returns:
            案件信息，如果不存在则返回 None
        """
        from sqlalchemy import select
        query = select(CaseInfo).where(CaseInfo.case_id == case_id)
        result = db.execute(query)
        return result.scalar_one_or_none()

    def list_all(self, db, *, skip: int = 0, limit: int = 100) -> List[CaseInfo]:
        """
        获取所有案件列表。

        Args:
            db: 数据库会话
            skip: 跳过的记录数
            limit: 返回的记录数限制

        Returns:
            案件列表
        """
        from sqlalchemy import select, desc
        query = select(CaseInfo).order_by(desc(CaseInfo.created_at)).offset(skip).limit(limit)
        result = db.execute(query)
        return list(result.scalars().all())

    def create_case(
        self,
        db,
        case_id: str,
        description: Optional[str] = None,
        profile_gender: Optional[str] = None,
        profile_region: Optional[str] = None,
        rental_company: Optional[str] = None,
        car_brand: Optional[str] = None
    ) -> CaseInfo:
        """
        创建新案件。

        Args:
            db: 数据库会话
            case_id: 案件ID
            description: 案件描述
            profile_gender: 嫌疑人性别
            profile_region: 嫌疑人户籍
            rental_company: 租赁公司名称
            car_brand: 车辆品牌

        Returns:
            创建的案件信息
        """
        case_data = {
            "case_id": case_id,
            "description": description,
            "profile_gender": profile_gender,
            "profile_region": profile_region,
            "rental_company": rental_company,
            "car_brand": car_brand
        }
        return self.create(db, obj_in=case_data)

    def update_case(
        self,
        db,
        case_id: str,
        *,
        description: Optional[str] = None,
        profile_gender: Optional[str] = None,
        profile_region: Optional[str] = None,
        rental_company: Optional[str] = None,
        car_brand: Optional[str] = None
    ) -> Optional[CaseInfo]:
        """
        更新案件信息。

        Args:
            db: 数据库会话
            case_id: 案件ID
            description: 案件描述
            profile_gender: 嫌疑人性别
            profile_region: 嫌疑人户籍
            rental_company: 租赁公司名称
            car_brand: 车辆品牌

        Returns:
            更新后的案件信息，如果不存在则返回 None
        """
        case = self.get_by_case_id(db, case_id)
        if case:
            update_data = {}
            if description is not None:
                update_data["description"] = description
            if profile_gender is not None:
                update_data["profile_gender"] = profile_gender
            if profile_region is not None:
                update_data["profile_region"] = profile_region
            if rental_company is not None:
                update_data["rental_company"] = rental_company
            if car_brand is not None:
                update_data["car_brand"] = car_brand

            if update_data:
                return self.update(db, db_obj=case, obj_in=update_data)
        return None

    def delete_by_case_id(self, db, case_id: str) -> int:
        """
        删除指定案件。

        Args:
            db: 数据库会话
            case_id: 案件ID

        Returns:
            删除的记录数
        """
        from sqlalchemy import delete
        stmt = delete(CaseInfo).where(CaseInfo.case_id == case_id)
        result = db.execute(stmt)
        db.commit()
        return result.rowcount