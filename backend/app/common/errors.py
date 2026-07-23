from typing import Any


class AppError(Exception):
    def __init__(self, status_code: int, code: str, message: str, details: Any = None) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details
        super().__init__(message)


def unauthorized(message: str = "Authentication required", code: str = "unauthorized") -> AppError:
    return AppError(401, code, message)


def forbidden(message: str = "Not permitted", code: str = "forbidden") -> AppError:
    return AppError(403, code, message)


def not_found(message: str = "Not found", code: str = "not_found") -> AppError:
    return AppError(404, code, message)


def conflict(message: str = "Conflict", code: str = "conflict", details: Any = None) -> AppError:
    return AppError(409, code, message, details)


def bad_request(
    message: str = "Bad request", code: str = "bad_request", details: Any = None
) -> AppError:
    return AppError(400, code, message, details)


def too_many_requests(
    message: str = "Too many requests", code: str = "too_many_requests"
) -> AppError:
    return AppError(429, code, message)
