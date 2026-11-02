"""FastAPI service. Run from the backend folder:

    uvicorn api.main:app --port 8001 --reload

Django's ORM is initialised first so FastAPI uses the SAME models and database
as Django. Only Django runs migrations; FastAPI never creates or alters tables.
"""
import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.db import connection  # noqa: E402
from fastapi import APIRouter, FastAPI, Request  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from api.core.config import get_settings  # noqa: E402
from api.core.db import DBRoute  # noqa: E402
from api.core.errors import ApiError, register_exception_handlers  # noqa: E402
from api.routers import attendance, auth, dashboard, employees, fees, reports, rooms, students  # noqa: E402

settings = get_settings()

app = FastAPI(
    title="Hostel Management API",
    version="1.0.0",
    description=(
        "REST API for the Hostel Management System.\n\n"
        "**Authentication:** browsers sign in with `POST /api/v1/auth/login` (HttpOnly cookies). "
        "To try endpoints here, click **Authorize** and sign in with your email as the *username* "
        "(uses `POST /api/v1/auth/token`, available in development only).\n\n"
        "Every error uses the shape `{\"error\": {\"code\", \"message\", \"details\"}}`."
    ),
)
register_exception_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-CSRF-Token", "Authorization"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "same-origin")
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


health_router = APIRouter(route_class=DBRoute, tags=["Health"])


@health_router.get("/health", summary="Service and database health check")
def health():
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception:
        raise ApiError(503, "database_unavailable", "The database is not reachable.")
    return {"status": "ok", "database": "up"}


app.include_router(health_router)
for module in (auth, dashboard, students, rooms, fees, attendance, employees, reports):
    app.include_router(module.router, prefix="/api/v1")
