"""Execution foundation errors."""

from __future__ import annotations


class ExecutionError(Exception):
    def __init__(self, detail: str, status_code: int = 400) -> None:
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


class ExecutionScopeError(ExecutionError):
    def __init__(self) -> None:
        super().__init__("Execution is not authorized for this company.", status_code=403)


class ExecutionStateError(ExecutionError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail, status_code=400)


class ExecutionPlanError(ExecutionError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail, status_code=400)


class ExecutionNotImplementedError(ExecutionError):
    def __init__(self, detail: str = "Autonomous execution is not enabled yet.") -> None:
        super().__init__(detail, status_code=501)
