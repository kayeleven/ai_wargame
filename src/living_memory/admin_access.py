"""Transactional administrative authority and grant lifecycle services."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from living_memory.administration import (
    AdminGame,
    AdministrationConflict,
    governing_configuration,
    lock_game,
    reconcile_team_state,
    validate_scope_names,
)
from living_memory.identity import (
    ExternalIdentityBinding,
    GameRole,
    PendingAccessRequest,
    TeamMembership,
    User,
    audit,
    is_game_admin,
    is_system_admin,
    remove_membership,
)


def require_admin(session: Session, actor: UUID, game_id: str) -> AdminGame:
    game = lock_game(session, game_id)
    if not is_game_admin(session, actor, game_id):
        raise PermissionError("Game administration required")
    return game


def eligible_target(session: Session, actor: UUID, game_id: str, user_id: UUID) -> User:
    user = session.get(User, user_id)
    if user is None or not user.active or user.pending:
        raise ValueError("User is not eligible")
    if not is_system_admin(session, actor):
        participant = session.scalar(
            select(TeamMembership.user_id)
            .where(TeamMembership.game_id == game_id, TeamMembership.user_id == user_id)
            .limit(1)
        )
        role = session.scalar(
            select(GameRole.user_id)
            .where(GameRole.game_id == game_id, GameRole.user_id == user_id)
            .limit(1)
        )
        approved = session.scalar(
            select(PendingAccessRequest.id)
            .join(
                ExternalIdentityBinding,
                ExternalIdentityBinding.id == PendingAccessRequest.binding_id,
            )
            .where(
                PendingAccessRequest.game_id == game_id,
                PendingAccessRequest.status == "approved",
                ExternalIdentityBinding.user_id == user_id,
            )
            .limit(1)
        )
        if participant is None and role is None and approved is None:
            raise PermissionError("System administrator must place unrelated accounts")
    return user


def set_membership(
    session: Session,
    actor: UUID,
    game_id: str,
    user_id: UUID,
    team_id: str,
    authority: str,
    now: datetime,
    *,
    change: bool = False,
) -> None:
    game = require_admin(session, actor, game_id)
    eligible_target(session, actor, game_id, user_id)
    configuration = governing_configuration(session, game, now)
    validate_scope_names(configuration)
    if authority not in {"member", "submitter"} or team_id not in {
        team.id for team in configuration.teams
    }:
        raise ValueError("Unknown configured team or authority")
    row = session.get(TeamMembership, (user_id, game_id, team_id))
    if change:
        if row is None:
            raise LookupError("Membership not found")
        row.authority = authority
    else:
        if row is not None:
            raise AdministrationConflict("Membership already exists; use change authority")
        session.add(
            TeamMembership(
                user_id=user_id,
                game_id=game_id,
                team_id=team_id,
                authority=authority,
                granted_at=now,
                granted_by=actor,
            )
        )
    reconcile_team_state(session, game, now)
    audit(
        session,
        actor,
        game_id,
        "membership_changed" if change else "membership_granted",
        "team_membership",
        f"{user_id}:{team_id}",
        now,
        {"authority": authority},
    )


def delete_membership(
    session: Session, actor: UUID, game_id: str, user_id: UUID, team_id: str, now: datetime
) -> None:
    require_admin(session, actor, game_id)
    row = session.get(TeamMembership, (user_id, game_id, team_id))
    if row is None:
        raise LookupError("Membership not found")
    remove_membership(session, row, actor, now)


def set_role(
    session: Session,
    actor: UUID,
    game_id: str,
    user_id: UUID,
    role: str,
    now: datetime,
    *,
    remove: bool = False,
) -> None:
    game = require_admin(session, actor, game_id)
    if role not in {"game_admin", "adjudicator"}:
        raise ValueError("Invalid role")
    system = is_system_admin(session, actor)
    if role == "adjudicator" and not system:
        raise PermissionError("Only system administrators may manage adjudicators")
    row = session.get(GameRole, (user_id, game_id, role))
    if remove:
        if row is None:
            raise LookupError("Role not found")
        if role == "game_admin" and not system:
            other = session.scalar(
                select(GameRole.user_id)
                .join(User, User.id == GameRole.user_id)
                .where(
                    GameRole.game_id == game_id,
                    GameRole.role == role,
                    GameRole.user_id != user_id,
                    User.active.is_(True),
                    User.pending.is_(False),
                )
                .limit(1)
            )
            if other is None:
                raise AdministrationConflict("Cannot remove the last active game administrator")
        session.delete(row)
    else:
        eligible_target(session, actor, game_id, user_id)
        validate_scope_names(governing_configuration(session, game, now))
        if row is not None:
            raise AdministrationConflict("Role already assigned")
        session.add(
            GameRole(user_id=user_id, game_id=game_id, role=role, granted_at=now, granted_by=actor)
        )
    reconcile_team_state(session, game, now)
    audit(
        session,
        actor,
        game_id,
        "game_role_removed" if remove else "game_role_granted",
        "game_role",
        f"{user_id}:{role}",
        now,
    )


def review_access(
    session: Session,
    actor: UUID,
    request_id: UUID,
    approve: bool,
    now: datetime,
    *,
    team_id: str = "",
    authority: str = "member",
    role: str = "",
) -> None:
    pending = session.get(PendingAccessRequest, request_id)
    if pending is None:
        raise LookupError("Request not found")
    game = require_admin(session, actor, pending.game_id)
    pending = session.get(
        PendingAccessRequest, request_id, with_for_update=True, populate_existing=True
    )
    assert pending is not None
    if pending.status != "pending":
        raise AdministrationConflict("Only pending requests can be reviewed")
    binding = session.get(ExternalIdentityBinding, pending.binding_id)
    user = session.get(User, binding.user_id) if binding else None
    if user is None or not user.active or not user.pending:
        raise AdministrationConflict("Applicant is not pending and active")
    pending.status = "approved" if approve else "denied"
    pending.reviewed_at, pending.reviewed_by = now, actor
    if approve:
        validate_scope_names(governing_configuration(session, game, now))
        user.pending, user.updated_at = False, now
        session.flush()
        if team_id:
            set_membership(session, actor, game.id, user.id, team_id, authority, now)
        if role:
            set_role(session, actor, game.id, user.id, role, now)
    reconcile_team_state(session, game, now)
    audit(
        session,
        actor,
        game.id,
        "external_access_approved" if approve else "external_access_denied",
        "pending_access_request",
        str(pending.id),
        now,
        {"team_id": team_id or None, "authority": authority, "role": role or None},
    )
