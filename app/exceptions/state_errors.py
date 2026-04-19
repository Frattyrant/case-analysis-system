from __future__ import annotations

from app.exceptions.base import AppError


class CaseNotSelectedError(AppError):
    """未选择当前案件。"""

    def __init__(self) -> None:
        message = "当前没有选择案件，请先选择或创建案件"
        super().__init__(message, code="CASE_NOT_SELECTED")


class CaseNotFoundError(AppError):
    """案件 ID 不在内存案件列表中。"""

    def __init__(self, case_id: str) -> None:
        message = f"案件不存在：{case_id}"
        super().__init__(message, code="CASE_NOT_FOUND", details={"case_id": case_id})


class SlotNotRegisteredError(AppError):
    """Schema 中未注册该 slot key。"""

    def __init__(self, key: str) -> None:
        message = f"字段未注册：'{key}'，请先调用 StateManager.register()"
        super().__init__(message, code="SLOT_NOT_REGISTERED", details={"key": key})


class InvalidCaseStateError(AppError):
    """当前案件数据不满足该操作的前置条件。"""

    def __init__(self, case_id: str, operation: str, reason: str) -> None:
        message = f"无效的案件状态：案件 {case_id} 无法执行 {operation}，原因：{reason}"
        super().__init__(
            message,
            code="INVALID_CASE_STATE",
            details={"case_id": case_id, "operation": operation, "reason": reason},
        )


class SlotNotFoundError(AppError):
    """案件上下文中无法解析到该业务字段（与未注册 schema 区分使用）。"""

    def __init__(self, case_id: str, key: str) -> None:
        message = f"字段不存在：案件 {case_id} 中不存在字段 '{key}'"
        super().__init__(message, code="SLOT_NOT_FOUND", details={"case_id": case_id, "key": key})