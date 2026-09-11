"""Game administration and dual-axis, immutable scenario configuration."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, UniqueConstraint, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, Session, mapped_column

from living_memory.db import Base

IDENTIFIER = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")


class Controller(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    kind: Literal["human", "imported", "ai"]
    reference: str | None = None


class ActorConfiguration(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    id: str
    name: str = Field(min_length=1, max_length=200)


class TeamConfiguration(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    id: str
    name: str = Field(min_length=1, max_length=200)
    actor_ids: tuple[str, ...] = Field(min_length=1)
    controllers: tuple[Controller, ...] = Field(min_length=1)


class ResourceConfiguration(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    id: str
    name: str = Field(min_length=1, max_length=200)
    initial_values: dict[str, float]


class RelationshipEndpointConfiguration(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    entity_id: str
    role: str


class RelationshipConfiguration(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    id: str
    type: str
    endpoints: tuple[RelationshipEndpointConfiguration, ...] = Field(min_length=2)


class TurnConfiguration(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    number: int = Field(ge=1)
    simulated_duration_minutes: int = Field(gt=0)
    submission_deadline: datetime

    @model_validator(mode="after")
    def utc_deadline(self) -> TurnConfiguration:
        if (
            self.submission_deadline.tzinfo is None
            or self.submission_deadline.utcoffset() != UTC.utcoffset(None)
        ):
            raise ValueError("submission deadlines must be UTC")
        return self


class ScenarioConfiguration(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    teams: tuple[TeamConfiguration, ...] = Field(min_length=1)
    actors: tuple[ActorConfiguration, ...] = Field(min_length=1)
    rules: tuple[str, ...] = Field(min_length=1)
    objectives: dict[str, tuple[str, ...]]
    resources: tuple[ResourceConfiguration, ...] = ()
    relationships: tuple[RelationshipConfiguration, ...] = ()
    turns: tuple[TurnConfiguration, ...] = Field(min_length=1)
    submission_policy: Literal["simultaneous_joint_review"] = "simultaneous_joint_review"
    vocabulary: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_graph(self) -> ScenarioConfiguration:
        collections = (self.teams, self.actors, self.resources, self.relationships)
        all_ids: list[str] = []
        for values in collections:
            ids = [item.id for item in values]
            if len(ids) != len(set(ids)) or any(not IDENTIFIER.fullmatch(value) for value in ids):
                raise ValueError("configuration identifiers must be stable, valid, and unique")
            all_ids.extend(ids)
        if len(all_ids) != len(set(all_ids)):
            raise ValueError("configuration identifiers must be unique across entity types")
        team_ids, actor_ids = {item.id for item in self.teams}, {item.id for item in self.actors}
        if set(self.objectives) != team_ids:
            raise ValueError("objectives must cover every team exactly")
        represented: set[str] = set()
        for team in self.teams:
            if not set(team.actor_ids) <= actor_ids:
                raise ValueError("team references an unknown actor")
            represented.update(team.actor_ids)
            if any(
                controller.kind != "human" and not controller.reference
                for controller in team.controllers
            ):
                raise ValueError("imported and AI controllers require a reference")
        if represented != actor_ids:
            raise ValueError("every actor must be represented by a team")
        entity_ids = team_ids | actor_ids | {item.id for item in self.resources}
        for relationship in self.relationships:
            if any(endpoint.entity_id not in entity_ids for endpoint in relationship.endpoints):
                raise ValueError("relationship endpoint does not exist")
        for resource in self.resources:
            if set(resource.initial_values) != team_ids:
                raise ValueError("resource initial values must cover every team")
        expected_numbers = list(range(1, len(self.turns) + 1))
        if [turn.number for turn in self.turns] != expected_numbers:
            raise ValueError("turns must be ordered and contiguous")
        deadlines = [turn.submission_deadline for turn in self.turns]
        if deadlines != sorted(deadlines) or len(deadlines) != len(set(deadlines)):
            raise ValueError("turn deadlines must strictly increase")
        return self


class AdminGame(Base):
    __tablename__ = "admin_game"
    __table_args__ = (CheckConstraint("status IN ('draft', 'active', 'completed')", name="status"),)
    id: Mapped[str] = mapped_column(primary_key=True)
    title: Mapped[str]
    description: Mapped[str]
    public_rules: Mapped[str]
    public_briefing: Mapped[str]
    status: Mapped[str]
    root_branch_id: Mapped[str]
    current_turn: Mapped[int]
    adjudicator_scopes: Mapped[list[str]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ConfigurationRevision(Base):
    __tablename__ = "admin_configuration_revision"
    __table_args__ = (
        UniqueConstraint("game_id", "sequence"),
        UniqueConstraint("id", "game_id"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    game_id: Mapped[str] = mapped_column(ForeignKey("admin_game.id", ondelete="CASCADE"))
    sequence: Mapped[int]
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    effective_turn: Mapped[int]
    configuration: Mapped[dict[str, Any]] = mapped_column(JSONB)
    supersedes_revision_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("admin_configuration_revision.id")
    )
    author_user_id: Mapped[UUID] = mapped_column(ForeignKey("auth_user.id"))


class TeamOperationalState(Base):
    __tablename__ = "admin_team_state"
    game_id: Mapped[str] = mapped_column(
        ForeignKey("admin_game.id", ondelete="CASCADE"), primary_key=True
    )
    team_id: Mapped[str] = mapped_column(primary_key=True)
    blocked: Mapped[bool] = mapped_column(default=True)
    reason: Mapped[str]
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


def create_game(
    db_session: Session,
    game_id: str,
    title: str,
    configuration: ScenarioConfiguration,
    author: UUID,
    now: datetime,
    *,
    description: str = "",
    public_rules: str = "",
    public_briefing: str = "",
    root_branch_id: str = "main",
) -> AdminGame:
    validate_scope_names(configuration)
    if not IDENTIFIER.fullmatch(game_id) or not IDENTIFIER.fullmatch(root_branch_id):
        raise ValueError("game and root branch identifiers are invalid")
    game = AdminGame(
        id=game_id,
        title=title,
        description=description,
        public_rules=public_rules,
        public_briefing=public_briefing,
        status="draft",
        root_branch_id=root_branch_id,
        current_turn=0,
        adjudicator_scopes=[],
        created_at=now,
        updated_at=now,
    )
    db_session.add(game)
    db_session.flush()
    db_session.add(
        ConfigurationRevision(
            game_id=game_id,
            sequence=1,
            recorded_at=now,
            effective_turn=1,
            configuration=configuration.model_dump(mode="json"),
            supersedes_revision_id=None,
            author_user_id=author,
        )
    )
    db_session.add_all(
        TeamOperationalState(
            game_id=game_id,
            team_id=team.id,
            blocked=True,
            reason="No active submitter is assigned",
            updated_at=now,
        )
        for team in configuration.teams
    )
    from living_memory.identity import audit

    audit(db_session, author, game_id, "game_created", "game", game_id, now)
    return game


def revise_game(
    db_session: Session,
    game: AdminGame,
    configuration: ScenarioConfiguration,
    effective_turn: int,
    author: UUID,
    now: datetime,
) -> ConfigurationRevision:
    game = lock_game(db_session, game.id)
    if game.status == "completed":
        raise AdministrationConflict("Completed games cannot be revised")
    previous = governing_configuration(db_session, game, now)
    ensure_compatible(db_session, game, now)
    validate_scope_names(configuration)
    if roster(configuration) != roster(previous):
        raise AdministrationConflict("Roster and controller edits require a new game")
    if effective_turn < 1:
        raise ValueError("effective turn must be positive")
    if game.status == "draft" and effective_turn != 1:
        raise ValueError("draft-game revisions are immediately effective at turn 1")
    if game.status == "active" and effective_turn <= game.current_turn:
        raise ValueError("active-game revisions must target a future turn")
    known = list(
        db_session.scalars(
            select(ConfigurationRevision)
            .where(ConfigurationRevision.game_id == game.id)
            .order_by(ConfigurationRevision.sequence)
        )
    )
    if game.status == "active":
        governing = configuration_at(db_session, game.id, now, game.current_turn)
        previous = ScenarioConfiguration.model_validate(governing.configuration)
        started = game.current_turn
        if previous.turns[:started] != configuration.turns[:started]:
            raise ValueError("previously started turn definitions cannot be modified")
    supersedes = next(
        (revision for revision in reversed(known) if revision.effective_turn == effective_turn),
        None,
    )
    revision = ConfigurationRevision(
        id=uuid4(),
        game_id=game.id,
        sequence=(known[-1].sequence + 1) if known else 1,
        recorded_at=now,
        effective_turn=effective_turn,
        configuration=configuration.model_dump(mode="json"),
        supersedes_revision_id=supersedes.id if supersedes else None,
        author_user_id=author,
    )
    db_session.add(revision)
    game.updated_at = now
    from living_memory.identity import audit

    audit(
        db_session,
        author,
        game.id,
        "configuration_revised",
        "configuration_revision",
        str(revision.id),
        now,
        {"effective_turn": effective_turn},
    )
    reconcile_team_state(db_session, game, now)
    return revision


def configuration_at(
    db_session: Session, game_id: str, known_at: datetime, turn: int
) -> ConfigurationRevision:
    revision = db_session.scalars(
        select(ConfigurationRevision)
        .where(
            ConfigurationRevision.game_id == game_id,
            ConfigurationRevision.recorded_at <= known_at,
            ConfigurationRevision.effective_turn <= turn,
        )
        .order_by(
            ConfigurationRevision.effective_turn.desc(),
            ConfigurationRevision.sequence.desc(),
        )
        .limit(1)
    ).one_or_none()
    if revision is None:
        raise LookupError("no configuration was known at this turn")
    return revision


def scheduled_configurations(
    db_session: Session, game_id: str, known_at: datetime, after_turn: int
) -> tuple[ConfigurationRevision, ...]:
    rows = list(
        db_session.scalars(
            select(ConfigurationRevision)
            .where(
                ConfigurationRevision.game_id == game_id,
                ConfigurationRevision.recorded_at <= known_at,
                ConfigurationRevision.effective_turn > after_turn,
            )
            .order_by(ConfigurationRevision.effective_turn, ConfigurationRevision.sequence.desc())
        )
    )
    chosen: dict[int, ConfigurationRevision] = {}
    for row in rows:
        chosen.setdefault(row.effective_turn, row)
    return tuple(chosen[key] for key in sorted(chosen))


def activate_game(db_session: Session, game: AdminGame, author: UUID, now: datetime) -> AdminGame:
    from living_memory.identity import AuditEntry
    from living_memory.team_authority import active_submitter_teams, has_active_adjudicator

    game = lock_game(db_session, game.id)
    if game.status != "draft":
        raise AdministrationConflict("Only draft games can be activated")
    ensure_compatible(db_session, game, now)
    configuration = governing_configuration(db_session, game, now)
    if not has_active_adjudicator(db_session, game.id):
        raise ValueError("an active adjudicator is required")
    submitter_teams = active_submitter_teams(db_session, game.id, now)
    required = {team.id for team in configuration.teams}
    if not required <= submitter_teams:
        raise ValueError("every team requires an active submitter")
    game.status, game.current_turn, game.updated_at = "active", 1, now
    reconcile_team_state(db_session, game, now)
    from living_memory.memory import create_operational_dataset

    create_operational_dataset(
        db_session,
        game.id,
        game.root_branch_id,
        {team.id for team in configuration.teams},
        now,
    )
    db_session.add(
        AuditEntry(
            actor_user_id=author,
            game_id=game.id,
            action="game_activated",
            subject_type="game",
            subject_id=game.id,
            recorded_at=now,
            detail={},
        )
    )
    return game


Game = AdminGame


class AdministrationConflict(ValueError):
    """A valid request conflicts with the current administrative state."""


def lock_game(db_session: Session, game_id: str) -> AdminGame:
    game = db_session.get(AdminGame, game_id, with_for_update=True, populate_existing=True)
    if game is None:
        raise LookupError("Game not found")
    return game


def governing_configuration(
    db_session: Session, game: AdminGame, now: datetime
) -> ScenarioConfiguration:
    return ScenarioConfiguration.model_validate(
        configuration_at(db_session, game.id, now, max(1, game.current_turn)).configuration
    )


def validate_scope_names(configuration: ScenarioConfiguration) -> None:
    if any(team.id == "adjudicator" for team in configuration.teams):
        raise AdministrationConflict("Team ID adjudicator is reserved; create a compatible game")


def roster(configuration: ScenarioConfiguration) -> tuple[Any, ...]:
    return (
        tuple(sorted(actor.id for actor in configuration.actors)),
        tuple(
            sorted(
                (
                    team.id,
                    tuple(sorted(team.actor_ids)),
                    tuple(sorted((c.kind, c.reference or "") for c in team.controllers)),
                )
                for team in configuration.teams
            )
        ),
    )


def ensure_compatible(db_session: Session, game: AdminGame, now: datetime) -> None:
    current = governing_configuration(db_session, game, now)
    validate_scope_names(current)
    for revision in scheduled_configurations(db_session, game.id, now, max(1, game.current_turn)):
        if roster(ScenarioConfiguration.model_validate(revision.configuration)) != roster(current):
            raise AdministrationConflict("Scheduled roster changes require explicit remediation")


def reconcile_team_state(db_session: Session, game: AdminGame, now: datetime) -> None:
    from living_memory.identity import _alert_admins
    from living_memory.team_authority import active_submitter_teams, governing_team_ids

    configured = governing_team_ids(db_session, game.id, now)
    db_session.flush()
    submitters = active_submitter_teams(db_session, game.id, now)
    existing = {
        state.team_id: state
        for state in db_session.scalars(
            select(TeamOperationalState).where(TeamOperationalState.game_id == game.id)
        )
    }
    for team_id, obsolete in existing.items():
        if team_id not in configured:
            # Workspace objects retain a restrictive reference to this state.
            # Keep an explicit blocked tombstone rather than deleting it.
            obsolete.blocked, obsolete.reason, obsolete.updated_at = (
                True,
                "Team is not in the governing configuration",
                now,
            )
    for team_id in configured:
        state = existing.get(team_id)
        blocked = team_id not in submitters
        if state is None:
            state = TeamOperationalState(game_id=game.id, team_id=team_id, blocked=blocked)
            db_session.add(state)
        elif blocked and not state.blocked:
            _alert_admins(db_session, game.id, "team_blocked", team_id, now)
        state.blocked, state.reason, state.updated_at = (
            blocked,
            "No active submitter is assigned" if blocked else "",
            now,
        )
