"""One consistent error format for every failure:

    {"error": {"code": "forbidden", "message": "...", "details": null}}
"""
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("hostel.api")


class ApiError(Exception):
    def __init__(self, status_code: int, code: str, message: str, details=None, headers: dict | None = None):
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details
        self.headers = headers or {}
        super().__init__(message)


def error_response(status_code: int, code: str, message: str, details=None, headers=None) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message, "details": details}},
        headers=headers,
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def handle_api_error(request: Request, exc: ApiError):
        return error_response(exc.status_code, exc.code, exc.message, exc.details, exc.headers)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError):
        # Never echo the submitted value back: it may be a password.
        details = [
            {"field": ".".join(str(p) for p in err["loc"] if p not in ("body", "query", "path")), "message": err["msg"]}
            for err in exc.errors()
        ]
        return error_response(422, "validation_error", "The request contains invalid data.", details)

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(request: Request, exc: StarletteHTTPException):
        codes = {401: "not_authenticated", 403: "forbidden", 404: "not_found", 405: "method_not_allowed"}
        return error_response(exc.status_code, codes.get(exc.status_code, "http_error"), str(exc.detail))

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception):
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return error_response(500, "server_error", "Something went wrong on the server.")
