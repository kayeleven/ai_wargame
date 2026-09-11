"""Phase 1D durable workspace aggregates and mutation services."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Text,
    UniqueConstraint,
    select,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, Session, mapped_column

from living_memory.db import Base


def canonical_fingerprint(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


class RequestKey(Base):
    __tablename__ = "ws_request_key"
    __table_args__ = (UniqueConstraint("game_id", "branch_id", "operation", "key"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    game_id: Mapped[str] = mapped_column(ForeignKey("admin_game.id", ondelete="CASCADE"))
    branch_id: Mapped[str]
    operation: Mapped[str]
    key: Mapped[UUID]
    fingerprint: Mapped[str]
    result_ref: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class IdempotencyConflict(ValueError):
    pass


class WorkspaceConflict(ValueError):
    pass


def claim_request_key(
    session: Session,
    *,
    game_id: str,
    branch_id: str,
    operation: str,
    key: UUID,
    fingerprint: str,
    result_ref: dict[str, Any],
    now: datetime,
) -> tuple[RequestKey, bool]:
    if set(result_ref) != {"kind", "id", "redirect"} or not all(result_ref.values()):
        raise ValueError("result_ref must contain kind, id, and redirect")
    row = RequestKey(
        game_id=game_id,
        branch_id=branch_id,
        operation=operation,
        key=key,
        fingerprint=fingerprint,
        result_ref=result_ref,
        created_at=now,
    )
    point = session.begin_nested()
    try:
        session.add(row)
        session.flush()
        point.commit()
        return row, False
    except IntegrityError:
        point.rollback()
    existing = session.scalars(
        select(RequestKey).where(
            RequestKey.game_id == game_id,
            RequestKey.branch_id == branch_id,
            RequestKey.operation == operation,
            RequestKey.key == key,
        )
    ).one()
    if existing.fingerprint != fingerprint:
        raise IdempotencyConflict("request key was already used with different content")
    return existing, True


class Draft(Base):
    __tablename__ = "ws_draft"
    __table_args__ = (
        UniqueConstraint("id", "game_id", "team_id"),
        ForeignKeyConstraint(
            ["game_id", "team_id"],
            ["admin_team_state.game_id", "admin_team_state.team_id"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint("game_id", "team_id", "turn"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    game_id: Mapped[str]
    team_id: Mapped[str]
    turn: Mapped[int]
    header: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    version: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class DraftAction(Base):
    __tablename__ = "ws_draft_action"
    __table_args__ = (
        UniqueConstraint("id", "game_id", "team_id"),
        ForeignKeyConstraint(
            ["draft_id", "game_id", "team_id"],
            ["ws_draft.id", "ws_draft.game_id", "ws_draft.team_id"],
            ondelete="CASCADE",
        ),
        CheckConstraint("origin IN ('manual', 'import')", name="origin"),
        CheckConstraint("version >= 0", name="version_nonnegative"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    draft_id: Mapped[UUID]
    game_id: Mapped[str]
    team_id: Mapped[str]
    action_id: Mapped[str]
    origin: Mapped[str] = mapped_column(default="manual")
    import_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("ws_import.id", deferrable=True, initially="DEFERRED")
    )
    body: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    version: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class DraftRevision(Base):
    __tablename__ = "ws_draft_revision"
    __table_args__ = (
        UniqueConstraint("draft_action_id", "version"),
        ForeignKeyConstraint(
            ["draft_action_id", "game_id", "team_id"],
            ["ws_draft_action.id", "ws_draft_action.game_id", "ws_draft_action.team_id"],
            ondelete="CASCADE",
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    draft_action_id: Mapped[UUID]
    game_id: Mapped[str]
    team_id: Mapped[str]
    version: Mapped[int]
    body: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    author_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("auth_user.id"))


class DraftComment(Base):
    __tablename__ = "ws_draft_comment"
    __table_args__ = (
        ForeignKeyConstraint(
            ["draft_action_id", "game_id", "team_id"],
            ["ws_draft_action.id", "ws_draft_action.game_id", "ws_draft_action.team_id"],
            ondelete="CASCADE",
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    draft_action_id: Mapped[UUID]
    game_id: Mapped[str]
    team_id: Mapped[str]
    author_user_id: Mapped[UUID] = mapped_column(ForeignKey("auth_user.id"))
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    retracted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Submission(Base):
    __tablename__ = "ws_submission"
    __table_args__ = (
        UniqueConstraint("id", "game_id", "team_id"),
        ForeignKeyConstraint(
            ["game_id", "team_id"],
            ["admin_team_state.game_id", "admin_team_state.team_id"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint("game_id", "team_id", "turn"),
        CheckConstraint(
            "status IN ('draft','submitted','amendment_pending','accepted','rejected')",
            name="status",
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    game_id: Mapped[str]
    team_id: Mapped[str]
    turn: Mapped[int]
    status: Mapped[str] = mapped_column(default="draft")
    version: Mapped[int] = mapped_column(default=0)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class SubmittedAction(Base):
    __tablename__ = "ws_submitted_action"
    __table_args__ = (
        UniqueConstraint("id", "game_id", "team_id"),
        ForeignKeyConstraint(
            ["submission_id", "game_id", "team_id"],
            ["ws_submission.id", "ws_submission.game_id", "ws_submission.team_id"],
            ondelete="CASCADE",
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    submission_id: Mapped[UUID]
    game_id: Mapped[str]
    team_id: Mapped[str]
    action_id: Mapped[str]
    body: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class SubmissionVersion(Base):
    __tablename__ = "ws_submission_version"
    __table_args__ = (
        UniqueConstraint("submission_id", "version"),
        ForeignKeyConstraint(
            ["submission_id", "game_id", "team_id"],
            ["ws_submission.id", "ws_submission.game_id", "ws_submission.team_id"],
            ondelete="CASCADE",
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    submission_id: Mapped[UUID]
    game_id: Mapped[str]
    team_id: Mapped[str]
    version: Mapped[int]
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    submitted_by: Mapped[UUID | None] = mapped_column(ForeignKey("auth_user.id"))


class Amendment(Base):
    __tablename__ = "ws_amendment"
    __table_args__ = (
        UniqueConstraint("submission_id", "version"),
        ForeignKeyConstraint(
            ["submission_id", "game_id", "team_id"],
            ["ws_submission.id", "ws_submission.game_id", "ws_submission.team_id"],
            ondelete="RESTRICT",
        ),
        CheckConstraint("status IN ('pending','accepted','rejected')", name="status"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    submission_id: Mapped[UUID]
    game_id: Mapped[str]
    team_id: Mapped[str]
    version: Mapped[int]
    body: Mapped[dict[str, Any]] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AmendmentDecision(Base):
    __tablename__ = "ws_amendment_decision"
    __table_args__ = (
        ForeignKeyConstraint(["amendment_id"], ["ws_amendment.id"], ondelete="RESTRICT"),
        CheckConstraint("decision IN ('accepted','rejected')", name="decision"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    amendment_id: Mapped[UUID]
    decision: Mapped[str]
    reason: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    adjudicator_user_id: Mapped[UUID] = mapped_column(ForeignKey("auth_user.id"))


class Coordination(Base):
    __tablename__ = "ws_coordination"
    __table_args__ = (
        UniqueConstraint("id", "game_id"),
        ForeignKeyConstraint(
            ["game_id", "proposing_team_id"],
            ["admin_team_state.game_id", "admin_team_state.team_id"],
            ondelete="RESTRICT",
        ),
        CheckConstraint("status IN ('proposed','active','withdrawn')", name="status"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    game_id: Mapped[str]
    proposing_team_id: Mapped[str]
    title: Mapped[str]
    terms: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(default="proposed")
    version: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class CoordinationParticipant(Base):
    __tablename__ = "ws_coordination_participant"
    __table_args__ = (
        ForeignKeyConstraint(
            ["coordination_id", "game_id"],
            ["ws_coordination.id", "ws_coordination.game_id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["game_id", "team_id"],
            ["admin_team_state.game_id", "admin_team_state.team_id"],
            ondelete="RESTRICT",
        ),
        CheckConstraint("status IN ('pending','consented','declined','withdrawn')", name="status"),
    )
    coordination_id: Mapped[UUID] = mapped_column(primary_key=True)
    game_id: Mapped[str] = mapped_column(primary_key=True)
    team_id: Mapped[str] = mapped_column(primary_key=True)
    status: Mapped[str] = mapped_column(default="pending")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class CoordinationLink(Base):
    __tablename__ = "ws_coordination_link"
    __table_args__ = (
        ForeignKeyConstraint(
            ["coordination_id", "game_id"],
            ["ws_coordination.id", "ws_coordination.game_id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["action_id", "game_id", "team_id"],
            [
                "ws_submitted_action.id",
                "ws_submitted_action.game_id",
                "ws_submitted_action.team_id",
            ],
            ondelete="RESTRICT",
        ),
    )
    coordination_id: Mapped[UUID] = mapped_column(primary_key=True)
    game_id: Mapped[str] = mapped_column(primary_key=True)
    team_id: Mapped[str] = mapped_column(primary_key=True)
    action_id: Mapped[UUID] = mapped_column(primary_key=True)


class Rfi(Base):
    __tablename__ = "ws_rfi"
    __table_args__ = (
        UniqueConstraint("id", "game_id", "team_id"),
        ForeignKeyConstraint(
            ["game_id", "team_id"],
            ["admin_team_state.game_id", "admin_team_state.team_id"],
            ondelete="RESTRICT",
        ),
        CheckConstraint("status IN ('open','withdrawn')", name="status"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    game_id: Mapped[str]
    team_id: Mapped[str]
    title: Mapped[str]
    type: Mapped[str]
    question: Mapped[str] = mapped_column(Text)
    recipient_role: Mapped[str] = mapped_column(default="adjudicator")
    visibility: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    status: Mapped[str] = mapped_column(default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RfiLink(Base):
    __tablename__ = "ws_rfi_link"
    __table_args__ = (
        ForeignKeyConstraint(
            ["rfi_id", "game_id", "team_id"],
            ["ws_rfi.id", "ws_rfi.game_id", "ws_rfi.team_id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["action_id", "game_id", "team_id"],
            [
                "ws_submitted_action.id",
                "ws_submitted_action.game_id",
                "ws_submitted_action.team_id",
            ],
            ondelete="RESTRICT",
        ),
    )
    rfi_id: Mapped[UUID] = mapped_column(primary_key=True)
    game_id: Mapped[str] = mapped_column(primary_key=True)
    team_id: Mapped[str] = mapped_column(primary_key=True)
    action_id: Mapped[UUID] = mapped_column(primary_key=True)


class WorkspaceImport(Base):
    __tablename__ = "ws_import"
    __table_args__ = (
        ForeignKeyConstraint(
            ["game_id", "team_id", "action_id"],
            ["ws_draft_action.game_id", "ws_draft_action.team_id", "ws_draft_action.id"],
            deferrable=True,
            initially="DEFERRED",
        ),
        CheckConstraint("format = 'labeled-text-v1'", name="format"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    game_id: Mapped[str]
    team_id: Mapped[str]
    action_id: Mapped[UUID | None]
    source_label: Mapped[str]
    format: Mapped[str] = mapped_column(default="labeled-text-v1")
    original_text: Mapped[str] = mapped_column(Text)
    original_sha256: Mapped[str]
    mapping: Mapped[dict[str, Any]] = mapped_column(JSONB)
    missing_fields: Mapped[list[Any]] = mapped_column(JSONB, default=list)
    missing_context: Mapped[list[Any]] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


# Public spelling used by the HTTP/API vocabulary; keep the original class for
# compatibility with the Phase 1C inventory code.
RFI = Rfi


def save_draft_action(
    session: Session,
    *,
    draft: Draft,
    action_id: UUID | None,
    action_key: str,
    body: dict[str, Any],
    expected_version: int | None,
    author: UUID | None,
    now: datetime,
) -> DraftAction:
    if action_id is None:
        if expected_version not in (None, 0):
            raise WorkspaceConflict("action does not exist at that version")
        action = DraftAction(
            draft_id=draft.id,
            game_id=draft.game_id,
            team_id=draft.team_id,
            action_id=action_key,
            body=body,
            version=1,
            created_at=now,
            updated_at=now,
        )
        session.add(action)
        session.flush()
    else:
        action = session.get(DraftAction, action_id, with_for_update=True)
        if action is None or action.draft_id != draft.id:
            raise LookupError("Draft action not found")
        if expected_version != action.version:
            raise WorkspaceConflict("stale draft action")
        action.body, action.version, action.updated_at = body, action.version + 1, now
    session.add(
        DraftRevision(
            draft_action_id=action.id,
            game_id=action.game_id,
            team_id=action.team_id,
            version=action.version,
            body=body,
            created_at=now,
            author_user_id=author,
        )
    )
    return action


def submit_draft(session: Session, *, draft: Draft, submitter: UUID, now: datetime) -> Submission:
    actions = list(
        session.scalars(
            select(DraftAction)
            .where(DraftAction.draft_id == draft.id)
            .order_by(DraftAction.created_at, DraftAction.id)
        )
    )
    snapshot = {
        "header": draft.header,
        "actions": [{"id": str(a.id), "action_id": a.action_id, "body": a.body} for a in actions],
    }
    submission = session.scalars(
        select(Submission)
        .where(
            Submission.game_id == draft.game_id,
            Submission.team_id == draft.team_id,
            Submission.turn == draft.turn,
        )
        .with_for_update()
    ).one_or_none()
    if submission is None:
        submission = Submission(
            game_id=draft.game_id,
            team_id=draft.team_id,
            turn=draft.turn,
            status="submitted",
            version=1,
            submitted_at=now,
            created_at=now,
            updated_at=now,
        )
        session.add(submission)
        session.flush()
    else:
        submission.version += 1
        submission.status = "amendment_pending"
        submission.updated_at = now
    session.add(
        SubmissionVersion(
            submission_id=submission.id,
            game_id=draft.game_id,
            team_id=draft.team_id,
            version=submission.version,
            snapshot=snapshot,
            created_at=now,
            submitted_by=submitter,
        )
    )
    if submission.version > 1:
        session.add(
            Amendment(
                submission_id=submission.id,
                game_id=draft.game_id,
                team_id=draft.team_id,
                version=submission.version,
                body=snapshot,
                created_at=now,
            )
        )
    else:
        for action in actions:
            session.add(
                SubmittedAction(
                    submission_id=submission.id,
                    game_id=draft.game_id,
                    team_id=draft.team_id,
                    action_id=action.action_id,
                    body=action.body,
                    created_at=now,
                )
            )
    return submission
