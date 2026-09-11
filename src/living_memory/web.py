"""Authentication and administration browser routes."""

from __future__ import annotations

from datetime import datetime, timedelta
from time import perf_counter
from typing import Annotated, Any
from uuid import UUID

import anyio
from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.routing import APIRoute
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from living_memory.admin_access import (
    delete_membership,
    review_access,
    set_membership,
    set_role,
)
from living_memory.administration import (
    AdminGame,
    AdministrationConflict,
    ConfigurationRevision,
    ScenarioConfiguration,
    TeamOperationalState,
    activate_game,
    configuration_at,
    create_game,
    ensure_compatible,
    revise_game,
    scheduled_configurations,
)
from living_memory.config import Settings
from living_memory.db import Database
from living_memory.forms import csrf_token
from living_memory.identity import (
    AdministratorAlert,
    AuthSession,
    ExternalIdentityBinding,
    GameRole,
    PendingAccessRequest,
    ProviderScope,
    SessionPolicy,
    TeamMembership,
    User,
    authenticate_local,
    create_local_user,
    deactivate_user,
    is_game_admin,
    is_system_admin,
    resolve_principal,
    resolve_session,
    rotate_session,
)

AUTH_COOKIE = "lm_auth"
ADMIN_DUPLICATE_CONSTRAINTS = {
    "uq_auth_user_username",
    "pk_admin_game",
    "pk_auth_team_membership",
    "pk_auth_game_role",
    "uq_auth_provider_scope_game_id",
    "uq_admin_configuration_revision_game_id",
}


class AccessChangedError(Exception):
    pass


def _policy(settings: Settings) -> SessionPolicy:
    return SessionPolicy(
        idle=timedelta(minutes=settings.session_idle_minutes),
        absolute=timedelta(days=settings.session_absolute_days),
    )


def _source(request: Request) -> str:
    # Forwarded headers are deliberately ignored until a trusted proxy topology is configured.
    return request.client.host if request.client else "unknown"


def _current_user(request: Request, db: Database, settings: Settings) -> User | None:
    started = perf_counter()
    token = request.cookies.get(AUTH_COOKIE)
    if not token:
        request.state.principal_resolution_ms = round((perf_counter() - started) * 1000, 3)
        return None
    with db.transaction() as db_session:
        user = resolve_session(db_session, token, request.app.state.clock.now(), _policy(settings))
    request.state.principal_resolution_ms = round((perf_counter() - started) * 1000, 3)
    return user


def access_changed_response(request: Request, status: int = 403) -> HTMLResponse:
    headers = {"Cache-Control": "no-store"}
    if request.headers.get("hx-request", "").lower() == "true":
        headers.update({"HX-Retarget": "body", "HX-Reswap": "innerHTML"})
    return HTMLResponse(
        "<!doctype html><html lang='en'><head><title>Access changed</title></head>"
        "<body><main><h1>Your access changed</h1>"
        "<p>Your account is still signed in, but this action is no longer available. "
        "Reload the workspace or contact an administrator.</p></main></body></html>",
        status_code=status,
        headers=headers,
    )


