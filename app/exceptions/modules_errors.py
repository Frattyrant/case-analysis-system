from __future__ import annotations

from app.exceptions.base import AppError


class ModuleExecutionError(AppError):
    """分析模块执行失败（逻辑异常、数据异常未捕获时统一包装）。"""

    def __init__(
        self,
        module_name: str,
        reason: str,
        *,
        cause: BaseException | None = None,
    ) -> None:
        message = f"模块执行失败：{module_name}，原因：{reason}"
        super().__init__(
            message,
            code="MODULE_EXECUTION_ERROR",
            details={"module_name": module_name, "reason": reason},
            cause=cause,
        )


class UnsupportedAnalysisTypeError(AppError):
    """请求的分析类型不在支持列表内。"""

    def __init__(self, analysis_type: str, supported_types: list[str]) -> None:
        message = f"不支持的分析类型：{analysis_type}，支持的类型：{', '.join(supported_types)}"
        super().__init__(
            message,
            code="UNSUPPORTED_ANALYSIS_TYPE",
            details={"analysis_type": analysis_type, "supported_types": supported_types},
        )


class AnalysisChainBreakError(AppError):
    """前置步骤未完成，当前模块无法继续。"""

    def __init__(self, current_module: str, missing_dependency: str) -> None:
        message = f"分析链中断：{current_module} 需要前置条件 {missing_dependency}"
        super().__init__(
            message,
            code="ANALYSIS_CHAIN_BREAK",
            details={"current_module": current_module, "missing_dependency": missing_dependency},
        )


class InvalidParameterError(AppError):
    """模块入参不合法。"""

    def __init__(self, module_name: str, parameter: str, reason: str) -> None:
        message = f"无效参数：{module_name}.{parameter}，原因：{reason}"
        super().__init__(
            message,
            code="INVALID_PARAMETER",
            details={"module_name": module_name, "parameter": parameter, "reason": reason},
        )


class TaskNotFoundError(AppError):
    """指定任务 ID 不存在。"""

    def __init__(self, task_id: str) -> None:
        message = f"任务不存在：{task_id}"
        super().__init__(message, code="TASK_NOT_FOUND", details={"task_id": task_id})


class TaskExecutionError(AppError):
    """后台任务执行失败。"""

    def __init__(self, task_id: str, reason: str, *, cause: BaseException | None = None) -> None:
        message = f"任务执行失败：{task_id}，原因：{reason}"
        super().__init__(
            message,
            code="TASK_EXECUTION_ERROR",
            details={"task_id": task_id, "reason": reason},
            cause=cause,
        )