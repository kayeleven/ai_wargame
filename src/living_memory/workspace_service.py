"""Wrapper-owned workspace commands. Call mutations inside one transaction."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from living_memory.administration import AdminGame, governing_configuration, lock_game
from living_memory.clocks import Clock
from living_memory.identity import TeamMembership, User, resolve_principal
from living_memory.team_authority import effective_memberships
from living_memory.workspace import (
    Amendment,
    AmendmentDecision,
    Draft,
    DraftAction,
    DraftComment,
    DraftRevision,
    EffectiveVersionEvent,
    PackageRevision,
    Submission,
    SubmissionVersion,
    SubmittedAction,
    WorkspaceConflict,
    canonical_fingerprint,
    claim_request_key,
    completed_request,
)


class ActionText(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = ""
    description: str = ""
    intent: str = ""
    anticipated_reaction: str = ""


class ActionView(BaseModel):
    id: UUID
    action_id: str
    body: ActionText
    owner_user_id: UUID | None = None
    position: int
    removed: bool = False
    origin: str = "manual"


class Package(BaseModel):
    content_version: Literal[1] = 1
    overall_intention: str = ""
    actions: list[ActionView] = Field(default_factory=list)

    def validate_submission(self) -> None:
        if not self.overall_intention.strip():
            raise ValueError("Enter an overall intention before submitting")
        if any(
            not value.strip()
            for a in self.actions
            if not a.removed and a.origin == "manual"
            for value in a.body.model_dump().values()
        ):
            raise ValueError("Complete all four fields for every native action")


class Command(BaseModel):
    model_config = ConfigDict(extra="forbid")
    operation: Literal[
        "intention", "action", "remove", "reorder", "comment", "submit", "amend", "decide"
    ]
    key: UUID
    expected_version: int = Field(ge=0)
    effective_version: int | None = None
    expected_deadline: AwareDatetime | None = None
    expected_consequence: Literal["immediate", "approval_required"] | None = None
    expected_late: bool | None = None
    action_id: UUID | None = None
    owner_user_id: UUID | None = None
    body: ActionText = Field(default_factory=ActionText)
    overall_intention: str = ""
    order: list[UUID] = Field(default_factory=list)
    comment: str = ""
    amendment_id: UUID | None = None
    decision: Literal["accepted", "rejected"] | None = None
    reason: str = ""


class Confirmation(BaseModel):
    effective_version: int | None
    expected_deadline: AwareDatetime
    expected_consequence: Literal["immediate", "approval_required"]
    expected_late: bool


class ConfirmationRequired(ValueError):
    def __init__(self, expectations: Confirmation):
        super().__init__("Confirm the submission consequence before continuing.")
        self.expectations = expectations


def command_payload(command: Command) -> dict[str, Any]:
    """Keep old fingerprints identical when the new confirmation fields are absent."""
    payload = command.model_dump(mode="json")
    for name in ("expected_deadline", "expected_consequence", "expected_late"):
        if payload[name] is None:
            del payload[name]
    return payload


def confirmation_for(
    session: Session, game: AdminGame, submission: Submission | None, turn: int, now: datetime
) -> Confirmation:
    deadline = (
        submission.deadline
        if submission
        else next(
            t.submission_deadline
            for t in governing_configuration(session, game, now).turns
            if t.number == turn
        )
    )
    # PR 3.1 deliberately retains the current amendment-only revision policy.
    return Confirmation(
        effective_version=submission.effective_version if submission else None,
        expected_deadline=deadline,
        expected_consequence="approval_required" if submission else "immediate",
        expected_late=now >= deadline,
    )


class Conflict(WorkspaceConflict):
    def __init__(self, base: Any, current: Any, submitted: Any):
        super().__init__("This workspace changed. Compare your input with the current version.")
        self.base, self.current, self.submitted = base, current, submitted


def _package_at_version(session: Session, draft: Draft | None, version: int) -> Package:
    """Return an existing immutable draft snapshot; never invent missing history."""
    if version == 0:
        return Package()
    if draft is None or version < 0 or version > draft.version:
        raise Conflict(None, Package().model_dump(mode="json"), {"version": version})
    revision = session.scalar(
        select(PackageRevision).where(
            PackageRevision.draft_id == draft.id,
            PackageRevision.version == version,
        )
    )
    if revision is None:
        raise Conflict(None, package(session, draft).model_dump(mode="json"), {"version": version})
    return Package.model_validate(revision.snapshot)


def _action_scope(value: Package, action_id: UUID) -> dict[str, Any] | None:
    action = next((item for item in value.actions if item.id == action_id), None)
    if action is None:
        return None
    return {
        "id": str(action.id),
        "body": action.body.model_dump(mode="json"),
        "owner_user_id": str(action.owner_user_id) if action.owner_user_id else None,
        "removed": action.removed,
    }


def _check_command_baseline(
    session: Session, draft: Draft | None, current: Package, command: Command
) -> None:
    version = draft.version if draft else 0
    if command.expected_version == version:
        return
    base = _package_at_version(session, draft, command.expected_version)
    if command.operation == "intention":
        if base.overall_intention == current.overall_intention:
            return
        raise Conflict(
            {"overall_intention": base.overall_intention},
            {"overall_intention": current.overall_intention},
            {"overall_intention": command.overall_intention},
        )
    if command.operation == "action" and command.action_id is not None:
        base_action = _action_scope(base, command.action_id)
        current_action = _action_scope(current, command.action_id)
        if base_action is not None and base_action == current_action:
            return
        raise Conflict(base_action, current_action, command.model_dump(mode="json"))
    if command.operation == "action" and command.action_id is None:
        return
    if command.operation == "comment":
        # Comments append immutable content. The target is checked after replay recognition.
        return
    raise Conflict(
        base.model_dump(mode="json"),
        current.model_dump(mode="json"),
        command.model_dump(mode="json"),
    )


def authorize(
    session: Session,
    user_id: UUID,
    game_id: str,
    team_id: str,
    now: datetime,
    *,
    review: bool = False,
    write: bool = False,
) -> AdminGame:
    game = lock_game(session, game_id) if write else session.get(AdminGame, game_id)
    if game is None:
        raise LookupError("Not found")
    user = session.get(User, user_id, populate_existing=True)
    if user is None or not user.active or user.pending:
        raise LookupError("Not found")
    config = governing_configuration(session, game, now)
    if team_id not in {t.id for t in config.teams}:
        raise LookupError("Not found")
    if review:
        if not resolve_principal(session, user, game_id, now).permits(game_id, "adjudicator"):
            raise LookupError("Not found")
    elif team_id not in effective_memberships(session, user_id, game_id, now):
        raise LookupError("Not found")
    return game


def package(session: Session, draft: Draft | None) -> Package:
    if draft is None:
        return Package()
    actions = session.scalars(
        select(DraftAction)
        .where(DraftAction.draft_id == draft.id)
        .order_by(DraftAction.position, DraftAction.id)
    ).all()
    return Package(
        overall_intention=str(draft.header.get("overall_intention", "")),
        actions=[
            ActionView(
                id=a.id,
                action_id=a.action_id,
                body=ActionText.model_validate(a.body),
                owner_user_id=a.owner_user_id,
                position=a.position,
                removed=a.removed_at is not None,
                origin=a.origin,
            )
            for a in actions
        ],
    )


def get_draft(session: Session, game_id: str, team_id: str, turn: int) -> Draft | None:
    return session.scalar(
        select(Draft).where(Draft.game_id == game_id, Draft.team_id == team_id, Draft.turn == turn)
    )


def get_submission(session: Session, game_id: str, team_id: str, turn: int) -> Submission | None:
    return session.scalar(
        select(Submission).where(
            Submission.game_id == game_id, Submission.team_id == team_id, Submission.turn == turn
        )
    )


def require_submitter(session: Session, user_id: UUID, game_id: str, team_id: str) -> None:
    member = session.get(TeamMembership, (user_id, game_id, team_id), populate_existing=True)
    if member is None or member.authority != "submitter":
        raise PermissionError("Only the designated submitter may submit or propose amendments")


def execute(
    session: Session,
    *,
    user_id: UUID,
    game_id: str,
    team_id: str,
    turn: int,
    command: Command,
    clock: Clock,
) -> dict[str, Any]:
    review = command.operation == "decide"
    # Cheap preflight only: no authority or timestamp from here survives the locks.
    authorize(session, user_id, game_id, team_id, clock.now(), review=review)
    game = lock_game(session, game_id)
    # Match administration's game -> sorted users lock order.
    for uid in sorted({user_id} | ({command.owner_user_id} if command.owner_user_id else set())):
        session.get(User, uid, with_for_update=True, populate_existing=True)
    draft = get_draft(session, game_id, team_id, turn)
    if draft is not None:
        session.refresh(draft, with_for_update=True)
    submission = get_submission(session, game_id, team_id, turn)
    if submission is not None:
        session.refresh(submission, with_for_update=True)
    amendment = None
    if review and submission is not None and command.amendment_id is not None:
        amendment = session.scalar(
            select(Amendment)
            .where(
                Amendment.id == command.amendment_id,
                Amendment.submission_id == submission.id,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    now = clock.now()
    authorize(session, user_id, game_id, team_id, now, review=review)
    if command.operation in {"submit", "amend"}:
        require_submitter(session, user_id, game_id, team_id)
    fingerprint = canonical_fingerprint(
        {
            "user": str(user_id),
            "team": team_id,
            "turn": turn,
            "command": command_payload(command),
        }
    )
    if command.operation in {"submit", "amend", "decide"}:
        completed = completed_request(
            session,
            game_id=game_id,
            branch_id=game.root_branch_id,
            operation=command.operation,
            key=command.key,
            fingerprint=fingerprint,
        )
        if completed is not None:
            return completed.result_ref
    if game.status != "active" or turn != game.current_turn:
        raise ValueError("Only the active current turn can be changed")
    current = package(session, draft)
    if review and (amendment is None or submission is None):
        raise LookupError("Not found")
    confirmation = None
    if command.operation in {"submit", "amend"}:
        if (
            (command.operation == "submit" and submission is not None)
            or (command.operation == "amend" and submission is None)
            or (submission is not None and submission.status == "amendment_pending")
        ):
            raise Conflict(
                None,
                {
                    "submission_status": submission.status if submission else None,
                    "effective_version": submission.effective_version if submission else None,
                },
                command.model_dump(mode="json"),
            )
        _check_command_baseline(session, draft, current, command)
        current.validate_submission()
        confirmation = confirmation_for(session, game, submission, turn, now)
        if any(
            getattr(command, name) != value for name, value in confirmation.model_dump().items()
        ):
            raise ConfirmationRequired(confirmation)
    result_id = str(uuid4())
    result_kind = "amendment_decision" if review else "package_revision"
    redirect = (
        f"/{'adjudicate' if review else 'play'}?game_id={game_id}&team_id={team_id}&turn={turn}"
    )
    record, replay = claim_request_key(
        session,
        game_id=game_id,
        branch_id=game.root_branch_id,
        operation=command.operation,
        key=command.key,
        fingerprint=fingerprint,
        result_ref={"kind": result_kind, "id": result_id, "redirect": redirect},
        now=now,
    )
    if replay:
        return record.result_ref
    if command.action_id is not None and command.action_id not in {a.id for a in current.actions}:
        raise LookupError("Not found")
    existing_owner = next(
        (a.owner_user_id for a in current.actions if a.id == command.action_id), None
    )
    if (
        command.owner_user_id
        and command.owner_user_id != existing_owner
        and team_id not in effective_memberships(session, command.owner_user_id, game_id, now)
    ):
        raise LookupError("Not found")
    if review:
        assert submission is not None and amendment is not None
        if (
            command.expected_version != submission.version
            or amendment.status != "pending"
            or amendment.base_version != submission.effective_version
        ):
            raise Conflict(
                {"effective_version": amendment.base_version},
                {
                    "version": submission.version,
                    "effective_version": submission.effective_version,
                    "amendment_status": amendment.status,
                },
                command.model_dump(mode="json"),
            )
        if command.decision is None or not command.reason.strip():
            raise ValueError("Choose a decision and enter a reason")
        amendment.status = command.decision
        session.add(
            AmendmentDecision(
                id=UUID(result_id),
                amendment_id=amendment.id,
                decision=command.decision,
                reason=command.reason,
                adjudicator_user_id=user_id,
                created_at=now,
            )
        )
        if command.decision == "accepted":
            session.flush()  # Persist the decision before its provenance FK is inserted.
            session.add(
                EffectiveVersionEvent(
                    submission_id=submission.id,
                    version=amendment.version,
                    mechanism="adjudicator_acceptance",
                    responsible_user_id=user_id,
                    effective_at=now,
                    source_decision_id=UUID(result_id),
                )
            )
            submission.effective_version = amendment.version
        submission.status, submission.updated_at = "submitted", now
        submission.version += 1
    else:
        _check_command_baseline(session, draft, current, command)
        if draft is None:
            draft = Draft(
                game_id=game_id,
                team_id=team_id,
                turn=turn,
                header={},
                version=0,
                created_at=now,
                updated_at=now,
            )
            session.add(draft)
            session.flush()
        if command.operation in {"submit", "amend"}:
            current.validate_submission()
            snapshot = current.model_copy(
                update={"actions": [a for a in current.actions if not a.removed]}
            )
            if submission is None:
                deadline = next(
                    t.submission_deadline
                    for t in governing_configuration(session, game, now).turns
                    if t.number == turn
                )
                submission = Submission(
                    game_id=game_id,
                    team_id=team_id,
                    turn=turn,
                    version=1,
                    effective_version=1,
                    deadline=deadline,
                    status="submitted",
                    submitted_at=now,
                    created_at=now,
                    updated_at=now,
                )
                session.add(submission)
                session.flush()
                content_version = 1
            else:
                versions = session.scalars(
                    select(SubmissionVersion.version).where(
                        SubmissionVersion.submission_id == submission.id
                    )
                ).all()
                content_version = max(versions) + 1
                session.add(
                    Amendment(
                        submission_id=submission.id,
                        game_id=game_id,
                        team_id=team_id,
                        version=content_version,
                        base_version=submission.effective_version,
                        proposed_by=user_id,
                        body=snapshot.model_dump(mode="json"),
                        status="pending",
                        created_at=now,
                    )
                )
                submission.version += 1
                submission.status, submission.updated_at = "amendment_pending", now
            session.add(
                SubmissionVersion(
                    submission_id=submission.id,
                    game_id=game_id,
                    team_id=team_id,
                    version=content_version,
                    snapshot=snapshot.model_dump(mode="json"),
                    created_at=now,
                    submitted_by=user_id,
                )
            )
            session.flush()
            if content_version == 1:
                session.add(
                    EffectiveVersionEvent(
                        submission_id=submission.id,
                        version=1,
                        mechanism="initial",
                        responsible_user_id=user_id,
                        effective_at=now,
                    )
                )
            for a in snapshot.actions:
                session.add(
                    SubmittedAction(
                        submission_id=submission.id,
                        game_id=game_id,
                        team_id=team_id,
                        version=content_version,
                        action_id=a.action_id,
                        body=a.body.model_dump(),
                        created_at=now,
                    )
                )
        elif command.operation == "intention":
            draft.header = {"overall_intention": command.overall_intention}
        elif command.operation == "action":
            if command.action_id:
                action = session.get(DraftAction, command.action_id)
                assert action is not None
                if action.removed_at is not None:
                    raise ValueError("Removed actions cannot be edited")
                action.body, action.owner_user_id = command.body.model_dump(), command.owner_user_id
                action.version += 1
                action.updated_at = now
            else:
                aid = uuid4()
                action = DraftAction(
                    id=aid,
                    draft_id=draft.id,
                    game_id=game_id,
                    team_id=team_id,
                    action_id=str(aid),
                    body=command.body.model_dump(),
                    owner_user_id=command.owner_user_id,
                    position=len(current.actions),
                    version=1,
                    created_at=now,
                    updated_at=now,
                )
                session.add(action)
            session.flush()
            session.add(
                DraftRevision(
                    draft_action_id=action.id,
                    game_id=game_id,
                    team_id=team_id,
                    version=action.version,
                    body=action.body,
                    author_user_id=user_id,
                    created_at=now,
                )
            )
        elif command.operation == "remove":
            action = session.get(DraftAction, command.action_id) if command.action_id else None
            if action is None:
                raise LookupError("Not found")
            action.removed_at, action.updated_at = now, now
        elif command.operation == "reorder":
            live = {a.id for a in current.actions if not a.removed}
            if len(command.order) != len(live) or set(command.order) != live:
                raise ValueError("Order must contain every current action exactly once")
            for position, aid in enumerate(command.order):
                action = session.get(DraftAction, aid)
                assert action is not None
                action.position = position
        elif command.operation == "comment":
            if not command.comment.strip():
                raise ValueError("Enter a comment")
            session.add(
                DraftComment(
                    draft_id=draft.id,
                    draft_action_id=command.action_id,
                    game_id=game_id,
                    team_id=team_id,
                    author_user_id=user_id,
                    body=command.comment,
                    created_at=now,
                )
            )
        draft.version += 1
        draft.updated_at = now
        session.flush()
        session.add(
            PackageRevision(
                id=UUID(result_id),
                draft_id=draft.id,
                game_id=game_id,
                team_id=team_id,
                version=draft.version,
                snapshot=package(session, draft).model_dump(mode="json"),
                author_user_id=user_id,
                created_at=now,
            )
        )
    session.flush()
    if confirmation is not None:
        assert submission is not None
        record.result_ref = {
            **record.result_ref,
            "completion": {
                **confirmation.model_dump(mode="json"),
                "submission_id": str(submission.id),
                "content_version": content_version,
                "command_time": now.isoformat(),
            },
        }
        session.flush()
    return record.result_ref
