"""Authenticated, server-rendered 1D-1 workspace."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, ValidationError
from sqlalchemy import select

from living_memory.administration import AdminGame, governing_configuration
from living_memory.config import Settings
from living_memory.db import Database, run_retryable
from living_memory.forms import csrf_token
from living_memory.identity import TeamMembership, User, resolve_principal
from living_memory.web import _current_user, shell_context
from living_memory.workspace import (
    Amendment,
    AmendmentDecision,
    DraftComment,
    IdempotencyConflict,
    PackageRevision,
    SubmissionVersion,
)
from living_memory.workspace_service import (
    ActionText,
    Command,
    Conflict,
    Package,
    authorize,
    execute,
    get_draft,
    get_submission,
    package,
)


class PersonView(BaseModel):
    id: UUID
    name: str


class CommentView(BaseModel):
    action_id: UUID | None
    author: str
    body: str
    created_at: datetime


class RevisionView(BaseModel):
    version: int
    package: Package
    author: str
    created_at: datetime


class AmendmentView(BaseModel):
    id: UUID
    version: int
    base_version: int
    status: str
    reason: str | None


class WorkspaceView(BaseModel):
    game_id: str
    title: str
    team_id: str
    teams: list[str]
    team_names: dict[str, str]
    turn: int
    turns: list[int]
    editable: bool
    review: bool
    submitter: bool
    version: int
    package: Package
    people: list[PersonView]
    comments: list[CommentView]
    history: list[RevisionView]
    submissions: list[RevisionView]
    amendments: list[AmendmentView]
    submission_version: int = 0
    effective_version: int | None = None
    submission_status: str | None = None
    submitted_at: datetime | None = None
    deadline: datetime | None = None


def workspace_router(db: Database, templates: Jinja2Templates, settings: Settings) -> APIRouter:
    router = APIRouter()

    def identity(request: Request) -> UUID:
        user = _current_user(request, db, settings)
        if user is None:
            raise HTTPException(401, "Authentication required")
        return user.id

    def read(
        request: Request, game_id: str, team_id: str | None, turn: int | None, review: bool
    ) -> WorkspaceView:
        uid = identity(request)
        now = request.app.state.clock.now()
        with db.transaction() as session:
            game = session.get(AdminGame, game_id)
            user = session.get(User, uid)
            if game is None or user is None:
                raise LookupError("Not found")
            principal = resolve_principal(session, user, game_id, now)
            config = governing_configuration(session, game, now)
            teams = [
                t.id
                for t in config.teams
                if principal.permits(game_id, "adjudicator" if review else t.id)
            ]
            selected = team_id or (teams[0] if teams else "")
            authorize(session, uid, game_id, selected, now, review=review)
            selected_turn = game.current_turn if turn is None else turn
            if selected_turn not in {t.number for t in config.turns}:
                raise LookupError("Not found")
            draft = get_draft(session, game_id, selected, selected_turn)
            submission = get_submission(session, game_id, selected, selected_turn)
            member = session.get(TeamMembership, (uid, game_id, selected))
            people = [
                PersonView(id=u.id, name=u.display_name)
                for u in session.scalars(
                    select(User)
                    .join(TeamMembership, User.id == TeamMembership.user_id)
                    .where(
                        TeamMembership.game_id == game_id,
                        TeamMembership.team_id == selected,
                        User.active.is_(True),
                        User.pending.is_(False),
                    )
                    .order_by(User.display_name)
                )
            ]

            def name(user_id: UUID | None) -> str:
                author = session.get(User, user_id) if user_id else None
                return author.display_name if author else "Unknown author"

            history = []
            comments = []
            if draft:
                history = [
                    RevisionView(
                        version=r.version,
                        package=Package.model_validate(r.snapshot),
                        author=name(r.author_user_id),
                        created_at=r.created_at,
                    )
                    for r in session.scalars(
                        select(PackageRevision)
                        .where(PackageRevision.draft_id == draft.id)
                        .order_by(PackageRevision.version.desc())
                    )
                ]
                comments = [
                    CommentView(
                        action_id=c.draft_action_id,
                        author=name(c.author_user_id),
                        body=c.body,
                        created_at=c.created_at,
                    )
                    for c in session.scalars(
                        select(DraftComment)
                        .where(DraftComment.draft_id == draft.id)
                        .order_by(DraftComment.created_at, DraftComment.id)
                    )
                ]
            versions = []
            amendments = []
            if submission:
                versions = [
                    RevisionView(
                        version=r.version,
                        package=Package.model_validate(r.snapshot),
                        author=name(r.submitted_by),
                        created_at=r.created_at,
                    )
                    for r in session.scalars(
                        select(SubmissionVersion)
                        .where(SubmissionVersion.submission_id == submission.id)
                        .order_by(SubmissionVersion.version.desc())
                    )
                ]
                for a in session.scalars(
                    select(Amendment)
                    .where(Amendment.submission_id == submission.id)
                    .order_by(Amendment.version.desc())
                ):
                    decision = session.scalar(
                        select(AmendmentDecision).where(AmendmentDecision.amendment_id == a.id)
                    )
                    amendments.append(
                        AmendmentView(
                            id=a.id,
                            version=a.version,
                            base_version=a.base_version,
                            status=a.status,
                            reason=decision.reason if decision else None,
                        )
                    )
            return WorkspaceView(
                game_id=game_id,
                title=game.title,
                team_id=selected,
                teams=teams,
                team_names={team.id: team.name for team in config.teams if team.id in teams},
                turn=selected_turn,
                turns=[t.number for t in config.turns],
                editable=game.status == "active" and selected_turn == game.current_turn,
                review=review,
                submitter=member is not None and member.authority == "submitter",
                version=draft.version if draft else 0,
                package=package(session, draft),
                people=people,
                comments=comments,
                history=history,
                submissions=versions,
                amendments=amendments,
                submission_version=submission.version if submission else 0,
                effective_version=submission.effective_version if submission else None,
                submission_status=submission.status if submission else None,
                submitted_at=submission.submitted_at if submission else None,
                deadline=submission.deadline if submission else None,
            )

    def render(
        request: Request,
        game_id: str,
        team_id: str | None,
        turn: int | None,
        review: bool,
        *,
        error: str | None = None,
        attempted: Command | None = None,
        conflict: Conflict | None = None,
        raw: dict[str, Any] | None = None,
        status: int = 200,
    ) -> Response:
        try:
            view = read(request, game_id, team_id, turn, review)
        except LookupError:
            raise HTTPException(404, "Not found") from None
        # Full documents for ordinary navigation and HTMX body swaps alike.
        selected_editor = request.query_params.get("edit")
        if selected_editor is None and attempted is not None:
            if attempted.operation == "intention":
                selected_editor = "intention"
            elif attempted.operation == "action":
                selected_editor = (
                    f"action-{attempted.action_id}" if attempted.action_id else "new-action"
                )
            elif attempted.operation == "comment":
                selected_editor = (
                    f"comment-{attempted.action_id}"
                    if attempted.action_id
                    else "package-comment"
                )
            elif attempted.operation == "decide" and attempted.amendment_id:
                selected_editor = f"decision-{attempted.amendment_id}"
        if selected_editor is None and raw is not None:
            operation = raw.get("operation")
            action_id = raw.get("action_id")
            amendment_id = raw.get("amendment_id")
            if operation == "intention":
                selected_editor = "intention"
            elif operation == "action":
                selected_editor = f"action-{action_id}" if action_id else "new-action"
            elif operation == "comment":
                selected_editor = f"comment-{action_id}" if action_id else "package-comment"
            elif operation == "decide" and amendment_id:
                selected_editor = f"decision-{amendment_id}"
        return templates.TemplateResponse(
            request=request,
            name="adjudicate.html" if review else "play.html",
            context={
                "view": view,
                "shell": shell_context(request, db, settings),
                "csrf": csrf_token(request),
                "new_key": lambda: str(uuid4()),
                "error": error,
                "attempted": attempted,
                "raw": raw or {},
                "conflict": conflict,
                "editor": selected_editor,
                "conflict_base": (
                    Package.model_validate(conflict.base)
                    if conflict and isinstance(conflict.base, dict) and "actions" in conflict.base
                    else None
                ),
                "conflict_current": (
                    Package.model_validate(conflict.current)
                    if conflict
                    and isinstance(conflict.current, dict)
                    and "actions" in conflict.current
                    else None
                ),
            },
            status_code=status,
            headers={"Cache-Control": "no-store", "HX-Retarget": "body", "HX-Reswap": "innerHTML"},
        )

    @router.get("/play", response_class=HTMLResponse)
    def play(
        request: Request, game_id: str, team_id: str | None = None, turn: int | None = None
    ) -> Response:
        return render(request, game_id, team_id, turn, False)

    @router.get("/adjudicate", response_class=HTMLResponse)
    def adjudicate(
        request: Request, game_id: str, team_id: str | None = None, turn: int | None = None
    ) -> Response:
        return render(request, game_id, team_id, turn, True)

    @router.post("/workspace/{game_id}/{team_id}/{turn}")
    def mutate(
        request: Request, game_id: str, team_id: str, turn: int, command: Command
    ) -> Response:
        """Typed JSON endpoint for clients; browser forms use the sibling route."""
        return apply(request, game_id, team_id, turn, command)

    def apply(
        request: Request, game_id: str, team_id: str, turn: int, command: Command
    ) -> Response:
        uid = identity(request)
        review = command.operation == "decide"

        def work() -> dict[str, Any]:
            with db.transaction() as session:
                return execute(
                    session,
                    user_id=uid,
                    game_id=game_id,
                    team_id=team_id,
                    turn=turn,
                    command=command,
                    now=request.app.state.clock.now(),
                )

        try:
            result = run_retryable(work)
        except LookupError:
            raise HTTPException(404, "Not found") from None
        except PermissionError as exc:
            raise HTTPException(403, str(exc)) from None
        except (ValueError, Conflict) as exc:
            return render(
                request,
                game_id,
                team_id,
                turn,
                review,
                error=str(exc),
                attempted=command,
                conflict=exc if isinstance(exc, Conflict) else None,
                status=409 if isinstance(exc, (Conflict, IdempotencyConflict)) else 422,
            )
        return RedirectResponse(result["redirect"], status_code=303)

    @router.post("/workspace/{game_id}/{team_id}/{turn}/form")
    async def form(request: Request, game_id: str, team_id: str, turn: int) -> Response:
        import anyio

        fields = await request.form()
        values: dict[str, Any] = {k: str(v) for k, v in fields.items() if k != "csrf_token"}
        if values.get("operation") == "action":
            values["body"] = {k: values.pop(k, "") for k in ActionText.model_fields}
        for k in ("action_id", "owner_user_id", "effective_version", "amendment_id", "decision"):
            if values.get(k) == "":
                values.pop(k)
        if "order" in values:
            values["order"] = str(values["order"]).split()
        try:
            command = Command.model_validate(values)
        except ValidationError as exc:
            message = "; ".join(
                f"{'.'.join(map(str, item['loc']))}: {item['msg']}" for item in exc.errors()
            )
            return await anyio.to_thread.run_sync(
                lambda: render(
                    request,
                    game_id,
                    team_id,
                    turn,
                    values.get("operation") == "decide",
                    error=message,
                    raw=values,
                    status=422,
                )
            )
        return await anyio.to_thread.run_sync(
            lambda: apply(request, game_id, team_id, turn, command)
        )

    return router
