"""Authentication and administration browser routes."""

from __future__ import annotations

from datetime import datetime, timedelta
from time import perf_counter
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select

from living_memory.administration import (
    AdminGame,
    ScenarioConfiguration,
    TeamOperationalState,
    activate_game,
    configuration_at,
    create_game,
    revise_game,
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
    ProviderGroupMapping,
    ProviderScope,
    SessionPolicy,
    TeamMembership,
    User,
    audit,
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
    router = APIRouter()

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

    @router.get("/admin", response_class=HTMLResponse)
    def admin(request: Request) -> Response:
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
            alerts = int(
                db_session.scalar(
                    select(func.count())
                    .select_from(AdministratorAlert)
                    .where(
                        AdministratorAlert.recipient_user_id == user.id,
                        AdministratorAlert.read_at.is_(None),
                    )
                )
                or 0
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
            users = tuple(db_session.execute(select(User.id, User.username, User.active)).all())
            scope_query = select(
                ProviderScope.id, ProviderScope.game_id, ProviderScope.provider
            ).order_by(ProviderScope.game_id, ProviderScope.provider)
            if not system:
                scope_query = scope_query.where(ProviderScope.game_id.in_(game_ids))
            scopes = tuple(db_session.execute(scope_query).all())
        return templates.TemplateResponse(
            request=request,
            name="admin.html",
            context={
                "csrf": csrf_token(request),
                "display_name": user.display_name,
                "games": games,
                "alerts": alerts,
                "pending": pending,
                "users": users,
                "scopes": scopes,
                "system": system,
            },
            headers={"Cache-Control": "no-store"},
        )

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
        with db.transaction() as db_session:
            user = db_session.get(User, user_id)
            if user is None:
                raise HTTPException(404, "Not found")
            deactivate_user(db_session, user, request.app.state.clock.now(), actor.id)
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

    @router.post("/admin/memberships")
    def add_membership(
        request: Request,
        user_id: Annotated[UUID, Form()],
        game_id: str = Form(),
        team_id: str = Form(),
        authority: str = Form(),
    ) -> Response:
        actor = _current_user(request, db, settings)
        if actor is None:
            raise HTTPException(401, "Authentication required")
        if authority not in {"member", "submitter"}:
            raise HTTPException(422, "Invalid authority")
        with db.transaction() as db_session:
            if not is_game_admin(db_session, actor.id, game_id):
                raise AccessChangedError
            game = db_session.get(AdminGame, game_id)
            target = db_session.get(User, user_id)
            if game is None or target is None or not target.active or target.pending:
                raise HTTPException(422, "User or game is not eligible")
            configured = ScenarioConfiguration.model_validate(
                configuration_at(
                    db_session,
                    game_id,
                    request.app.state.clock.now(),
                    max(1, game.current_turn),
                ).configuration
            )
            if team_id not in {team.id for team in configured.teams}:
                raise HTTPException(422, "Unknown configured team")
            db_session.add(
                TeamMembership(
                    user_id=user_id,
                    game_id=game_id,
                    team_id=team_id,
                    authority=authority,
                    granted_at=request.app.state.clock.now(),
                    granted_by=actor.id,
                )
            )
            if authority == "submitter":
                state = db_session.get(TeamOperationalState, (game_id, team_id))
                if state:
                    state.blocked, state.reason = False, ""
                    state.updated_at = request.app.state.clock.now()
            audit(
                db_session,
                actor.id,
                game_id,
                "membership_granted",
                "team_membership",
                f"{user_id}:{team_id}",
                request.app.state.clock.now(),
                {"authority": authority},
            )
        return RedirectResponse("/admin", status_code=303)

    @router.post("/admin/roles")
    def add_role(
        request: Request,
        user_id: Annotated[UUID, Form()],
        game_id: str = Form(),
        role: str = Form(),
    ) -> Response:
        actor = _current_user(request, db, settings)
        if actor is None:
            raise HTTPException(401, "Authentication required")
        if role not in {"game_admin", "adjudicator"}:
            raise HTTPException(422, "Invalid role")
        with db.transaction() as db_session:
            if not is_game_admin(db_session, actor.id, game_id):
                raise AccessChangedError
            db_session.add(
                GameRole(
                    user_id=user_id,
                    game_id=game_id,
                    role=role,
                    granted_at=request.app.state.clock.now(),
                    granted_by=actor.id,
                )
            )
            audit(
                db_session,
                actor.id,
                game_id,
                "game_role_granted",
                "game_role",
                f"{user_id}:{role}",
                request.app.state.clock.now(),
            )
        return RedirectResponse("/admin", status_code=303)

    @router.post("/admin/external/{request_id}/approve")
    def approve_external(
        request: Request,
        request_id: UUID,
        team_id: str = Form(default=""),
        authority: str = Form(default="member"),
        role: str = Form(default=""),
    ) -> Response:
        actor = _current_user(request, db, settings)
        if actor is None:
            raise HTTPException(401, "Authentication required")
        if authority not in {"member", "submitter"}:
            raise HTTPException(422, "Invalid authority")
        if role and role not in {"game_admin", "adjudicator"}:
            raise HTTPException(422, "Invalid role")
        with db.transaction() as db_session:
            pending = db_session.get(PendingAccessRequest, request_id)
            if pending is None:
                raise HTTPException(404, "Not found")
            if not is_game_admin(db_session, actor.id, pending.game_id):
                raise AccessChangedError
            binding = db_session.get(ExternalIdentityBinding, pending.binding_id)
            if binding is None:
                raise HTTPException(404, "Not found")
            user = db_session.get(User, binding.user_id)
            if user is None:
                raise HTTPException(404, "Not found")
            user.pending = False
            user.updated_at = request.app.state.clock.now()
            pending.status = "approved"
            pending.reviewed_at = request.app.state.clock.now()
            pending.reviewed_by = actor.id
            if team_id:
                game = db_session.get(AdminGame, pending.game_id)
                if game is None:
                    raise HTTPException(404, "Not found")
                configured = ScenarioConfiguration.model_validate(
                    configuration_at(
                        db_session,
                        pending.game_id,
                        request.app.state.clock.now(),
                        max(1, game.current_turn),
                    ).configuration
                )
                if team_id not in {team.id for team in configured.teams}:
                    raise HTTPException(422, "Unknown configured team")
                db_session.add(
                    TeamMembership(
                        user_id=user.id,
                        game_id=pending.game_id,
                        team_id=team_id,
                        authority=authority,
                        granted_at=request.app.state.clock.now(),
                        granted_by=actor.id,
                    )
                )
                if authority == "submitter":
                    state = db_session.get(TeamOperationalState, (pending.game_id, team_id))
                    if state:
                        state.blocked, state.reason = False, ""
                        state.updated_at = request.app.state.clock.now()
            if role:
                db_session.add(
                    GameRole(
                        user_id=user.id,
                        game_id=pending.game_id,
                        role=role,
                        granted_at=request.app.state.clock.now(),
                        granted_by=actor.id,
                    )
                )
            audit(
                db_session,
                actor.id,
                pending.game_id,
                "external_access_approved",
                "pending_access_request",
                str(pending.id),
                request.app.state.clock.now(),
                {"team_id": team_id or None, "authority": authority, "role": role or None},
            )
        return RedirectResponse("/admin", status_code=303)

    @router.post("/admin/provider-mappings")
    def add_mapping(
        request: Request,
        provider_scope_id: Annotated[UUID, Form()],
        external_group: str = Form(),
        suggested_team_id: str = Form(default=""),
        suggested_role: str = Form(default=""),
    ) -> Response:
        actor = _current_user(request, db, settings)
        if actor is None:
            raise HTTPException(401, "Authentication required")
        if not external_group.strip():
            raise HTTPException(422, "External group must be an exact nonempty identifier")
        if suggested_role and suggested_role not in {"game_admin", "adjudicator"}:
            raise HTTPException(422, "Invalid suggested role")
        with db.transaction() as db_session:
            scope = db_session.get(ProviderScope, provider_scope_id)
            if scope is None:
                raise HTTPException(404, "Not found")
            if not is_game_admin(db_session, actor.id, scope.game_id):
                raise AccessChangedError
            db_session.add(
                ProviderGroupMapping(
                    provider_scope_id=scope.id,
                    external_group=external_group,
                    suggested_team_id=suggested_team_id or None,
                    suggested_role=suggested_role or None,
                )
            )
        return RedirectResponse("/admin", status_code=303)

    @router.post("/admin/external/{request_id}/deny")
    def deny_external(request: Request, request_id: UUID) -> Response:
        actor = _current_user(request, db, settings)
        if actor is None:
            raise HTTPException(401, "Authentication required")
        with db.transaction() as db_session:
            pending = db_session.get(PendingAccessRequest, request_id)
            if pending is None:
                raise HTTPException(404, "Not found")
            if not is_game_admin(db_session, actor.id, pending.game_id):
                raise AccessChangedError
            pending.status = "denied"
            pending.reviewed_at = request.app.state.clock.now()
            pending.reviewed_by = actor.id
            audit(
                db_session,
                actor.id,
                pending.game_id,
                "external_access_denied",
                "pending_access_request",
                str(pending.id),
                request.app.state.clock.now(),
            )
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
        dataset_id: UUID,
        scope_id: str,
        known_at: datetime,
        effective_microseconds: int,
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
            principal = resolve_principal(db_session, user, game_id)
            dataset = db_session.get(Dataset, dataset_id)
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
                    dataset_id=dataset_id,
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

    return router


def __token_hash(token: str) -> bytes:
    import hashlib

    return hashlib.sha256(token.encode()).digest()
