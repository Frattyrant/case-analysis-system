from __future__ import annotations


class AppError(Exception):
    """应用基础异常，所有业务异常继承此类。"""

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        details: dict | None = None,
        cause: BaseException | None = None,
    ) -> None:
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)
        if cause is not None:
            self.__cause__ = cause