import json
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from time import perf_counter
from typing import Protocol
from uuid import uuid4

import anyio.to_thread
from fastapi import Depends, FastAPI, HTTPException, Request
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
        request.state.principal_resolution_ms = None
        request.state.memory_query_ms = None
        start = perf_counter()
        response: Response
        try:
            blocked = False
            if (
                isinstance(db, Database)
                and request.url.path != "/health/live"
                and not request.url.path.startswith("/static/")
            ):
                try:
                    blocked = await anyio.to_thread.run_sync(db.recovery_blocked)
                except SQLAlchemyError:
                    blocked = True
            if blocked:
                if "text/html" in request.headers.get("accept", ""):
                    response = templates.TemplateResponse(
                        request=request,
                        name="error.html",
                        context={
                            "shell": {"signed_in": False},
                            "title": "Service unavailable",
                            "message": "Database recovery is in progress. Try again later.",
                        },
                        status_code=503,
                    )
                else:
                    response = JSONResponse(
                        {
                            "detail": "Database recovery is blocked",
                            "request_id": request.state.request_id,
                        },
                        status_code=503,
                    )
            else:
                response = await call_next(request)
        except Exception:
            if "text/html" in request.headers.get("accept", ""):
                response = templates.TemplateResponse(
                    request=request,
                    name="error.html",
                    context={
                        "shell": {"signed_in": False},
                        "title": "Something went wrong",
                        "message": "The request could not be completed. Return home and try again.",
                    },
                    status_code=500,
                )
            else:
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
                    "principal_resolution_ms": request.state.principal_resolution_ms,
                    "memory_query_ms": request.state.memory_query_ms,
                    "database_timeout_category": request.state.db_timeout_category,
                }
            )
        )
        return response

    @app.exception_handler(SQLAlchemyError)
    async def database_failure(request: Request, exc: SQLAlchemyError) -> Response:
        request.state.db_timeout_category = timeout_category(exc)
        if "text/html" in request.headers.get("accept", ""):
            return templates.TemplateResponse(
                request=request,
                name="error.html",
                context={
                    "shell": {"signed_in": False},
                    "title": "Service temporarily unavailable",
                    "message": (
                        "The database did not respond. Your browser input has not "
                        "been confirmed as saved."
                    ),
                },
                status_code=503,
                headers={"Retry-After": "2"},
            )
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
        shell: dict[str, object] = {"signed_in": False}
        if isinstance(db, Database):
            from living_memory.web import shell_context

            shell = shell_context(request, db, settings)
        return templates.TemplateResponse(
            request=request,
            name="home.html",
            context={
                "development": settings.environment == "development",
                "message": pop_flash(request),
                "shell": shell,
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

    if isinstance(db, Database):
        from living_memory.web import (
            AccessChangedError,
            access_changed_response,
            auth_admin_router,
            shell_context,
        )

        @app.exception_handler(AccessChangedError)
        async def access_changed(request: Request, exc: AccessChangedError) -> HTMLResponse:
            del exc
            return access_changed_response(
                request,
                templates=templates,
                shell=shell_context(request, db, settings),
            )

        @app.exception_handler(HTTPException)
        async def browser_error(request: Request, exc: HTTPException) -> Response:
            if "text/html" not in request.headers.get("accept", ""):
                return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
            title = "Page not found" if exc.status_code == 404 else "Access unavailable"
            message = (
                "This page does not exist or is not available with your current access."
                if exc.status_code in {401, 403, 404}
                else str(exc.detail)
            )
            return templates.TemplateResponse(
                request=request,
                name="error.html",
                context={
                    "shell": shell_context(request, db, settings),
                    "title": title,
                    "message": message,
                },
                status_code=exc.status_code,
                headers={"Cache-Control": "no-store"},
            )

        app.include_router(auth_admin_router(db, templates, settings))
        from living_memory.workspace_web import workspace_router

        app.include_router(workspace_router(db, templates, settings))

    if settings.environment == "development":
        from living_memory.explorer import explorer_router

        if isinstance(db, Database):
            app.include_router(
                explorer_router(db, templates, settings.session_secret.get_secret_value().encode())
            )

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
