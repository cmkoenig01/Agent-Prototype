"""Explicit application outcomes, shared by the CLI and tools."""


class AppError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)
