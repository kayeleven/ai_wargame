"""Durable identities, authentication, authorization, and external-provider seam."""

from __future__ import annotations

import hashlib
import secrets
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Protocol
from uuid import UUID, uuid4

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    LargeBinary,
    UniqueConstraint,
    func,
    select,
    text,
    update,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, Session, mapped_column

from living_memory.db import Base
from living_memory.memory import Principal, VisibilityGrant


def normalize_username(value: str) -> str:
    """Normalize usernames for comparison without changing immutable user IDs."""
    normalized = unicodedata.normalize("NFKC", value).strip().casefold()
    if not normalized or len(normalized) > 120 or any(char.isspace() for char in normalized):
        raise ValueError("username must be 1-120 characters without whitespace")
    return normalized


class User(Base):
    __tablename__ = "auth_user"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    username: Mapped[str] = mapped_column(unique=True)
    display_name: Mapped[str]
    active: Mapped[bool] = mapped_column(default=True)
    pending: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    deactivated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class LocalCredential(Base):
    __tablename__ = "auth_local_credential"
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("auth_user.id", ondelete="CASCADE"), primary_key=True
    )
    password_hash: Mapped[str]
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AuthSession(Base):
    __tablename__ = "auth_session"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("auth_user.id", ondelete="CASCADE"))
    token_hash: Mapped[bytes] = mapped_column(LargeBinary(32), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    absolute_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revocation_reason: Mapped[str | None]


class LoginAttempt(Base):
    __tablename__ = "auth_login_attempt"
    __table_args__ = (
        Index("ix_auth_login_attempt_username_time", "username", "attempted_at"),
        Index("ix_auth_login_attempt_source_time", "source_hash", "attempted_at"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    username: Mapped[str]
    source_hash: Mapped[bytes] = mapped_column(LargeBinary(32))
    attempted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    succeeded: Mapped[bool]


class GlobalRole(Base):
    __tablename__ = "auth_global_role"
    __table_args__ = (CheckConstraint("role = 'system_admin'", name="role"),)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("auth_user.id", ondelete="CASCADE"), primary_key=True
    )
    role: Mapped[str] = mapped_column(primary_key=True)
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    granted_by: Mapped[UUID | None] = mapped_column(ForeignKey("auth_user.id"))


class GameRole(Base):
    __tablename__ = "auth_game_role"
    __table_args__ = (CheckConstraint("role IN ('game_admin', 'adjudicator')", name="role"),)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("auth_user.id", ondelete="CASCADE"), primary_key=True
    )
    game_id: Mapped[str] = mapped_column(
        ForeignKey("admin_game.id", ondelete="CASCADE"), primary_key=True
    )
    role: Mapped[str] = mapped_column(primary_key=True)
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    granted_by: Mapped[UUID | None] = mapped_column(ForeignKey("auth_user.id"))


class TeamMembership(Base):
    __tablename__ = "auth_team_membership"
    __table_args__ = (
        CheckConstraint("authority IN ('member', 'submitter')", name="authority"),
        Index(
            "uq_auth_team_submitter",
            "game_id",
            "team_id",
            unique=True,
            postgresql_where=text("authority = 'submitter'"),
        ),
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("auth_user.id", ondelete="CASCADE"), primary_key=True
    )
    game_id: Mapped[str] = mapped_column(
        ForeignKey("admin_game.id", ondelete="CASCADE"), primary_key=True
    )
    team_id: Mapped[str] = mapped_column(primary_key=True)
    authority: Mapped[str]
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    granted_by: Mapped[UUID | None] = mapped_column(ForeignKey("auth_user.id"))


class ProviderScope(Base):
    __tablename__ = "auth_provider_scope"
    __table_args__ = (UniqueConstraint("game_id", "provider"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    game_id: Mapped[str] = mapped_column(ForeignKey("admin_game.id", ondelete="CASCADE"))
    provider: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ExternalIdentityBinding(Base):
    __tablename__ = "auth_external_binding"
    __table_args__ = (UniqueConstraint("provider_scope_id", "provider_subject"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    provider_scope_id: Mapped[UUID] = mapped_column(
        ForeignKey("auth_provider_scope.id", ondelete="CASCADE")
    )
    provider_subject: Mapped[str]
    user_id: Mapped[UUID] = mapped_column(ForeignKey("auth_user.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class PendingAccessRequest(Base):
    __tablename__ = "auth_pending_access_request"
    __table_args__ = (UniqueConstraint("binding_id"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    binding_id: Mapped[UUID] = mapped_column(
        ForeignKey("auth_external_binding.id", ondelete="CASCADE")
    )
    game_id: Mapped[str] = mapped_column(ForeignKey("admin_game.id", ondelete="CASCADE"))
    display_attributes: Mapped[dict[str, Any]] = mapped_column(JSONB)
    observed_groups: Mapped[list[str]] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewed_by: Mapped[UUID | None] = mapped_column(ForeignKey("auth_user.id"))


class ProviderGroupMapping(Base):
    __tablename__ = "auth_provider_group_mapping"
    __table_args__ = (UniqueConstraint("provider_scope_id", "external_group"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    provider_scope_id: Mapped[UUID] = mapped_column(
        ForeignKey("auth_provider_scope.id", ondelete="CASCADE")
    )
    external_group: Mapped[str]
    suggested_team_id: Mapped[str | None]
    suggested_role: Mapped[str | None]


class AdministratorAlert(Base):
    __tablename__ = "admin_alert"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    recipient_user_id: Mapped[UUID] = mapped_column(ForeignKey("auth_user.id", ondelete="CASCADE"))
    game_id: Mapped[str | None] = mapped_column(ForeignKey("admin_game.id", ondelete="CASCADE"))
    kind: Mapped[str]
    subject_id: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuditEntry(Base):
    __tablename__ = "admin_audit_entry"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    actor_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("auth_user.id"))
    game_id: Mapped[str | None] = mapped_column(ForeignKey("admin_game.id", ondelete="SET NULL"))
    action: Mapped[str]
    subject_type: Mapped[str]
    subject_id: Mapped[str]
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    detail: Mapped[dict[str, Any]] = mapped_column(JSONB)


class AuthenticatedSubject(BaseModel):
    model_config = ConfigDict(frozen=True)
    provider_subject: str
    display_attributes: dict[str, str] = Field(default_factory=dict)
    external_group_ids: tuple[str, ...] = ()


class IdentityProvider(Protocol):
    name: str

    def authenticate(self, credentials: dict[str, str]) -> AuthenticatedSubject: ...


class FakeExternalProvider:
    name = "fake-external"

    def __init__(self, subjects: dict[str, AuthenticatedSubject]):
        self.subjects = subjects

    def authenticate(self, credentials: dict[str, str]) -> AuthenticatedSubject:
        key = credentials.get("subject", "")
        try:
            return self.subjects[key]
        except KeyError:
            raise PermissionError("authentication failed") from None


PASSWORD_HASHER = PasswordHasher(
    time_cost=3, memory_cost=65536, parallelism=4, hash_len=32, salt_len=16
)
_DUMMY_HASH = PASSWORD_HASHER.hash("living-memory-dummy-password")


def hash_password(password: str) -> str:
    if not password:
        raise ValueError("password cannot be empty")
    return PASSWORD_HASHER.hash(password)


def verify_password(stored: str, password: str) -> tuple[bool, str | None]:
    try:
        PASSWORD_HASHER.verify(stored, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False, None
    return True, hash_password(password) if PASSWORD_HASHER.check_needs_rehash(stored) else None


def create_local_user(
    db_session: Session,
    username: str,
    display_name: str,
    password: str,
    now: datetime,
    *,
    system_admin: bool = False,
    author: UUID | None = None,
) -> User:
    user = User(
        username=normalize_username(username),
        display_name=display_name.strip(),
        active=True,
        pending=False,
        created_at=now,
        updated_at=now,
        deactivated_at=None,
    )
    if not user.display_name:
        raise ValueError("display name cannot be empty")
    db_session.add(user)
    db_session.flush()
    db_session.add(
        LocalCredential(user_id=user.id, password_hash=hash_password(password), changed_at=now)
    )
    if system_admin:
        db_session.add(
            GlobalRole(
                user_id=user.id,
                role="system_admin",
                granted_at=now,
                granted_by=user.id,
            )
        )
    audit(
        db_session,
        author or user.id,
        None,
        "user_created",
        "user",
        str(user.id),
        now,
    )
    return user


def reset_password(
    db_session: Session,
    user: User,
    password: str,
    now: datetime,
    author: UUID | None = None,
) -> None:
    credential = db_session.get(LocalCredential, user.id)
    if credential is None:
        credential = LocalCredential(user_id=user.id, password_hash="", changed_at=now)
        db_session.add(credential)
    credential.password_hash, credential.changed_at = hash_password(password), now
    revoke_user_sessions(db_session, user.id, now, "password_reset")
    audit(db_session, author or user.id, None, "password_reset", "user", str(user.id), now)


def deactivate_user(
    db_session: Session, user_id: UUID | User, now: datetime, author: UUID | None = None
) -> None:
    from living_memory.administration import lock_game, reconcile_team_state
    from living_memory.team_authority import RetryableConflict

    # Accepting User remains a harmless compatibility shim for integrations
    # written before this operation became retry-safe.
    target_id = user_id.id if isinstance(user_id, User) else user_id

    # Discover games before taking the target lock.  Locks are always games
    # (sorted) then user; a changed discovery set retries the transaction.
    game_ids = sorted(
        set(
            db_session.scalars(
                select(TeamMembership.game_id)
                .where(TeamMembership.user_id == target_id)
                .union(select(GameRole.game_id).where(GameRole.user_id == target_id))
            )
        )
    )
    games = [lock_game(db_session, game_id) for game_id in game_ids]
    user = db_session.get(User, target_id, with_for_update=True, populate_existing=True)
    if user is None:
        raise LookupError("User not found")
    # A membership/role may have appeared after the initial discovery.  Do not
    # acquire a late game lock after the user lock: retry from a fresh tx.
    confirmed_game_ids = sorted(
        set(
            db_session.scalars(
                select(TeamMembership.game_id)
                .where(TeamMembership.user_id == target_id)
                .union(select(GameRole.game_id).where(GameRole.user_id == target_id))
            )
        )
    )
    if confirmed_game_ids != game_ids:
        raise RetryableConflict("affected games changed while deactivating user")
    user.active, user.deactivated_at, user.updated_at = False, now, now
    revoke_user_sessions(db_session, user.id, now, "account_deactivated")
    for game in games:
        reconcile_team_state(db_session, game, now)
    audit(db_session, author or user.id, None, "user_deactivated", "user", str(user.id), now)


def authenticate_local(
    db_session: Session,
    username: str,
    password: str,
    apparent_source: str,
    now: datetime,
    *,
    username_limit: int = 8,
    source_limit: int = 80,
    window: timedelta = timedelta(minutes=15),
) -> User:
    """Authenticate with generic failure and durable username/source throttling."""
    try:
        normalized = normalize_username(username)
    except ValueError:
        normalized = "<invalid>"
    source_hash = hashlib.sha256(apparent_source.encode()).digest()
    since = now - window
    username_failures = int(
        db_session.scalar(
            select(func.count())
            .select_from(LoginAttempt)
            .where(
                LoginAttempt.username == normalized,
                LoginAttempt.attempted_at >= since,
                LoginAttempt.succeeded.is_(False),
            )
        )
        or 0
    )
    source_failures = int(
        db_session.scalar(
            select(func.count())
            .select_from(LoginAttempt)
            .where(
                LoginAttempt.source_hash == source_hash,
                LoginAttempt.attempted_at >= since,
                LoginAttempt.succeeded.is_(False),
            )
        )
        or 0
    )
    user = db_session.scalars(select(User).where(User.username == normalized)).one_or_none()
    credential = db_session.get(LocalCredential, user.id) if user else None
    stored = credential.password_hash if credential else _DUMMY_HASH
    verified, upgraded = verify_password(stored, password)
    allowed = username_failures < username_limit and source_failures < source_limit
    succeeded = bool(allowed and verified and user and user.active and not user.pending)
    db_session.add(
        LoginAttempt(
            username=normalized,
            source_hash=source_hash,
            attempted_at=now,
            succeeded=succeeded,
        )
    )
    if not succeeded or user is None:
        raise PermissionError("Invalid username or password")
    if upgraded and credential:
        credential.password_hash, credential.changed_at = upgraded, now
    return user


class LocalPasswordProvider:
    """Local provider adapter; its immutable subject is the internal user UUID."""

    name = "local"

    def __init__(self, db_session: Session, now: datetime, apparent_source: str = "unknown"):
        self.db_session = db_session
        self.now = now
        self.apparent_source = apparent_source

    def authenticate(self, credentials: dict[str, str]) -> AuthenticatedSubject:
        user = authenticate_local(
            self.db_session,
            credentials.get("username", ""),
            credentials.get("password", ""),
            self.apparent_source,
            self.now,
        )
        return AuthenticatedSubject(
            provider_subject=str(user.id),
            display_attributes={"display_name": user.display_name},
        )


def _token_hash(token: str) -> bytes:
    return hashlib.sha256(token.encode()).digest()


@dataclass(frozen=True)
class SessionPolicy:
    idle: timedelta = timedelta(minutes=30)
    absolute: timedelta = timedelta(days=7)


DEFAULT_SESSION_POLICY = SessionPolicy()


def issue_session(
    db_session: Session,
    user_id: UUID,
    now: datetime,
    policy: SessionPolicy = DEFAULT_SESSION_POLICY,
) -> str:
    token = secrets.token_urlsafe(32)
    db_session.add(
        AuthSession(
            user_id=user_id,
            token_hash=_token_hash(token),
            created_at=now,
            last_seen_at=now,
            absolute_expires_at=now + policy.absolute,
            revoked_at=None,
            revocation_reason=None,
        )
    )
    return token


def resolve_session(
    db_session: Session,
    token: str,
    now: datetime,
    policy: SessionPolicy = DEFAULT_SESSION_POLICY,
) -> User | None:
    from living_memory.db import recovery_blocked

    if recovery_blocked(db_session):
        return None
    row = db_session.scalars(
        select(AuthSession).where(AuthSession.token_hash == _token_hash(token)).with_for_update()
    ).one_or_none()
    if row is None or row.revoked_at is not None:
        return None
    user = db_session.get(User, row.user_id)
    if (
        user is None
        or not user.active
        or now >= row.absolute_expires_at
        or now - row.last_seen_at >= policy.idle
    ):
        row.revoked_at, row.revocation_reason = now, "expired_or_inactive"
        return None
    row.last_seen_at = now
    return user


def revoke_user_sessions(db_session: Session, user_id: UUID, now: datetime, reason: str) -> None:
    db_session.execute(
        update(AuthSession)
        .where(AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None))
        .values(revoked_at=now, revocation_reason=reason)
    )


def rotate_session(
    db_session: Session,
    token: str | None,
    user_id: UUID,
    now: datetime,
    policy: SessionPolicy = DEFAULT_SESSION_POLICY,
) -> str:
    if token:
        db_session.execute(
            update(AuthSession)
            .where(AuthSession.token_hash == _token_hash(token), AuthSession.revoked_at.is_(None))
            .values(revoked_at=now, revocation_reason="rotated")
        )
    return issue_session(db_session, user_id, now, policy)


def revoke_all_sessions_after_restore(db_session: Session, now: datetime) -> int:
    count = int(
        db_session.scalar(
            select(func.count()).select_from(AuthSession).where(AuthSession.revoked_at.is_(None))
        )
        or 0
    )
    db_session.execute(
        update(AuthSession)
        .where(AuthSession.revoked_at.is_(None))
        .values(revoked_at=now, revocation_reason="database_restore")
    )
    audit(
        db_session,
        None,
        None,
        "recovery_sessions_revoked",
        "session_set",
        "all",
        now,
        {"count": count},
    )
    return count


def resolve_principal(db_session: Session, user: User, game_id: str, now: datetime) -> Principal:
    from living_memory.administration import AdminGame
    from living_memory.team_authority import effective_memberships, governing_team_ids

    empty = Principal(identity=str(user.id), grants=())
    if not user.active or user.pending:
        return empty
    game = db_session.get(AdminGame, game_id)
    if game is None:
        return empty
    try:
        team_ids = governing_team_ids(db_session, game_id, now)
    except (ValueError, LookupError):
        return empty
    scopes = set(effective_memberships(db_session, user.id, game_id, now))
    if db_session.get(
        GameRole, (user.id, game_id, "adjudicator"), populate_existing=True
    ) is not None:
        scopes.update(team_ids | {"adjudicator"})
    return Principal(
        identity=str(user.id),
        grants=tuple(
            VisibilityGrant(game_id=game_id, visibility_scope_id=scope) for scope in sorted(scopes)
        ),
    )


def is_system_admin(db_session: Session, user_id: UUID) -> bool:
    return (
        db_session.scalar(
            select(func.count()).select_from(GlobalRole).where(GlobalRole.user_id == user_id)
        )
        == 1
    )


def is_game_admin(db_session: Session, user_id: UUID, game_id: str) -> bool:
    return bool(
        is_system_admin(db_session, user_id)
        or db_session.scalar(
            select(func.count())
            .select_from(GameRole)
            .where(
                GameRole.user_id == user_id,
                GameRole.game_id == game_id,
                GameRole.role == "game_admin",
            )
        )
    )


def authenticate(provider: IdentityProvider, credentials: dict[str, str]) -> AuthenticatedSubject:
    return provider.authenticate(credentials)


def resolve_or_register_external_identity(
    db_session: Session,
    provider_scope: ProviderScope,
    subject: AuthenticatedSubject,
    now: datetime,
) -> User:
    binding = db_session.scalars(
        select(ExternalIdentityBinding).where(
            ExternalIdentityBinding.provider_scope_id == provider_scope.id,
            ExternalIdentityBinding.provider_subject == subject.provider_subject,
        )
    ).one_or_none()
    minimal_attributes = {
        key: value for key, value in subject.display_attributes.items() if key in {"display_name"}
    }
    if binding:
        user = db_session.get(User, binding.user_id)
        if user is None:
            raise RuntimeError("external identity binding has no user")
        request = db_session.scalars(
            select(PendingAccessRequest).where(PendingAccessRequest.binding_id == binding.id)
        ).one_or_none()
        if request and request.status == "pending":
            request.display_attributes = minimal_attributes
            request.observed_groups = sorted(set(subject.external_group_ids))
        return user
    display = subject.display_attributes.get("display_name", "External user")[:200]
    suffix = uuid4().hex
    user = User(
        username=f"external-{suffix}",
        display_name=display,
        active=True,
        pending=True,
        created_at=now,
        updated_at=now,
        deactivated_at=None,
    )
    db_session.add(user)
    db_session.flush()
    binding = ExternalIdentityBinding(
        provider_scope_id=provider_scope.id,
        provider_subject=subject.provider_subject,
        user_id=user.id,
        created_at=now,
    )
    db_session.add(binding)
    db_session.flush()
    request = PendingAccessRequest(
        id=uuid4(),
        binding_id=binding.id,
        game_id=provider_scope.game_id,
        display_attributes=minimal_attributes,
        observed_groups=sorted(set(subject.external_group_ids)),
        status="pending",
        created_at=now,
        reviewed_at=None,
        reviewed_by=None,
    )
    db_session.add(request)
    _alert_admins(db_session, provider_scope.game_id, "pending_access", str(request.id), now)
    audit(
        db_session,
        None,
        provider_scope.game_id,
        "external_access_requested",
        "pending_access_request",
        str(request.id),
        now,
    )
    return user


def _alert_admins(
    db_session: Session, game_id: str, kind: str, subject_id: str, now: datetime
) -> None:
    global_admins = select(GlobalRole.user_id)
    game_admins = select(GameRole.user_id).where(
        GameRole.game_id == game_id, GameRole.role == "game_admin"
    )
    recipients = set(db_session.scalars(global_admins)) | set(db_session.scalars(game_admins))
    active = set(
        db_session.scalars(select(User.id).where(User.id.in_(recipients), User.active.is_(True)))
    )
    db_session.add_all(
        AdministratorAlert(
            recipient_user_id=user_id,
            game_id=game_id,
            kind=kind,
            subject_id=subject_id,
            created_at=now,
            read_at=None,
        )
        for user_id in active
    )


def remove_membership(
    db_session: Session, membership: TeamMembership, actor: UUID, now: datetime
) -> None:
    from living_memory.administration import lock_game, reconcile_team_state

    game_id, team_id = membership.game_id, membership.team_id
    game = lock_game(db_session, game_id)
    if not is_game_admin(db_session, actor, game_id):
        raise PermissionError("Game administration required")
    db_session.delete(membership)
    reconcile_team_state(db_session, game, now)
    db_session.add(
        AuditEntry(
            actor_user_id=actor,
            game_id=game_id,
            action="membership_removed",
            subject_type="team_membership",
            subject_id=f"{membership.user_id}:{team_id}",
            recorded_at=now,
            detail={},
        )
    )


def audit(
    db_session: Session,
    actor_user_id: UUID | None,
    game_id: str | None,
    action: str,
    subject_type: str,
    subject_id: str,
    now: datetime,
    detail: dict[str, Any] | None = None,
) -> None:
    db_session.add(
        AuditEntry(
            actor_user_id=actor_user_id,
            game_id=game_id,
            action=action,
            subject_type=subject_type,
            subject_id=subject_id,
            recorded_at=now,
            detail=detail or {},
        )
    )
