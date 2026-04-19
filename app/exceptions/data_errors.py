from __future__ import annotations

from app.exceptions.base import AppError


class DataNotLoadedError(AppError):
    """访问了尚未加载的数据（如未上传对应文件）。"""

    def __init__(self, data_type: str, case_id: str | None = None) -> None:
        message = f"数据未加载：{data_type}"
        if case_id:
            message += f"（案件ID: {case_id}）"
        super().__init__(message, code="DATA_NOT_LOADED", details={"data_type": data_type, "case_id": case_id})


class EmptyDataError(AppError):
    """数据为空：DataFrame 无行、或业务上视为无有效记录。"""

    def __init__(self, data_type: str, case_id: str | None = None, *, hint: str | None = None) -> None:
        message = f"数据为空：{data_type}"
        if case_id:
            message += f"（案件ID: {case_id}）"
        if hint:
            message += f"，{hint}"
        super().__init__(
            message,
            code="EMPTY_DATA",
            details={"data_type": data_type, "case_id": case_id, "hint": hint},
        )


class MissingColumnError(AppError):
    """表结构缺少必需列（与业务「字段缺失」对应，列名即字段名）。"""

    def __init__(self, data_type: str, missing_columns: list[str]) -> None:
        cols = ", ".join(missing_columns)
        message = f"字段缺失：{data_type}，缺少列：{cols}"
        super().__init__(
            message,
            code="MISSING_COLUMN",
            details={"data_type": data_type, "missing_columns": missing_columns},
        )


class MissingFieldError(AppError):
    """与 MissingColumnError 同义，便于业务层按「字段」一词抛出（code 区分）。"""

    def __init__(self, data_type: str, missing_fields: list[str]) -> None:
        fields = ", ".join(missing_fields)
        message = f"字段缺失：{data_type}，缺少：{fields}"
        super().__init__(
            message,
            code="MISSING_FIELD",
            details={"data_type": data_type, "missing_fields": missing_fields},
        )


class InvalidDateFormatError(AppError):
    """日期字段无法按预期解析（仅日期部分）。"""

    def __init__(self, column_name: str, data_type: str, sample_value: str | None = None) -> None:
        message = f"日期格式错误：{data_type}.{column_name}"
        if sample_value is not None:
            message += f"，示例值：{sample_value}"
        super().__init__(
            message,
            code="INVALID_DATE_FORMAT",
            details={"column_name": column_name, "data_type": data_type, "sample_value": sample_value},
        )


class InvalidTimeFormatError(AppError):
    """时间或日期时间字段无法按预期解析。"""

    def __init__(self, column_name: str, data_type: str, sample_value: str | None = None) -> None:
        message = f"时间格式错误：{data_type}.{column_name}"
        if sample_value is not None:
            message += f"，示例值：{sample_value}"
        super().__init__(
            message,
            code="INVALID_TIME_FORMAT",
            details={"column_name": column_name, "data_type": data_type, "sample_value": sample_value},
        )


class UnsupportedFileFormatError(AppError):
    """文件扩展名或类型不在支持范围内。"""

    def __init__(self, filename: str) -> None:
        message = f"不支持的文件格式：{filename}"
        super().__init__(message, code="UNSUPPORTED_FILE_FORMAT", details={"filename": filename})


class FileParseError(AppError):
    """文件已选但解析失败（编码、损坏、引擎等）。"""

    def __init__(self, filename: str, reason: str, *, cause: BaseException | None = None) -> None:
        message = f"文件解析失败：{filename}，原因：{reason}"
        super().__init__(
            message,
            code="FILE_PARSE_ERROR",
            details={"filename": filename, "reason": reason},
            cause=cause,
        )