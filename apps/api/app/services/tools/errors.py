"""Safe tool execution errors."""

from __future__ import annotations

from app.schemas.tool import ToolErrorCode


class ToolError(Exception):
    """Base tool layer error with safe client-facing fields."""

    def __init__(
        self,
        error_code: ToolErrorCode,
        message: str,
        *,
        status_code: int = 400,
    ) -> None:
        self.error_code = error_code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class ToolNotFoundError(ToolError):
    def __init__(self, qualified_name: str) -> None:
        super().__init__(
            ToolErrorCode.TOOL_NOT_FOUND,
            "Tool not found.",
            status_code=404,
        )
        self.qualified_name = qualified_name


class ToolDisabledError(ToolError):
    def __init__(self, qualified_name: str) -> None:
        super().__init__(
            ToolErrorCode.TOOL_DISABLED,
            "Tool is disabled.",
            status_code=403,
        )
        self.qualified_name = qualified_name


class ToolUnauthorizedError(ToolError):
    def __init__(self) -> None:
        super().__init__(
            ToolErrorCode.TOOL_UNAUTHORIZED,
            "Tool execution is not authorized.",
            status_code=403,
        )


class ToolWriteNotAllowedError(ToolError):
    def __init__(self, qualified_name: str) -> None:
        super().__init__(
            ToolErrorCode.TOOL_WRITE_NOT_ALLOWED,
            "Write tools are not permitted.",
            status_code=403,
        )
        self.qualified_name = qualified_name


class ToolInvalidInputError(ToolError):
    def __init__(self, message: str = "Tool input is invalid.") -> None:
        super().__init__(ToolErrorCode.TOOL_INVALID_INPUT, message, status_code=400)


class ToolInvalidOutputError(ToolError):
    def __init__(self) -> None:
        super().__init__(
            ToolErrorCode.TOOL_INVALID_OUTPUT,
            "Tool returned invalid output.",
            status_code=500,
        )


class ToolTimeoutError(ToolError):
    def __init__(self) -> None:
        super().__init__(
            ToolErrorCode.TOOL_TIMEOUT,
            "Tool execution timed out.",
            status_code=504,
        )


class ToolResultTooLargeError(ToolError):
    def __init__(self) -> None:
        super().__init__(
            ToolErrorCode.TOOL_RESULT_TOO_LARGE,
            "Tool result exceeds allowed size.",
            status_code=500,
        )


class ToolExecutionFailedError(ToolError):
    def __init__(self) -> None:
        super().__init__(
            ToolErrorCode.TOOL_EXECUTION_FAILED,
            "Tool execution failed.",
            status_code=500,
        )


class ToolPolicyLimitError(ToolError):
    def __init__(self, message: str) -> None:
        super().__init__(ToolErrorCode.TOOL_POLICY_LIMIT, message, status_code=429)
