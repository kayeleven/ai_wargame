"""Shared lock and retry vocabulary for changes affecting team authority."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session


class RetryableConflict(RuntimeError):
    """The authoritative lock set changed while acquiring it.

    Callers must discard the transaction and start again; continuing in the
    current transaction could make a user/game lock order inconsistent.
    """


def governing_team_ids(session: Session, game_id: str, now: datetime) -> frozenset[str]:
    """Return the teams in the configuration governing *now*.

    This is deliberately the single authority boundary for team membership:
    stale memberships never become permissions merely because their rows still
    exist after a configuration change.
    """
    from living_memory.administration import (
        AdminGame,
        governing_configuration,
        validate_scope_names,
    )

    game = session.get(AdminGame, game_id)
    if game is None:
        return frozenset()
    configuration = governing_configuration(session, game, now)
    validate_scope_names(configuration)
    return frozenset(team.id for team in configuration.teams)


def effective_memberships(
    session: Session, user_id: UUID, game_id: str, now: datetime
) -> frozenset[str]:
    """Return active, non-pending user's memberships in governing teams only."""
    from living_memory.identity import TeamMembership, User

    user = session.get(User, user_id)
    if user is None or not user.active or user.pending:
        return frozenset()
    teams = governing_team_ids(session, game_id, now)
    if not teams:
        return frozenset()
    return frozenset(
        session.scalars(
            select(TeamMembership.team_id).where(
                TeamMembership.user_id == user_id,
                TeamMembership.game_id == game_id,
                TeamMembership.team_id.in_(teams),
            )
        )
    )


def active_submitter_teams(session: Session, game_id: str, now: datetime) -> frozenset[str]:
    """Return governing teams with at least one active submitter."""
    from living_memory.identity import TeamMembership, User

    teams = governing_team_ids(session, game_id, now)
    if not teams:
        return frozenset()
    return frozenset(
        session.scalars(
            select(TeamMembership.team_id)
            .join(User, User.id == TeamMembership.user_id)
            .where(
                TeamMembership.game_id == game_id,
                TeamMembership.team_id.in_(teams),
                TeamMembership.authority == "submitter",
                User.active.is_(True),
                User.pending.is_(False),
            )
        )
    )


def has_active_adjudicator(session: Session, game_id: str) -> bool:
    """Whether a game has an account currently able to adjudicate."""
    from living_memory.identity import GameRole, User

    return (
        session.scalars(
            select(GameRole.user_id)
            .join(User, User.id == GameRole.user_id)
            .where(
                GameRole.game_id == game_id,
                GameRole.role == "adjudicator",
                User.active.is_(True),
                User.pending.is_(False),
            )
            .limit(1)
        ).first()
        is not None
    )
