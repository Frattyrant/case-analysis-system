from __future__ import annotations

from app.exceptions.base import AppError


class DatabaseConnectionError(AppError):
    """无法建立或校验数据库连接。"""

    def __init__(self, reason: str) -> None:
        message = f"数据库连接失败：{reason}"
        super().__init__(message, code="DATABASE_CONNECTION_ERROR", details={"reason": reason})


class QueryExecutionError(AppError):
    """SQL 执行失败。"""

    def __init__(self, table: str, operation: str, reason: str) -> None:
        message = f"查询执行失败：{table}.{operation}，原因：{reason}"
        super().__init__(
            message,
            code="QUERY_EXECUTION_ERROR",
            details={"table": table, "operation": operation, "reason": reason},
        )


class TransactionError(AppError):
    """事务提交或回滚失败。"""

    def __init__(self, operation: str, reason: str) -> None:
        message = f"事务执行失败：{operation}，原因：{reason}"
        super().__init__(message, code="TRANSACTION_ERROR", details={"operation": operation, "reason": reason})


class RecordNotFoundError(AppError):
    """按主键或条件查询无记录。"""

    def __init__(self, table: str, record_id: int | str) -> None:
        message = f"记录不存在：{table} 中不存在 ID 为 {record_id} 的记录"
        super().__init__(message, code="RECORD_NOT_FOUND", details={"table": table, "record_id": record_id})


class DuplicateRecordError(AppError):
    """唯一约束冲突。"""

    def __init__(self, table: str, key: str, value: str) -> None:
        message = f"重复记录：{table} 中已存在 {key}={value} 的记录"
        super().__init__(message, code="DUPLICATE_RECORD", details={"table": table, "key": key, "value": value})