"""Wrapper-owned workspace commands. Call mutations inside one transaction."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from living_memory.administration import AdminGame, governing_configuration, lock_game
from living_memory.identity import TeamMembership, User, resolve_principal
from living_memory.team_authority import effective_memberships
from living_memory.workspace import (
    Amendment,
    AmendmentDecision,
    Draft,
    DraftAction,
    DraftComment,
    DraftRevision,
    PackageRevision,
    Submission,
    SubmissionVersion,
    SubmittedAction,
    WorkspaceConflict,
    canonical_fingerprint,
    claim_request_key,
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
    action_id: UUID | None = None
    owner_user_id: UUID | None = None
    body: ActionText = Field(default_factory=ActionText)
    overall_intention: str = ""
    order: list[UUID] = Field(default_factory=list)
    comment: str = ""
    amendment_id: UUID | None = None
    decision: Literal["accepted", "rejected"] | None = None
    reason: str = ""


class Conflict(WorkspaceConflict):
    def __init__(self, base: Any, current: Any, submitted: Any):
        super().__init__("This workspace changed. Compare your input with the current version.")
        self.base, self.current, self.submitted = base, current, submitted


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
    member = session.get(TeamMembership, (user_id, game_id, team_id))
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
    now: datetime,
) -> dict[str, Any]:
    review = command.operation == "decide"
    game = authorize(session, user_id, game_id, team_id, now, review=review, write=True)
    # Administration also locks the game before changing memberships. Lock users in stable order.
    for uid in sorted({user_id} | ({command.owner_user_id} if command.owner_user_id else set())):
        session.get(User, uid, with_for_update=True, populate_existing=True)
    authorize(session, user_id, game_id, team_id, now, review=review)
    if command.operation in {"submit", "amend"}:
        require_submitter(session, user_id, game_id, team_id)
    if game.status != "active" or turn != game.current_turn:
        raise ValueError("Only the active current turn can be changed")
    draft = get_draft(session, game_id, team_id, turn)
    if draft is not None:
        session.refresh(draft, with_for_update=True)
    submission = get_submission(session, game_id, team_id, turn)
    if submission is not None:
        session.refresh(submission, with_for_update=True)
    current = package(session, draft)
    if command.action_id is not None and command.action_id not in {a.id for a in current.actions}:
        raise LookupError("Not found")
    amendment = None
    if review:
        amendment = session.get(Amendment, command.amendment_id) if command.amendment_id else None
        if amendment is None or submission is None or amendment.submission_id != submission.id:
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
    result_id = str(uuid4())
    result_kind = "amendment_decision" if review else "package_revision"
    redirect = (
        f"/{'adjudicate' if review else 'play'}?game_id={game_id}&team_id={team_id}&turn={turn}"
    )
    _, replay = claim_request_key(
        session,
        game_id=game_id,
        branch_id=game.root_branch_id,
        operation=command.operation,
        key=command.key,
        fingerprint=canonical_fingerprint(
            {
                "user": str(user_id),
                "team": team_id,
                "turn": turn,
                "command": command.model_dump(mode="json"),
            }
        ),
        result_ref={"kind": result_kind, "id": result_id, "redirect": redirect},
        now=now,
    )
    if replay:
        from living_memory.workspace import RequestKey

        record = session.scalar(
            select(RequestKey).where(
                RequestKey.game_id == game_id,
                RequestKey.branch_id == game.root_branch_id,
                RequestKey.operation == command.operation,
                RequestKey.key == command.key,
            )
        )
        assert record is not None
        return record.result_ref
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
            submission.effective_version = amendment.version
        submission.status, submission.updated_at = "submitted", now
        submission.version += 1
    else:
        version = draft.version if draft else 0
        if command.expected_version != version:
            base = (
                session.scalar(
                    select(PackageRevision).where(
                        PackageRevision.draft_id == draft.id,
                        PackageRevision.version == command.expected_version,
                    )
                )
                if draft
                else None
            )
            raise Conflict(
                base.snapshot if base else Package().model_dump(mode="json"),
                current.model_dump(mode="json"),
                command.model_dump(mode="json"),
            )
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
            if command.operation == "submit" and submission is not None:
                raise Conflict(
                    None,
                    {"effective_version": submission.effective_version},
                    command.model_dump(mode="json"),
                )
            if command.operation == "amend" and (
                submission is None
                or submission.status == "amendment_pending"
                or submission.effective_version != command.effective_version
            ):
                raise Conflict(
                    {"effective_version": command.effective_version},
                    {"effective_version": submission.effective_version if submission else None},
                    command.model_dump(mode="json"),
                )
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
    return {"kind": result_kind, "id": result_id, "redirect": redirect}