def auth_admin_router(db: Database, templates: Jinja2Templates, settings: Settings) -> APIRouter:
    class AdminRoute(APIRoute):
        def get_route_handler(self) -> Any:
            original = super().get_route_handler()

            async def handler(request: Request) -> Response:
                if not request.url.path.startswith("/admin/") or request.method != "POST":
                    return await original(request)
                try:
                    return await original(request)
                except PermissionError:
                    return access_changed_response(request)
                except LookupError:
                    raise HTTPException(404, "Not found") from None
                except (ValueError, RequestValidationError, IntegrityError, HTTPException) as exc:
                    status = 422
                    if isinstance(exc, HTTPException):
                        if exc.status_code not in {409, 422}:
                            raise
                        status, message = exc.status_code, str(exc.detail)
                    elif isinstance(exc, IntegrityError):
                        diag = getattr(exc.orig, "diag", None)
                        name = getattr(diag, "constraint_name", "") or ""
                        if (
                            getattr(exc.orig, "sqlstate", None) != "23505"
                            or name not in ADMIN_DUPLICATE_CONSTRAINTS
                        ):
                            raise
                        status, message = 409, "This identifier or assignment already exists."
                    elif isinstance(exc, (ValidationError, RequestValidationError)):
                        message = "; ".join(
                            f"{'.'.join(map(str, item['loc']))}: {item['msg']}"
                            for item in exc.errors()
                        )
                    else:
                        status = 409 if isinstance(exc, AdministrationConflict) else 422
                        message = str(exc)
                    form = await request.form()
                    values = {
                        key: str(value)
                        for key, value in form.items()
                        if key not in {"password", "csrf_token"}
                    }
                    return await anyio.to_thread.run_sync(
                        lambda: admin(
                            request,
                            status=status,
                            error=message,
                            values=values,
                            form_action=request.url.path,
                        )
                    )

            return handler

    router = APIRouter(route_class=AdminRoute)

    @router.get("/login", response_class=HTMLResponse)
    def login_form(request: Request) -> Response:
        if _current_user(request, db, settings):
            return RedirectResponse("/", status_code=303)
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"csrf": csrf_token(request), "error": None, "username": ""},
            headers={"Cache-Control": "no-store"},
        )

    @router.post("/login", response_class=HTMLResponse)
    def login(request: Request, username: str = Form(), password: str = Form()) -> Response:
        now = request.app.state.clock.now()
        with db.transaction() as db_session:
            try:
                user = authenticate_local(
                    db_session,
                    username,
                    password,
                    _source(request),
                    now,
                    username_limit=settings.login_username_limit,
                    source_limit=settings.login_source_limit,
                    window=timedelta(minutes=settings.login_window_minutes),
                )
            except PermissionError:
                user = None
            if user is not None:
                token = rotate_session(
                    db_session,
                    request.cookies.get(AUTH_COOKIE),
                    user.id,
                    now,
                    _policy(settings),
                )
        if user is None:
            return templates.TemplateResponse(
                request=request,
                name="login.html",
                context={
                    "csrf": csrf_token(request),
                    "error": "Invalid username or password.",
                    "username": username,
                },
                status_code=401,
                headers={"Cache-Control": "no-store"},
            )
        response = RedirectResponse("/", status_code=303)
        response.set_cookie(
            AUTH_COOKIE,
            token,
            max_age=settings.session_absolute_days * 86400,
            httponly=True,
            secure=settings.secure_cookies,
            samesite="lax",
            path="/",
        )
        return response

    @router.post("/logout")
    def logout(request: Request) -> Response:
        token = request.cookies.get(AUTH_COOKIE)
        if token:
            now = request.app.state.clock.now()
            with db.transaction() as db_session:
                row = db_session.scalars(
                    select(AuthSession).where(AuthSession.token_hash == __token_hash(token))
                ).one_or_none()
                if row and row.revoked_at is None:
                    row.revoked_at, row.revocation_reason = now, "logout"
        response = RedirectResponse("/login", status_code=303)
        response.delete_cookie(AUTH_COOKIE, path="/", httponly=True, samesite="lax")
        return response

    def admin(
        request: Request,
        *,
        status: int = 200,
        error: str = "",
        values: dict[str, str] | None = None,
        form_action: str = "",
    ) -> Response:
        user = _current_user(request, db, settings)
        if user is None:
            return RedirectResponse("/login", status_code=303)
        with db.transaction() as db_session:
            system = is_system_admin(db_session, user.id)
            game_ids = set(
                db_session.scalars(
                    select(GameRole.game_id).where(
                        GameRole.user_id == user.id, GameRole.role == "game_admin"
                    )
                )
            )
            if not system and not game_ids:
                return access_changed_response(request)
            game_query = select(AdminGame).order_by(AdminGame.id)
            if not system:
                game_query = game_query.where(AdminGame.id.in_(game_ids))
            games = tuple(
                {
                    "id": game.id,
                    "title": game.title,
                    "status": game.status,
                    "current_turn": game.current_turn,
                }
                for game in db_session.scalars(game_query)
            )
            pending_query = (
                select(
                    PendingAccessRequest.id,
                    PendingAccessRequest.game_id,
                    PendingAccessRequest.display_attributes,
                    PendingAccessRequest.observed_groups,
                )
                .where(PendingAccessRequest.status == "pending")
                .order_by(PendingAccessRequest.created_at)
            )
            if not system:
                pending_query = pending_query.where(PendingAccessRequest.game_id.in_(game_ids))
            pending = tuple(db_session.execute(pending_query).all())
            user_query = select(User.id, User.username, User.active, User.pending)
            if not system:
                participants = (
                    select(TeamMembership.user_id)
                    .where(TeamMembership.game_id.in_(game_ids))
                    .union(
                        select(GameRole.user_id).where(GameRole.game_id.in_(game_ids)),
                        select(ExternalIdentityBinding.user_id)
                        .join(PendingAccessRequest)
                        .where(PendingAccessRequest.game_id.in_(game_ids)),
                    )
                )
                user_query = user_query.where(User.id.in_(participants))
            users = tuple(db_session.execute(user_query).all())
            alert_query = select(AdministratorAlert).where(
                AdministratorAlert.recipient_user_id == user.id
            )
            if not system:
                alert_query = alert_query.where(AdministratorAlert.game_id.in_(game_ids))

            def alert_link(row: AdministratorAlert) -> str | None:
                if not row.game_id or row.subject_id == "None":
                    return None
                if row.kind == "team_blocked":
                    target = db_session.get(TeamOperationalState, (row.game_id, row.subject_id))
                    return f"/admin/games/{row.game_id}" if target else None
                if row.kind == "pending_access":
                    try:
                        pending_id = UUID(row.subject_id)
                    except ValueError:
                        return None
                    item = db_session.get(PendingAccessRequest, pending_id)
                    if item and item.game_id == row.game_id:
                        return f"/admin#pending-{pending_id}"
                return None

            alert_rows = tuple(
                {
                    "id": row.id,
                    "game_id": row.game_id,
                    "kind": row.kind,
                    "subject_id": row.subject_id,
                    "read_at": row.read_at,
                    "link": alert_link(row),
                }
                for row in db_session.scalars(
                    alert_query.order_by(AdministratorAlert.created_at.desc())
                )
            )
            scope_query = select(
                ProviderScope.id, ProviderScope.game_id, ProviderScope.provider
            ).order_by(ProviderScope.game_id, ProviderScope.provider)
            if not system:
                scope_query = scope_query.where(ProviderScope.game_id.in_(game_ids))
            scopes = tuple(db_session.execute(scope_query).all())
        return templates.TemplateResponse(
            request=request,
            name="admin.html",
            status_code=status,
            context={
                "csrf": csrf_token(request),
                "display_name": user.display_name,
                "games": games,
                "alerts": sum(row["read_at"] is None for row in alert_rows),
                "pending": pending,
                "users": users,
                "scopes": scopes,
                "system": system,
                "alert_rows": alert_rows,
                "error": error,
                "values": values or {},
                "form_action": form_action,
            },
            headers={"Cache-Control": "no-store"},
        )

    @router.get("/admin", response_class=HTMLResponse)
    def admin_page(request: Request) -> Response:
        return admin(request)

    @router.get("/admin/games/{game_id}", response_class=HTMLResponse)
    def game_detail(request: Request, game_id: str) -> Response:
        actor = _current_user(request, db, settings)
        if actor is None:
            raise HTTPException(401, "Authentication required")
        with db.transaction() as session:
            if not is_game_admin(session, actor.id, game_id):
                raise AccessChangedError
            game = session.get(AdminGame, game_id)
            if game is None:
                raise HTTPException(404, "Not found")
            now = request.app.state.clock.now()
            current = configuration_at(session, game_id, now, max(1, game.current_turn))
            problem = ""
            try:
                ensure_compatible(session, game, now)
            except ValueError as exc:
                problem = str(exc)
            history = tuple(
                {
                    "id": row.id,
                    "sequence": row.sequence,
                    "recorded_at": row.recorded_at,
                    "effective_turn": row.effective_turn,
                    "configuration": row.configuration,
                }
                for row in session.scalars(
                    select(ConfigurationRevision)
                    .where(ConfigurationRevision.game_id == game_id)
                    .order_by(ConfigurationRevision.sequence.desc())
                )
            )
            members = tuple(
                session.execute(
                    select(
                        TeamMembership.user_id,
                        User.username,
                        TeamMembership.team_id,
                        TeamMembership.authority,
                    )
                    .join(User, User.id == TeamMembership.user_id)
                    .where(TeamMembership.game_id == game_id)
                ).all()
            )
            roles = tuple(
                session.execute(
                    select(
                        GameRole.user_id,
                        User.username,
                        GameRole.role,
                        GameRole.granted_by,
                        GameRole.granted_at,
                    )
                    .join(User, User.id == GameRole.user_id)
                    .where(GameRole.game_id == game_id)
                ).all()
            )
            states = tuple(
                {"team_id": row.team_id, "blocked": row.blocked, "reason": row.reason}
                for row in session.scalars(
                    select(TeamOperationalState).where(TeamOperationalState.game_id == game_id)
                )
            )
            context = {
                "csrf": csrf_token(request),
                "game_id": game.id,
                "title": game.title,
                "status": game.status,
                "turn": game.current_turn,
                "current": current.configuration,
                "source_revision": current.sequence,
                "history": history,
                "members": members,
                "roles": roles,
                "states": states,
                "scheduled": tuple(
                    row.sequence
                    for row in scheduled_configurations(
                        session, game_id, now, max(1, game.current_turn)
                    )
                ),
                "problem": problem,
                "system": is_system_admin(session, actor.id),
            }
        return templates.TemplateResponse(
            request=request,
            name="admin_game.html",
            context=context,
            headers={"Cache-Control": "no-store"},
        )

    @router.post("/admin/alerts/{alert_id}/read")
    def read_alert(request: Request, alert_id: UUID) -> Response:
        actor = _current_user(request, db, settings)
        if actor is None:
            raise HTTPException(401, "Authentication required")
        with db.transaction() as session:
            row = session.get(AdministratorAlert, alert_id, with_for_update=True)
            if (
                row is None
                or row.recipient_user_id != actor.id
                or (row.game_id and not is_game_admin(session, actor.id, row.game_id))
            ):
                raise HTTPException(404, "Not found")
            if row.read_at is None:
                row.read_at = request.app.state.clock.now()
        return RedirectResponse("/admin", status_code=303)

    def require_system(request: Request) -> User:
        user = _current_user(request, db, settings)
        if user is None:
            raise HTTPException(401, "Authentication required")
        with db.transaction() as db_session:
            if not is_system_admin(db_session, user.id):
                raise AccessChangedError
        return user

    @router.post("/admin/users")
    def add_user(
        request: Request,
        username: str = Form(),
        display_name: str = Form(),
        password: str = Form(),
    ) -> Response:
        actor = require_system(request)
        with db.transaction() as db_session:
            create_local_user(
                db_session,
                username,
                display_name,
                password,
                request.app.state.clock.now(),
                author=actor.id,
            )
        del actor
        return RedirectResponse("/admin", status_code=303)

    @router.post("/admin/users/{user_id}/deactivate")
    def disable_user(request: Request, user_id: UUID) -> Response:
        actor = require_system(request)
        if actor.id == user_id:
            raise HTTPException(409, "A system administrator cannot deactivate this session")
        # Capture wall time once: retries are a concurrency implementation
        # detail, not distinct administrative events.
        now = request.app.state.clock.now()
        from living_memory.db import run_retryable
        from living_memory.team_authority import RetryableConflict

        try:

            def operation() -> None:
                with db.transaction() as db_session:
                    deactivate_user(db_session, user_id, now, actor.id)

            run_retryable(operation)
        except LookupError:
            raise HTTPException(404, "Not found") from None
        except RetryableConflict:
            raise HTTPException(409, "Try again") from None
        return RedirectResponse("/admin", status_code=303)

    @router.post("/admin/games")
    def add_game(
        request: Request,
        game_id: str = Form(),
        title: str = Form(),
        configuration: str = Form(),
        description: str = Form(default=""),
        public_rules: str = Form(default=""),
        public_briefing: str = Form(default=""),
    ) -> Response:
        actor = require_system(request)
        parsed = ScenarioConfiguration.model_validate_json(configuration)
        with db.transaction() as db_session:
            create_game(
                db_session,
                game_id,
                title,
                parsed,
                actor.id,
                request.app.state.clock.now(),
                description=description,
                public_rules=public_rules,
                public_briefing=public_briefing,
            )
        return RedirectResponse("/admin", status_code=303)

    @router.post("/admin/games/{game_id}/activate")
    def activate(request: Request, game_id: str) -> Response:
        actor = _current_user(request, db, settings)
        if actor is None:
            raise HTTPException(401, "Authentication required")
        with db.transaction() as db_session:
            if not is_game_admin(db_session, actor.id, game_id):
                raise AccessChangedError
            game = db_session.get(AdminGame, game_id)
            if game is None:
                raise HTTPException(404, "Not found")
            activate_game(db_session, game, actor.id, request.app.state.clock.now())
        return RedirectResponse("/admin", status_code=303)

    @router.post("/admin/games/{game_id}/revisions")
    def add_revision(
        request: Request,
        game_id: str,
        effective_turn: int = Form(),
        configuration: str = Form(),
    ) -> Response:
        actor = _current_user(request, db, settings)
        if actor is None:
            raise HTTPException(401, "Authentication required")
        with db.transaction() as db_session:
            if not is_game_admin(db_session, actor.id, game_id):
                raise AccessChangedError
            game = db_session.get(AdminGame, game_id)
            if game is None:
                raise HTTPException(404, "Not found")
            revise_game(
                db_session,
                game,
                ScenarioConfiguration.model_validate_json(configuration),
                effective_turn,
                actor.id,
                request.app.state.clock.now(),
            )
        return RedirectResponse("/admin", status_code=303)

    def signed_in(request: Request) -> User:
        actor = _current_user(request, db, settings)
        if actor is None:
            raise HTTPException(401, "Authentication required")
        return actor

    @router.post("/admin/memberships")
    def add_membership(
        request: Request,
        user_id: Annotated[UUID, Form()],
        game_id: str = Form(),
        team_id: str = Form(),
        authority: str = Form(),
    ) -> Response:
        actor = signed_in(request)
        with db.transaction() as session:
            set_membership(
                session,
                actor.id,
                game_id,
                user_id,
                team_id,
                authority,
                request.app.state.clock.now(),
            )
        return RedirectResponse("/admin", status_code=303)

    @router.post("/admin/games/{game_id}/memberships/{user_id}/{team_id}/change")
    def change_membership(
        request: Request, game_id: str, user_id: UUID, team_id: str, authority: str = Form()
    ) -> Response:
        actor = signed_in(request)
        with db.transaction() as session:
            set_membership(
                session,
                actor.id,
                game_id,
                user_id,
                team_id,
                authority,
                request.app.state.clock.now(),
                change=True,
            )
        return RedirectResponse(f"/admin/games/{game_id}", status_code=303)

    @router.post("/admin/games/{game_id}/memberships/{user_id}/{team_id}/remove")
    def remove_team_member(request: Request, game_id: str, user_id: UUID, team_id: str) -> Response:
        actor = signed_in(request)
        with db.transaction() as session:
            delete_membership(
                session, actor.id, game_id, user_id, team_id, request.app.state.clock.now()
            )
        return RedirectResponse(f"/admin/games/{game_id}", status_code=303)

    @router.post("/admin/roles")
    def add_role(
        request: Request,
        user_id: Annotated[UUID, Form()],
        game_id: str = Form(),
        role: str = Form(),
    ) -> Response:
        actor = signed_in(request)
        with db.transaction() as session:
            set_role(session, actor.id, game_id, user_id, role, request.app.state.clock.now())
        return RedirectResponse("/admin", status_code=303)

    @router.post("/admin/games/{game_id}/roles/{user_id}/{role}/remove")
    def remove_role(request: Request, game_id: str, user_id: UUID, role: str) -> Response:
        actor = signed_in(request)
        with db.transaction() as session:
            set_role(
                session,
                actor.id,
                game_id,
                user_id,
                role,
                request.app.state.clock.now(),
                remove=True,
            )
        return RedirectResponse(f"/admin/games/{game_id}", status_code=303)

    @router.post("/admin/external/{request_id}/approve")
    def approve_external(
        request: Request,
        request_id: UUID,
        team_id: str = Form(default=""),
        authority: str = Form(default="member"),
        role: str = Form(default=""),
    ) -> Response:
        actor = signed_in(request)
        with db.transaction() as session:
            review_access(
                session,
                actor.id,
                request_id,
                True,
                request.app.state.clock.now(),
                team_id=team_id,
                authority=authority,
                role=role,
            )
        return RedirectResponse("/admin", status_code=303)

    @router.post("/admin/external/{request_id}/deny")
    def deny_external(request: Request, request_id: UUID) -> Response:
        actor = signed_in(request)
        with db.transaction() as session:
            review_access(session, actor.id, request_id, False, request.app.state.clock.now())
        return RedirectResponse("/admin", status_code=303)

    @router.post("/admin/provider-scopes")
    def add_provider_scope(
        request: Request, game_id: str = Form(), provider: str = Form()
    ) -> Response:
        actor = require_system(request)
        del actor
        with db.transaction() as db_session:
            if db_session.get(AdminGame, game_id) is None:
                raise HTTPException(404, "Not found")
            db_session.add(
                ProviderScope(
                    game_id=game_id,
                    provider=provider,
                    created_at=request.app.state.clock.now(),
                )
            )
        return RedirectResponse("/admin", status_code=303)

    @router.get("/games/{game_id}/public")
    def public_game(request: Request, game_id: str) -> Response:
        user = _current_user(request, db, settings)
        if user is None:
            raise HTTPException(401, "Authentication required")
        with db.transaction() as db_session:
            if user.pending:
                associated = db_session.scalar(
                    select(func.count())
                    .select_from(ExternalIdentityBinding)
                    .join(
                        ProviderScope,
                        ProviderScope.id == ExternalIdentityBinding.provider_scope_id,
                    )
                    .where(
                        ExternalIdentityBinding.user_id == user.id,
                        ProviderScope.game_id == game_id,
                    )
                )
                if not associated:
                    raise HTTPException(404, "Not found")
            game = db_session.get(AdminGame, game_id)
            if game is None:
                raise HTTPException(404, "Not found")
            return JSONResponse(
                {
                    "id": game.id,
                    "title": game.title,
                    "description": game.description,
                    "rules": game.public_rules,
                    "briefing": game.public_briefing,
                },
                headers={"Cache-Control": "no-store"},
            )

    @router.get("/memory")
    def authenticated_memory(
        request: Request,
        game_id: str,
        scope_id: str,
        known_at: datetime,
        effective_microseconds: int,
        dataset_id: UUID | None = None,
        record_id: str | None = None,
        search: str | None = None,
        cursor: str | None = None,
    ) -> Response:
        from living_memory.clocks import GameTime
        from living_memory.memory import BranchLineage, Dataset, MemoryQuery, MemoryReader

        user = _current_user(request, db, settings)
        if user is None:
            return access_changed_response(request, 401)
        started = perf_counter()
        with db.transaction() as db_session:
            principal = resolve_principal(db_session, user, game_id, request.app.state.clock.now())
            dataset = (
                db_session.get(Dataset, dataset_id)
                if dataset_id is not None
                else db_session.scalars(
                    select(Dataset).where(
                        Dataset.admin_game_id == game_id,
                        Dataset.source_kind == "operational",
                    )
                ).one_or_none()
            )
            if (
                dataset is None
                or dataset.game_id != game_id
                or not principal.permits(game_id, scope_id)
            ):
                raise HTTPException(404, "Not found")
            root = dataset.root_branch_id
        request.state.principal_resolution_ms = round(
            request.state.principal_resolution_ms + (perf_counter() - started) * 1000, 3
        )
        query_started = perf_counter()
        try:
            view = MemoryReader(
                db, settings.session_secret.get_secret_value().encode()
            ).read_memory(
                principal,
                game_id,
                scope_id,
                BranchLineage(root=root),
                known_at,
                GameTime(elapsed_microseconds=effective_microseconds),
                MemoryQuery(
                    dataset_id=dataset.id,
                    record_id=record_id,
                    text=search,
                    cursor=cursor,
                ),
            )
        except (LookupError, PermissionError):
            raise HTTPException(404, "Not found") from None
        except ValueError:
            if cursor:
                return access_changed_response(request)
            raise
        finally:
            request.state.memory_query_ms = round((perf_counter() - query_started) * 1000, 3)
        return JSONResponse(view.model_dump(mode="json"), headers={"Cache-Control": "no-store"})

    @router.get("/play", response_class=HTMLResponse)
    def play_workspace(request: Request, game_id: str) -> Response:
        """Team-scoped workspace entry point (works without HTMX as well)."""
        user = _current_user(request, db, settings)
        if user is None:
            return access_changed_response(request, 401)
        with db.transaction() as session:
            game = session.get(AdminGame, game_id)
            principal = resolve_principal(session, user, game_id, request.app.state.clock.now())
            teams = [
                grant.visibility_scope_id
                for grant in principal.grants
                if grant.visibility_scope_id != "adjudicator"
            ]
        if game is None or not teams:
            raise HTTPException(404, "Not found")
        return templates.TemplateResponse(
            request=request,
            name="play.html",
            context={"game": game, "teams": teams, "csrf": csrf_token(request)},
            headers={"Cache-Control": "no-store"},
        )

    @router.get("/adjudicate", response_class=HTMLResponse)
    def adjudicate_workspace(request: Request, game_id: str) -> Response:
        user = _current_user(request, db, settings)
        if user is None:
            return access_changed_response(request, 401)
        with db.transaction() as session:
            game = session.get(AdminGame, game_id)
            principal = resolve_principal(session, user, game_id, request.app.state.clock.now())
        if game is None or not principal.permits(game_id, "adjudicator"):
            raise HTTPException(404, "Not found")
        return templates.TemplateResponse(
            request=request,
            name="adjudicate.html",
            context={"game": game, "csrf": csrf_token(request)},
            headers={"Cache-Control": "no-store"},
        )

    return router


def __token_hash(token: str) -> bytes:
    import hashlib

    return hashlib.sha256(token.encode()).digest()
