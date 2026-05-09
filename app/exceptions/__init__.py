"""
Exceptions package initialization.
"""
from __future__ import annotations

from app.exceptions.base import AppError
from app.exceptions.data_errors import (
    DataNotLoadedError,
    EmptyDataError,
    MissingColumnError,
    MissingFieldError,
    InvalidDateFormatError,
    InvalidTimeFormatError,
    UnsupportedFileFormatError,
    FileParseError,
)
from app.exceptions.state_errors import (
    CaseNotSelectedError,
    CaseNotFoundError,
    SlotNotRegisteredError,
    InvalidCaseStateError,
    SlotNotFoundError,
)
from app.exceptions.database_errors import (
    DatabaseConnectionError,
    QueryExecutionError,
    TransactionError,
    RecordNotFoundError,
    DuplicateRecordError,
)
from app.exceptions.modules_errors import (
    ModuleExecutionError,
    UnsupportedAnalysisTypeError,
    AnalysisChainBreakError,
    InvalidParameterError,
    TaskNotFoundError,
    TaskExecutionError,
)

__all__ = [
    'AppError',
    'DataNotLoadedError',
    'EmptyDataError',
    'MissingColumnError',
    'MissingFieldError',
    'InvalidDateFormatError',
    'InvalidTimeFormatError',
    'UnsupportedFileFormatError',
    'FileParseError',
    'CaseNotSelectedError',
    'CaseNotFoundError',
    'SlotNotRegisteredError',
    'InvalidCaseStateError',
    'SlotNotFoundError',
    'DatabaseConnectionError',
    'QueryExecutionError',
    'TransactionError',
    'RecordNotFoundError',
    'DuplicateRecordError',
    'ModuleExecutionError',
    'UnsupportedAnalysisTypeError',
    'AnalysisChainBreakError',
    'InvalidParameterError',
    'TaskNotFoundError',
    'TaskExecutionError',
]