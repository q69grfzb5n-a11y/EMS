from collections.abc import Sequence
from typing import Any

from fastapi import APIRouter, FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.common.errors import AppError
from app.core.logging import RequestLoggingMiddleware, configure_logging
from app.db.session import SessionLocal
from app.modules.approvals.router import router as approvals_router
from app.modules.attendance.router import router as attendance_router
from app.modules.audit.router import router as audit_router
from app.modules.auth.router import router as auth_router
from app.modules.employees.router import router as employees_router
from app.modules.evaluations.router import evaluations_router
from app.modules.incentives.router import router as incentives_router
from app.modules.kpi_templates.router import positions_router as kpi_positions_router
from app.modules.kpi_templates.router import router as kpi_templates_router
from app.modules.org.router import router as org_router
from app.modules.reports.router import router as reports_router
from app.modules.transfers.router import router as transfers_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_router)
api_router.include_router(org_router)
api_router.include_router(employees_router)
api_router.include_router(kpi_templates_router)
api_router.include_router(kpi_positions_router)
api_router.include_router(attendance_router)
api_router.include_router(evaluations_router)
api_router.include_router(transfers_router)
api_router.include_router(incentives_router)
api_router.include_router(reports_router)
api_router.include_router(approvals_router)
api_router.include_router(audit_router)


def _sanitize_errors(errors: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """pydantic's ValidationError.errors() embeds the raw exception instance under
    ctx.error for @model_validator(mode="after") failures — not JSON-serializable
    as-is, so it must be stringified before the response is rendered."""
    sanitized = []
    for err in errors:
        err = dict(err)
        ctx = err.get("ctx")
        if isinstance(ctx, dict) and "error" in ctx:
            err["ctx"] = {**ctx, "error": str(ctx["error"])}
        sanitized.append(err)
    return sanitized


_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
}


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(title="EMS API")
    app.add_middleware(RequestLoggingMiddleware)

    @app.middleware("http")
    async def add_security_headers(request: Request, call_next: Any) -> Any:
        response = await call_next(request)
        for name, value in _SECURITY_HEADERS.items():
            response.headers[name] = value
        # nginx terminates TLS and forwards this header; only advertise HSTS
        # over a connection that was actually HTTPS end-to-end.
        if request.headers.get("x-forwarded-proto") == "https":
            response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
        return response

    app.include_router(api_router)

    @app.exception_handler(AppError)
    def handle_app_error(_request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message, "details": exc.details}},
        )

    @app.exception_handler(RequestValidationError)
    def handle_validation_error(_request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "validation_error",
                    "message": "Request validation failed",
                    "details": jsonable_encoder(_sanitize_errors(exc.errors())),
                }
            },
        )

    @app.get("/health")
    def health() -> dict[str, str]:
        db_status = "connected"
        try:
            with SessionLocal() as session:
                session.execute(text("SELECT 1"))
        except Exception:
            db_status = "unavailable"
        return {"status": "ok", "db": db_status}

    return app


app = create_app()
