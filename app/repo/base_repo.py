from __future__ import annotations

from typing import TypeVar, Generic, Type, Optional, List, Any
from sqlalchemy.orm import Session

from app.core.database import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """基础仓储类，提供通用的 CRUD 操作。"""

    def __init__(self, model: Type[ModelType]):
        """
        初始化仓储。

        Args:
            model: SQLAlchemy 模型类
        """
        self.model = model

    def get(self, db: Session, id: int) -> Optional[ModelType]:
        """
        根据 ID 获取记录。

        Args:
            db: 数据库会话
            id: 记录 ID

        Returns:
            记录对象，如果不存在则返回 None
        """
        return db.query(self.model).filter(self.model.id == id).first()

    def get_multi(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100
    ) -> List[ModelType]:
        """
        获取多条记录。

        Args:
            db: 数据库会话
            skip: 跳过的记录数
            limit: 返回的记录数限制

        Returns:
            记录列表
        """
        return db.query(self.model).offset(skip).limit(limit).all()

    def create(self, db: Session, *, obj_in: dict[str, Any]) -> ModelType:
        """
        创建新记录。

        Args:
            db: 数据库会话
            obj_in: 创建数据的字典

        Returns:
            创建的记录对象
        """
        db_obj = self.model(**obj_in)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(
        self,
        db: Session,
        *,
        db_obj: ModelType,
        obj_in: dict[str, Any]
    ) -> ModelType:
        """
        更新记录。

        Args:
            db: 数据库会话
            db_obj: 要更新的记录对象
            obj_in: 更新数据的字典

        Returns:
            更新后的记录对象
        """
        for field, value in obj_in.items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, *, id: int) -> Optional[ModelType]:
        """
        删除记录。

        Args:
            db: 数据库会话
            id: 记录 ID

        Returns:
            被删除的记录对象，如果不存在则返回 None
        """
        obj = self.get(db, id)
        if obj:
            db.delete(obj)
            db.commit()
        return obj

    def count(self, db: Session, *, filters: Optional[dict[str, Any]] = None) -> int:
        """
        统计记录数。

        Args:
            db: 数据库会话
            filters: 过滤条件字典

        Returns:
            记录数
        """
        query = db.query(self.model)
        if filters:
            for key, value in filters.items():
                if hasattr(self.model, key):
                    query = query.filter(getattr(self.model, key) == value)
        return query.count()