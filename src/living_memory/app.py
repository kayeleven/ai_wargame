import json
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from time import perf_counter
from typing import Protocol
from uuid import uuid4

import anyio.to_thread
from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.exc import DBAPIError, SQLAlchemyError, TimeoutError
from starlette.middleware.base import RequestResponseEndpoint
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import Response

from living_memory.clocks import Clock, SystemClock
from living_memory.config import Settings, load_settings
from living_memory.db import Database
from living_memory.forms import (
    BoundForm,
    DemoInput,
    bind_form,
    csrf_token,
    flash,
    pop_flash,
    require_csrf,
)

ASSETS = Path(__file__).parent
logger = logging.getLogger("living_memory.requests")
logger.setLevel(logging.INFO)
if not logger.handlers:
    logger.addHandler(logging.StreamHandler())


class DatabaseService(Protocol):
    def ready(self) -> bool: ...
    def close(self) -> None: ...


def timeout_category(exc: SQLAlchemyError) -> str:
    if isinstance(exc, TimeoutError):
        return "pool_checkout"
    if isinstance(exc, DBAPIError):
        if getattr(exc.orig, "sqlstate", None) == "57014":
            return "statement_timeout"
        return "database_unavailable"
    return "database_error"


def create_app(
    settings: Settings | None = None,
    database: DatabaseService | None = None,
    clock: Clock | None = None,
) -> FastAPI:
    settings = settings or load_settings()
    db = database or Database(settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        limiter = anyio.to_thread.current_default_thread_limiter()
        previous = limiter.total_tokens
        limiter.total_tokens = settings.thread_tokens
        try:
            yield
        finally:
            await anyio.to_thread.run_sync(db.close)
            limiter.total_tokens = previous

    app = FastAPI(title="Living Memory", lifespan=lifespan, dependencies=[Depends(require_csrf)])
    app.state.clock = clock or SystemClock()
    app.state.database = db
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.session_secret.get_secret_value(),
        session_cookie="lm_session",
        same_site="lax",
        https_only=settings.secure_cookies,
    )
    app.mount("/static", StaticFiles(directory=ASSETS / "static"), name="static")
    templates = Jinja2Templates(directory=ASSETS / "templates")

    @app.middleware("http")
    async def diagnostics(request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Never trust client request IDs or log raw URLs/query strings.
        request.state.request_id = uuid4().hex
        request.state.db_timeout_category = None
        start = perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            response = JSONResponse(
                {"detail": "Unexpected error", "request_id": request.state.request_id},
                status_code=500,
            )
        response.headers["X-Request-ID"] = request.state.request_id
        route = request.scope.get("route")
        logger.info(
            json.dumps(
                {
                    "request_id": request.state.request_id,
                    "route": getattr(route, "path", "unmatched"),
                    "status": response.status_code,
                    "elapsed_ms": round((perf_counter() - start) * 1000, 3),
                    "database_timeout_category": request.state.db_timeout_category,
                }
            )
        )
        return response

    @app.exception_handler(SQLAlchemyError)
    async def database_failure(request: Request, exc: SQLAlchemyError) -> JSONResponse:
        request.state.db_timeout_category = timeout_category(exc)
        return JSONResponse(
            {
                "detail": "Database temporarily unavailable. Please retry.",
                "request_id": request.state.request_id,
            },
            status_code=503,
            headers={"Retry-After": "2"},
        )

    @app.get("/", response_class=HTMLResponse)
    def home(request: Request) -> Response:
        return templates.TemplateResponse(
            request=request,
            name="home.html",
            context={
                "development": settings.environment == "development",
                "message": pop_flash(request),
            },
        )

    @app.get("/health/live")
    def live() -> dict[str, str]:
        return {"status": "live"}

    @app.get("/health/ready")
    def ready() -> JSONResponse:
        # All database work, including connection cleanup, stays in this sync scope.
        available = db.ready()
        return JSONResponse(
            {"status": "ready" if available else "schema mismatch"},
            status_code=200 if available else 503,
        )

    if settings.environment == "development":
        from living_memory.explorer import explorer_router

        if isinstance(db, Database):
            app.include_router(explorer_router(db, templates))

        def render_form(request: Request, bound: BoundForm, status: int = 200) -> Response:
            partial = request.headers.get("hx-request", "").lower() == "true"
            return templates.TemplateResponse(
                request=request,
                name="form.html" if partial else "demo.html",
                context={"form": bound, "csrf": csrf_token(request), "message": pop_flash(request)},
                status_code=status,
                headers={"Vary": "HX-Request"},
            )

        @app.get("/dev/forms", response_class=HTMLResponse)
        def demo(request: Request) -> Response:
            return render_form(request, BoundForm())

        @app.post("/dev/forms", response_class=HTMLResponse)
        async def submit_demo(request: Request) -> Response:
            fields = await request.form(max_files=0, max_fields=100, max_part_size=64 * 1024)
            bound = bind_form(DemoInput, fields, {"actions"})
            if bound.valid is None:
                return render_form(request, bound, 422)
            flash(request, "demo_saved")
            if request.headers.get("hx-request", "").lower() == "true":
                return Response(status_code=200, headers={"HX-Redirect": "/dev/forms"})
            return RedirectResponse("/dev/forms", status_code=303)

    return app
