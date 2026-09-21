"""Authenticated, server-rendered 1D-1 workspace."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
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


ENHANCED_MEDIA_TYPE = "application/vnd.living-memory.workspace+json"
SUCCESS_MESSAGES = {
    "intention": "Overall intention saved.",
    "action": "Action saved.",
    "comment": "Comment added.",
    "submit": "Turn package submitted.",
    "amend": "Amendment proposed.",
    "remove": "Action removed.",
    "reorder": "Action order updated.",
    "decide": "Amendment decision recorded.",
}


def _enhanced(request: Request) -> bool:
    """Require an explicit opt-in so existing form and API clients keep their contract."""
    return (
        request.headers.get("x-workspace-enhanced") == "1"
        and ENHANCED_MEDIA_TYPE in request.headers.get("accept", "").lower()
    )


def _editor_identity(values: Command | dict[str, Any]) -> str | None:
    operation = values.operation if isinstance(values, Command) else values.get("operation")
    action_id = values.action_id if isinstance(values, Command) else values.get("action_id")
    amendment_id = (
        values.amendment_id if isinstance(values, Command) else values.get("amendment_id")
    )
    if operation == "intention":
        return "intention"
    if operation == "action":
        return f"action-{action_id}" if action_id else "new-action"
    if operation == "comment":
        return f"comment-{action_id}" if action_id else "package-comment"
    if operation == "decide" and amendment_id:
        return f"decision-{amendment_id}"
    return None


def _refresh_url(game_id: str, team_id: str, turn: int, review: bool) -> str:
    page = "adjudicate" if review else "play"
    return f"/{page}?game_id={game_id}&team_id={team_id}&turn={turn}"


def _field_error(field: str, message: str) -> dict[str, str]:
    return {"field": field, "message": message}


def _schema_errors(exc: ValidationError) -> list[dict[str, str]]:
    """Translate Pydantic implementation details into stable, readable form errors."""
    details: list[dict[str, str]] = []
    labels = {
        "action_id": "action",
        "amendment_id": "amendment",
        "decision": "decision",
        "effective_version": "submission version",
        "expected_version": "workspace version",
        "key": "save request",
        "operation": "workspace action",
        "owner_user_id": "responsible teammate",
        "order": "action order",
    }
    for item in exc.errors():
        location = [str(part) for part in item["loc"] if str(part) != "body"]
        field = location[-1] if location else "_form"
        label = labels.get(field, field.replace("_", " "))
        error_type = str(item.get("type", ""))
        if error_type == "missing":
            message = f"Enter {label}."
        elif "uuid" in error_type:
            message = f"Choose a valid {label}."
        elif error_type in {"literal_error", "enum"}:
            message = f"Choose a valid {label}."
        elif error_type.startswith(("int_", "greater_than")):
            message = f"Enter a valid {label}."
        else:
            message = f"Check {label}."
        details.append(_field_error(field, message))
    return details


def _command_errors(exc: ValueError) -> list[dict[str, str]]:
    message = str(exc)
    if message == "Enter a comment":
        return [_field_error("comment", message)]
    if message == "Choose a decision and enter a reason":
        return [
            _field_error("decision", "Choose Accept or Reject."),
            _field_error("reason", "Enter a reason."),
        ]
    if message == "Enter an overall intention before submitting":
        return [_field_error("overall_intention", message)]
    if message == "Complete all four fields for every native action":
        return [_field_error("actions", message)]
    if message == "Order must contain every current action exactly once":
        return [_field_error("order", message)]
    return [_field_error("_form", message)]


def _conflict_display(value: Any, view: WorkspaceView) -> dict[str, Any]:
    """Build presentation data without exposing internal identifiers as labels."""
    if value is None:
        return {"kind": "value", "state": "missing", "fields": []}
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    if not isinstance(value, dict):
        return {
            "kind": "value",
            "state": "empty" if value in (None, "") else "available",
            "fields": [{"label": "Value", "value": value or "", "empty": value in (None, "")}],
        }
    people = {str(person.id): person.name for person in view.people}
    if "actions" in value:
        action_lines = []
        for index, action in enumerate(value.get("actions", []), start=1):
            body = action.get("body", {})
            owner_id = action.get("owner_user_id")
            owner = people.get(str(owner_id), "Former teammate") if owner_id else "Unassigned"
            removed = " (removed)" if action.get("removed") else ""
            action_lines.append(
                f"{index}. {body.get('title') or '(empty)'}{removed}\n"
                f"Description: {body.get('description') or '(empty)'}\n"
                f"Intent of action: {body.get('intent') or '(empty)'}\n"
                f"Anticipated reaction: {body.get('anticipated_reaction') or '(empty)'}\n"
                f"Responsible teammate: {owner}"
            )
        return {
            "kind": "package",
            "state": "available",
            "fields": [
                {
                    "label": "Overall intention",
                    "value": value.get("overall_intention", ""),
                    "empty": not bool(value.get("overall_intention")),
                },
                {
                    "label": "Actions",
                    "value": "\n\n".join(action_lines),
                    "empty": not bool(action_lines),
                },
            ],
        }
    body = value.get("body")
    if isinstance(body, BaseModel):
        body = body.model_dump(mode="json")
    if isinstance(body, dict) and (
        value.get("operation") == "action" or "operation" not in value
    ):
        fields = [
            {
                "label": label,
                "value": body.get(field, ""),
                "empty": not bool(body.get(field, "")),
            }
            for field, label in (
                ("title", "Title"),
                ("description", "Description"),
                ("intent", "Intent of action"),
                ("anticipated_reaction", "Anticipated reaction"),
            )
        ]
        owner_id = value.get("owner_user_id")
        fields.append(
            {
                "label": "Responsible teammate",
                "value": people.get(str(owner_id), "Former teammate") if owner_id else "Unassigned",
                "empty": owner_id is None,
            }
        )
        return {
            "kind": "action",
            "state": "removed" if value.get("removed") else "available",
            "fields": fields,
        }
    labels = {
        "operation": "Requested operation",
        "overall_intention": "Overall intention",
        "decision": "Decision",
        "reason": "Reason",
        "effective_version": "Effective version",
        "version": "Version",
        "amendment_status": "Amendment status",
    }
    operations = {
        "intention": "Save overall intention",
        "action": "Save action",
        "comment": "Add comment",
        "submit": "Submit turn package",
        "amend": "Propose amendment",
        "remove": "Remove action",
        "reorder": "Reorder actions",
        "decide": "Record amendment decision",
    }
    operation = value.get("operation")
    relevant = {
        "intention": {"operation", "overall_intention"},
        "amend": {"operation", "effective_version"},
        "decide": {"operation", "decision", "reason"},
    }.get(str(operation), {"operation"})
    fields = [
        {
            "label": label,
            "value": (
                operations.get(str(value.get(field)), str(value.get(field, "")))
                if field == "operation"
                else value.get(field, "")
            ),
            "empty": value.get(field) in (None, ""),
        }
        for field, label in labels.items()
        if field in value and (operation is None or field in relevant)
    ]
    action_id = value.get("action_id")
    if action_id:
        action = next(
            (item for item in view.package.actions if str(item.id) == str(action_id)), None
        )
        fields.append(
            {
                "label": "Action",
                "value": action.body.title if action else "Removed action",
                "empty": False,
            }
        )
    if value.get("order"):
        titles = {str(item.id): item.body.title for item in view.package.actions}
        fields.append(
            {
                "label": "Requested action order",
                "value": "\n".join(
                    f"{index}. {titles.get(str(item), 'Removed action')}"
                    for index, item in enumerate(value["order"], start=1)
                ),
                "empty": False,
            }
        )
    return {
        "kind": "text" if "overall_intention" in value else "command",
        "state": "empty" if fields and all(item["empty"] for item in fields) else "available",
        "fields": fields,
    }


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
        field_errors: list[dict[str, str]] | None = None,
        status: int = 200,
    ) -> Response:
        try:
            view = read(request, game_id, team_id, turn, review)
        except LookupError:
            raise HTTPException(404, "Not found") from None
        # Full documents for ordinary navigation and HTMX body swaps alike.
        selected_editor = request.query_params.get("edit")
        if selected_editor is None and attempted is not None:
            selected_editor = _editor_identity(attempted)
        if selected_editor is None and raw is not None:
            selected_editor = _editor_identity(raw)
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
                "field_errors": field_errors or [],
                "conflict": conflict,
                "conflict_display": (
                    {
                        "base": _conflict_display(conflict.base, view),
                        "current": _conflict_display(conflict.current, view),
                        "mine": _conflict_display(conflict.submitted, view),
                    }
                    if conflict
                    else None
                ),
                "editor": selected_editor,
                "saved_message": SUCCESS_MESSAGES.get(request.query_params.get("saved", "")),
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
        refresh = _refresh_url(game_id, team_id, turn, review)

        def work() -> dict[str, Any]:
            with db.transaction() as session:
                result = dict(
                    execute(
                        session,
                        user_id=uid,
                        game_id=game_id,
                        team_id=team_id,
                        turn=turn,
                        command=command,
                        now=request.app.state.clock.now(),
                    )
                )
                editor = _editor_identity(command)
                if command.operation == "action" and command.action_id is None:
                    revision = session.get(PackageRevision, UUID(result["id"]))
                    if revision is not None:
                        previous_ids: set[str] = set()
                        if revision.version > 1:
                            previous = session.scalar(
                                select(PackageRevision).where(
                                    PackageRevision.draft_id == revision.draft_id,
                                    PackageRevision.version == revision.version - 1,
                                )
                            )
                            if previous is not None:
                                previous_ids = {
                                    str(item["id"]) for item in previous.snapshot.get("actions", [])
                                }
                        added = [
                            str(item["id"])
                            for item in revision.snapshot.get("actions", [])
                            if str(item["id"]) not in previous_ids
                        ]
                        if len(added) == 1:
                            editor = f"action-{added[0]}"
                result["editor"] = editor
                revision = (
                    session.get(PackageRevision, UUID(result["id"]))
                    if result.get("kind") == "package_revision"
                    else None
                )
                result["committed_draft_version"] = revision.version if revision else None
                return result

        def enhanced_error(
            *,
            outcome: str,
            message: str,
            status: int,
            attempted: Command | None = None,
            conflict: Conflict | None = None,
            raw: dict[str, Any] | None = None,
            errors: list[dict[str, str]] | None = None,
        ) -> Response:
            try:
                current = read(request, game_id, team_id, turn, review)
            except LookupError:
                raise HTTPException(404, "Not found") from None
            rendered = render(
                request,
                game_id,
                team_id,
                turn,
                review,
                error=message,
                attempted=attempted,
                conflict=conflict,
                raw=raw,
                field_errors=errors,
                status=status,
            )
            payload: dict[str, Any] = {
                "outcome": outcome,
                "operation": command.operation,
                "key": str(command.key),
                "editor": _editor_identity(command),
                "refresh": refresh,
                "current_version": (
                    current.submission_version if review else current.version
                ),
                "errors": errors or [],
                "values": command.model_dump(mode="json"),
                "html": bytes(rendered.body).decode("utf-8"),
            }
            if conflict is not None:
                payload["conflict"] = {
                    "base": conflict.base,
                    "current": conflict.current,
                    "mine": conflict.submitted,
                }
                payload["conflict_display"] = {
                    "base": _conflict_display(conflict.base, current),
                    "current": _conflict_display(conflict.current, current),
                    "mine": _conflict_display(conflict.submitted, current),
                }
            return JSONResponse(
                jsonable_encoder(payload),
                status_code=status,
                media_type=ENHANCED_MEDIA_TYPE,
                headers={
                    "Cache-Control": "no-store",
                    "Vary": "Accept, X-Workspace-Enhanced",
                },
            )

        try:
            result = run_retryable(work)
        except LookupError:
            raise HTTPException(404, "Not found") from None
        except PermissionError as exc:
            raise HTTPException(403, str(exc)) from None
        except Conflict as exc:
            if _enhanced(request):
                return enhanced_error(
                    outcome="conflict",
                    message=str(exc),
                    status=409,
                    attempted=command,
                    conflict=exc,
                )
            return render(
                request,
                game_id,
                team_id,
                turn,
                review,
                error=str(exc),
                attempted=command,
                conflict=exc,
                status=409,
            )
        except IdempotencyConflict as exc:
            if _enhanced(request):
                return enhanced_error(
                    outcome="key_conflict",
                    message=str(exc),
                    status=409,
                    attempted=command,
                )
            return render(
                request,
                game_id,
                team_id,
                turn,
                review,
                error=str(exc),
                attempted=command,
                status=409,
            )
        except ValueError as exc:
            errors = _command_errors(exc)
            if _enhanced(request):
                return enhanced_error(
                    outcome="validation_error",
                    message=str(exc),
                    status=422,
                    attempted=command,
                    errors=errors,
                )
            return render(
                request,
                game_id,
                team_id,
                turn,
                review,
                error=str(exc),
                attempted=command,
                field_errors=errors,
                status=422,
            )
        if _enhanced(request):
            return JSONResponse(
                {
                    "outcome": "committed",
                    "operation": command.operation,
                    "key": str(command.key),
                    "editor": result.get("editor"),
                    "refresh": result["redirect"],
                    "committed_draft_version": result.get("committed_draft_version"),
                },
                media_type=ENHANCED_MEDIA_TYPE,
                headers={
                    "Cache-Control": "no-store",
                    "Vary": "Accept, X-Workspace-Enhanced",
                },
            )
        return RedirectResponse(
            f"{result['redirect']}&saved={command.operation}", status_code=303
        )

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
            errors = _schema_errors(exc)
            message = "Please correct the highlighted fields."

            def invalid_response() -> Response:
                review = values.get("operation") == "decide"
                rendered = render(
                    request,
                    game_id,
                    team_id,
                    turn,
                    review,
                    error=message,
                    raw=values,
                    field_errors=errors,
                    status=422,
                )
                if not _enhanced(request):
                    return rendered
                payload = {
                    "outcome": "validation_error",
                    "operation": values.get("operation"),
                    "key": values.get("key"),
                    "editor": _editor_identity(values),
                    "refresh": _refresh_url(game_id, team_id, turn, review),
                    "errors": errors,
                    "values": values,
                    "html": bytes(rendered.body).decode("utf-8"),
                }
                return JSONResponse(
                    jsonable_encoder(payload),
                    status_code=422,
                    media_type=ENHANCED_MEDIA_TYPE,
                    headers={
                        "Cache-Control": "no-store",
                        "Vary": "Accept, X-Workspace-Enhanced",
                    },
                )

            return await anyio.to_thread.run_sync(
                invalid_response
            )
        return await anyio.to_thread.run_sync(
            lambda: apply(request, game_id, team_id, turn, command)
        )

    return router
