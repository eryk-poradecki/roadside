"""RFC 9457 problem details with a stable `reason` code, for every error."""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

PROBLEM_JSON = "application/problem+json"

_DEFAULT_REASONS = {
    404: "not_found",
    405: "method_not_allowed",
    413: "body_too_large",
}


class AppError(Exception):
    def __init__(
        self,
        status: int,
        reason: str,
        detail: str | None = None,
        errors: list[dict[str, str]] | None = None,
    ) -> None:
        super().__init__(reason)
        self.status = status
        self.reason = reason
        self.detail = detail
        self.errors = errors


class NotFoundError(AppError):
    def __init__(self, what: str = "Resource") -> None:
        super().__init__(404, "not_found", f"{what} not found")


class FieldValidationError(AppError):
    """A 422 found by a service (e.g. an unknown id), shaped like request validation."""

    def __init__(self, field: str, message: str) -> None:
        super().__init__(
            422,
            "validation_error",
            "Invalid request",
            [{"field": field, "message": message}],
        )


def problem(
    status: int,
    reason: str,
    title: str,
    instance: str,
    detail: str | None = None,
    errors: list[dict[str, str]] | None = None,
) -> JSONResponse:
    body: dict[str, Any] = {
        "type": "about:blank",
        "title": title,
        "status": status,
        "detail": detail,
        "instance": instance,
        "reason": reason,
    }
    if errors is not None:
        body["errors"] = errors
    return JSONResponse(body, status_code=status, media_type=PROBLEM_JSON)


def _title(status: int) -> str:
    from http import HTTPStatus

    try:
        return HTTPStatus(status).phrase
    except ValueError:
        return "Error"


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(request: Request, exc: AppError) -> JSONResponse:
        return problem(
            exc.status, exc.reason, _title(exc.status), request.url.path, exc.detail, exc.errors
        )

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = [
            {
                "field": ".".join(str(p) for p in e["loc"][1:]),
                "message": str(e["msg"]).removeprefix("Value error, "),
            }
            for e in exc.errors()
        ]
        return problem(
            422, "validation_error", _title(422), request.url.path, "Invalid request", errors
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        reason = _DEFAULT_REASONS.get(exc.status_code, "http_error")
        response = problem(exc.status_code, reason, _title(exc.status_code), request.url.path)
        response.headers.update(exc.headers or {})
        return response
