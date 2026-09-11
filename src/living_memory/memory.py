"""Scenario-independent, authorized bitemporal memory core."""

import base64
import hashlib
import hmac
import json
import secrets
from collections import defaultdict
from datetime import datetime
from typing import Any
from uuid import UUID, uuid5

from pydantic import BaseModel, ConfigDict, Field, JsonValue
from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Identity,
    Index,
    UniqueConstraint,
    and_,
    cast,
    func,
    or_,
    select,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, synonym
from sqlalchemy.types import Text

from living_memory.clocks import GameTime
from living_memory.db import Base, Database, DevelopmentArtifact
from living_memory.seed import (
    DisclosureSource,
    DisclosureValue,
    PackageManifest,
    ReferenceDeclaration,
    SourcePackage,
    artifact_manifest,
    artifact_supersession,
)


class RebuildState(Base):
    __tablename__ = "memory_rebuild_state"
    __table_args__ = (CheckConstraint("status IN ('pending', 'loaded')", name="status"),)
    artifact_id: Mapped[UUID] = mapped_column(
        ForeignKey("development_artifact.id", ondelete="CASCADE"), primary_key=True
    )
    status: Mapped[str]
    detail: Mapped[str]


class Dataset(Base):
    __tablename__ = "memory_dataset"
    __table_args__ = (
        UniqueConstraint("id", "game_id", name="uq_memory_dataset_id_game"),
        UniqueConstraint("id", "game_id", "root_branch_id", name="uq_memory_dataset_root"),
    )
    id: Mapped[UUID] = mapped_column(
        ForeignKey("development_artifact.id", ondelete="CASCADE"), primary_key=True
    )
    package_id: Mapped[str]
    label: Mapped[str]
    game_id: Mapped[str]
    root_branch_id: Mapped[str]
    manifest: Mapped[dict[str, Any]] = mapped_column(JSONB)


Timeline = Dataset


class Game(Base):
    __tablename__ = "memory_game"
    dataset_id: Mapped[UUID] = mapped_column(primary_key=True)
    id: Mapped[str] = mapped_column(primary_key=True)
    __table_args__ = (
        ForeignKeyConstraint(
            ["dataset_id", "id"],
            ["memory_dataset.id", "memory_dataset.game_id"],
            ondelete="CASCADE",
        ),
    )


class Branch(Base):
    __tablename__ = "memory_branch"
    dataset_id: Mapped[UUID] = mapped_column(primary_key=True)
    game_id: Mapped[str] = mapped_column(primary_key=True)
    id: Mapped[str] = mapped_column(primary_key=True)
    parent_id: Mapped[str | None]
    __table_args__ = (
        ForeignKeyConstraint(
            ["dataset_id", "game_id"],
            ["memory_game.dataset_id", "memory_game.id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["dataset_id", "game_id", "parent_id"],
            ["memory_branch.dataset_id", "memory_branch.game_id", "memory_branch.id"],
        ),
    )


class VisibilityScope(Base):
    __tablename__ = "memory_visibility_scope"
    dataset_id: Mapped[UUID] = mapped_column(primary_key=True)
    game_id: Mapped[str] = mapped_column(primary_key=True)
    id: Mapped[str] = mapped_column(primary_key=True)
    label: Mapped[str]
    __table_args__ = (
        ForeignKeyConstraint(
            ["dataset_id", "game_id"],
            ["memory_game.dataset_id", "memory_game.id"],
            ondelete="CASCADE",
        ),
    )


class Record(Base):
    __tablename__ = "memory_record"
    __table_args__ = (
        ForeignKeyConstraint(
            ["dataset_id", "game_id", "branch_id"],
            ["memory_branch.dataset_id", "memory_branch.game_id", "memory_branch.id"],
            ondelete="CASCADE",
        ),
        UniqueConstraint("dataset_id", "external_id", name="uq_memory_record_external"),
        UniqueConstraint("id", "dataset_id", "game_id", "branch_id", name="uq_memory_record_owner"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True)
    dataset_id: Mapped[UUID]
    game_id: Mapped[str]
    branch_id: Mapped[str]
    external_id: Mapped[str]
    type_id: Mapped[str]


class Revision(Base):
    __tablename__ = "memory_record_revision"
    __table_args__ = (
        Index(
            "ix_memory_record_temporal", "dataset_id", "game_id", "branch_id", "recorded_at", "id"
        ),
        ForeignKeyConstraint(
            ["record_id", "dataset_id", "game_id", "branch_id"],
            [
                "memory_record.id",
                "memory_record.dataset_id",
                "memory_record.game_id",
                "memory_record.branch_id",
            ],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["supersedes_revision_id", "record_id"],
            ["memory_record_revision.id", "memory_record_revision.record_id"],
        ),
        CheckConstraint("valid_to IS NULL OR valid_from < valid_to", name="valid_interval"),
        UniqueConstraint("dataset_id", "external_id", name="uq_memory_record_revision_external"),
        UniqueConstraint("id", "record_id", name="uq_memory_record_revision_identity"),
        UniqueConstraint("id", "dataset_id", "game_id", name="uq_memory_record_revision_owner"),
        UniqueConstraint(
            "dataset_id", "ingestion_order", name="uq_memory_record_revision_ingestion"
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True)
    record_id: Mapped[UUID]
    dataset_id: Mapped[UUID]
    game_id: Mapped[str]
    branch_id: Mapped[str]
    external_id: Mapped[str]
    ingestion_order: Mapped[int] = mapped_column(BigInteger, Identity())
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    valid_from: Mapped[int] = mapped_column(BigInteger)
    valid_to: Mapped[int | None] = mapped_column(BigInteger)
    supersedes_revision_id: Mapped[UUID | None]
    body: Mapped[dict[str, Any]] = mapped_column(JSONB)
    revision_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB)
    source_id = synonym("external_id")

    @property
    def content(self) -> dict[str, Any]:
        return {**self.revision_metadata, "body": self.body}


class Disclosure(Base):
    __tablename__ = "memory_record_disclosure"
    revision_id: Mapped[UUID] = mapped_column(primary_key=True)
    dataset_id: Mapped[UUID]
    game_id: Mapped[str]
    scope_id: Mapped[str] = mapped_column(primary_key=True)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        ForeignKeyConstraint(
            ["dataset_id", "game_id", "scope_id"],
            [
                "memory_visibility_scope.dataset_id",
                "memory_visibility_scope.game_id",
                "memory_visibility_scope.id",
            ],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["revision_id", "dataset_id", "game_id"],
            [
                "memory_record_revision.id",
                "memory_record_revision.dataset_id",
                "memory_record_revision.game_id",
            ],
            ondelete="CASCADE",
        ),
    )

    @property
    def audience(self) -> str:
        return self.scope_id


class DeclaredReference(Base):
    __tablename__ = "memory_declared_reference"
    __table_args__ = (
        CheckConstraint("target_kind IN ('record', 'action', 'external')", name="target_kind"),
        UniqueConstraint(
            "revision_id",
            "purpose",
            "target_kind",
            "target_id",
            "json_pointer",
            name="uq_memory_declared_reference",
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True)
    revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("memory_record_revision.id", ondelete="CASCADE")
    )
    purpose: Mapped[str]
    target_kind: Mapped[str]
    target_id: Mapped[str]
    json_pointer: Mapped[str | None]


class Relationship(Base):
    __tablename__ = "memory_relationship"
    __table_args__ = (
        ForeignKeyConstraint(
            ["dataset_id", "game_id", "branch_id"],
            ["memory_branch.dataset_id", "memory_branch.game_id", "memory_branch.id"],
            ondelete="CASCADE",
        ),
        UniqueConstraint("dataset_id", "external_id", name="uq_memory_relationship_external"),
        UniqueConstraint(
            "id", "dataset_id", "game_id", "branch_id", name="uq_memory_relationship_owner"
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True)
    dataset_id: Mapped[UUID]
    game_id: Mapped[str]
    branch_id: Mapped[str]
    external_id: Mapped[str]
    type_id: Mapped[str]


class RelationshipRevision(Base):
    __tablename__ = "memory_relationship_revision"
    __table_args__ = (
        ForeignKeyConstraint(
            ["relationship_id", "dataset_id", "game_id", "branch_id"],
            [
                "memory_relationship.id",
                "memory_relationship.dataset_id",
                "memory_relationship.game_id",
                "memory_relationship.branch_id",
            ],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["supersedes_revision_id", "relationship_id"],
            ["memory_relationship_revision.id", "memory_relationship_revision.relationship_id"],
        ),
        CheckConstraint("valid_to IS NULL OR valid_from < valid_to", name="valid_interval"),
        UniqueConstraint(
            "dataset_id", "external_id", name="uq_memory_relationship_revision_external"
        ),
        UniqueConstraint("id", "relationship_id", name="uq_memory_relationship_revision_identity"),
        UniqueConstraint(
            "id", "dataset_id", "game_id", name="uq_memory_relationship_revision_owner"
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True)
    relationship_id: Mapped[UUID]
    dataset_id: Mapped[UUID]
    game_id: Mapped[str]
    branch_id: Mapped[str]
    external_id: Mapped[str]
    ingestion_order: Mapped[int] = mapped_column(BigInteger, Identity())
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    valid_from: Mapped[int] = mapped_column(BigInteger)
    valid_to: Mapped[int | None] = mapped_column(BigInteger)
    supersedes_revision_id: Mapped[UUID | None]
    body: Mapped[dict[str, Any]] = mapped_column(JSONB)


class RelationshipDisclosure(Base):
    __tablename__ = "memory_relationship_disclosure"
    revision_id: Mapped[UUID] = mapped_column(primary_key=True)
    dataset_id: Mapped[UUID]
    game_id: Mapped[str]
    scope_id: Mapped[str] = mapped_column(primary_key=True)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        ForeignKeyConstraint(
            ["dataset_id", "game_id", "scope_id"],
            [
                "memory_visibility_scope.dataset_id",
                "memory_visibility_scope.game_id",
                "memory_visibility_scope.id",
            ],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["revision_id", "dataset_id", "game_id"],
            [
                "memory_relationship_revision.id",
                "memory_relationship_revision.dataset_id",
                "memory_relationship_revision.game_id",
            ],
            ondelete="CASCADE",
        ),
    )


class RelationshipEndpoint(Base):
    __tablename__ = "memory_relationship_endpoint"
    revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("memory_relationship_revision.id", ondelete="CASCADE"), primary_key=True
    )
    position: Mapped[int] = mapped_column(primary_key=True)
    role_id: Mapped[str]
    target_kind: Mapped[str]
    target_id: Mapped[str]
    __table_args__ = (
        CheckConstraint("position >= 0", name="position"),
        CheckConstraint("target_kind IN ('record', 'action', 'external')", name="target_kind"),
    )


class ReadModel(BaseModel):
    model_config = ConfigDict(frozen=True)


class VisibilityGrant(ReadModel):
    game_id: str
    visibility_scope_id: str


class Principal(ReadModel):
    identity: str
    grants: tuple[VisibilityGrant, ...]

    def permits(self, game_id: str, scope_id: str) -> bool:
        return VisibilityGrant(game_id=game_id, visibility_scope_id=scope_id) in self.grants

    @property
    def audiences(self) -> tuple[str, ...]:
        return tuple(grant.visibility_scope_id for grant in self.grants)

    @property
    def game_id(self) -> str:
        games = {grant.game_id for grant in self.grants}
        if len(games) != 1:
            raise ValueError("principal has grants in multiple games")
        return next(iter(games))


class BranchLineage(ReadModel):
    root: str


class MemoryQuery(ReadModel):
    dataset_id: UUID
    record_id: str | None = None
    revision_id: UUID | None = None
    text: str | None = None
    record_types: tuple[str, ...] = ()
    relationship_types: tuple[str, ...] = ()
    relationship_role: str | None = None
    related_target_id: str | None = None
    limit: int = Field(default=50, ge=1, le=100)
    cursor: str | None = None


class FieldView(ReadModel):
    label: str
    text: str


class ActionView(ReadModel):
    id: str
    title: str
    description: str
    intention: str
    anticipated_reaction: str


class ReferenceView(ReadModel):
    purpose: str
    target_kind: str
    target_id: str
    json_pointer: str | None


class EndpointView(ReadModel):
    position: int
    role: str
    target_kind: str
    target_id: str


class RelationshipSummary(ReadModel):
    id: str
    revision_id: UUID
    type: str
    revision_status: str
    effective_status: str
    endpoints: tuple[EndpointView, ...]


class RecordSummary(ReadModel):
    id: str
    stable_id: str
    revision_id: UUID
    title: str
    overall_intention: str | None
    actions: tuple[ActionView, ...]
    kind: str
    recorded_at: datetime
    effective_turn: int | None
    valid_from: int
    valid_to: int | None
    status: str
    revision_status: str
    effective_status: str
    temporal_status: str
    visibility_label: str
    source_refs: tuple[str, ...]
    references: tuple[ReferenceView, ...]
    relationships: tuple[RelationshipSummary, ...]
    fields: tuple[FieldView, ...]


class RecordView(RecordSummary):
    body: dict[str, JsonValue]


class ScopeMetadata(ReadModel):
    id: str
    label: str


class IngestionWatermark(ReadModel):
    records: int
    relationships: int


class MemoryView(ReadModel):
    records: tuple[RecordView, ...]
    audience: str
    scope: ScopeMetadata
    known_at: datetime
    effective_at: GameTime
    authorized_result_count: int
    next_cursor: str | None
    ingestion_watermark: IngestionWatermark


def _disclosure_times(value: DisclosureValue) -> tuple[datetime, datetime]:
    if isinstance(value, DisclosureSource):
        return value.available_at, value.recorded_at
    return value, value


def _parent_id(record: Any) -> str | None:
    value = record.supersedes
    return value if isinstance(value, str) else None


def _turn_boundaries(records: list[Any]) -> dict[int, int]:
    turns = next((r.body.get("turns") for r in records if r.body.get("turns")), None)
    if not turns:
        return {}
    result: dict[int, int] = {}
    elapsed = 0
    for turn in turns:
        result[int(turn["number"])] = elapsed
        elapsed += int(turn["simulated_days"]) * 86_400_000_000
    return result


def _validate_graph(
    records: list[Any], manifest: PackageManifest
) -> tuple[dict[str, str], set[str]]:
    by_id = {record.id: record for record in records}
    actions = {
        action["action_id"] for record in records for action in record.body.get("actions", [])
    }
    stable: dict[str, str] = {}
    for original in by_id:
        current, seen = original, set()
        while (prior := _parent_id(by_id[current])) is not None:
            if current in seen or prior not in by_id:
                raise ValueError("Invalid supersession chain")
            seen.add(current)
            current = prior
        stable[original] = by_id[original].stable_id or current
    declarations = {
        record.id: [
            *(
                ReferenceDeclaration(purpose="evidence", target_id=value)
                for value in record.source_refs
            ),
            *record.references,
            *manifest.references.get(record.id, []),
        ]
        for record in records
    }
    for refs in declarations.values():
        for ref in refs:
            record_targets = set(by_id) | set(stable.values())
            valid = ref.target_kind == "external" or ref.target_id in (
                actions if ref.target_kind == "action" else record_targets
            )
            if not valid:
                raise ValueError("Unresolved declared reference")
    edges = {
        source: [r.target_id for r in refs if r.target_kind == "record"]
        for source, refs in declarations.items()
    }

    def visit(node: str, path: set[str], done: set[str]) -> None:
        if node in path:
            raise ValueError("Declared reference graph contains a cycle")
        if node in done:
            return
        path.add(node)
        for target in edges[node]:
            if target in edges:
                visit(target, path, done)
        path.remove(node)
        done.add(node)

    done: set[str] = set()
    for node in edges:
        visit(node, set(), done)
    return stable, actions


def load_timeline(db: Database, checksum: str) -> bool:
    """Atomically rebuild a staged package through the shared validated repository path."""
    with db.transaction() as session:
        artifact = session.scalars(
            select(DevelopmentArtifact).where(DevelopmentArtifact.checksum == checksum)
        ).one()
        records_raw = artifact.contents.get("_records.json", artifact.contents.get("source.json"))
        if not isinstance(records_raw, str):
            raise ValueError("staged package has no normalized record source")
        package = SourcePackage.model_validate_json(records_raw)
        manifest = artifact_manifest(artifact.package, package, artifact.contents)
        records = [
            record.model_copy(
                update={"supersedes": artifact_supersession(artifact.package, record)}
            )
            for record in package.records
        ]
        if any(
            r.game_id != manifest.game_id or r.branch_id != manifest.root_branch_id for r in records
        ):
            raise ValueError("package records must belong to its game and root branch")
        if session.get(Dataset, artifact.id) is not None:
            return False
        stable, actions = _validate_graph(records, manifest)
        scopes = {scope.id for scope in manifest.visibility_scopes}
        record_types = {item.id for item in manifest.record_types}
        relationship_types = {item.id for item in manifest.relationship_types}
        relationship_roles = {item.id for item in manifest.relationship_roles}
        if record_types and any(record.kind not in record_types for record in records):
            raise ValueError("record uses an undeclared type")
        if any(set(r.disclosures) - scopes for r in records):
            raise ValueError("record disclosure uses an undeclared scope")
        boundaries = _turn_boundaries(records)
        session.add(
            Dataset(
                id=artifact.id,
                package_id=manifest.package_id,
                label=manifest.label,
                game_id=manifest.game_id,
                root_branch_id=manifest.root_branch_id,
                manifest=manifest.model_dump(mode="json"),
            )
        )
        session.flush()
        session.add(Game(dataset_id=artifact.id, id=manifest.game_id))
        session.flush()
        session.add(
            Branch(
                dataset_id=artifact.id,
                game_id=manifest.game_id,
                id=manifest.root_branch_id,
                parent_id=None,
            )
        )
        session.add_all(
            VisibilityScope(
                dataset_id=artifact.id, game_id=manifest.game_id, id=scope.id, label=scope.label
            )
            for scope in manifest.visibility_scopes
        )
        session.flush()
        stable_ids = sorted(set(stable.values()))
        first_for_stable = {
            value: next(r for r in records if stable[r.id] == value) for value in stable_ids
        }
        for external in stable_ids:
            first = first_for_stable[external]
            session.add(
                Record(
                    id=uuid5(artifact.id, "record:" + external),
                    dataset_id=artifact.id,
                    game_id=manifest.game_id,
                    branch_id=manifest.root_branch_id,
                    external_id=external,
                    type_id=first.kind,
                )
            )
        session.flush()
        for record in records:
            if record.kind == "import":
                name = record.body.get("artifact")
                if not isinstance(name, str) or record.body.get(
                    "original_text"
                ) != artifact.contents.get(name):
                    raise ValueError("import source text must match its staged artifact")
            parent = _parent_id(record)
            if record.valid_from is not None:
                valid_from = record.valid_from
            elif record.effective_turn is not None:
                valid_from = boundaries[record.effective_turn]
            else:
                raise ValueError("record has no effective boundary")
            revision_id = uuid5(artifact.id, "revision:" + record.id)
            session.add(
                Revision(
                    id=revision_id,
                    record_id=uuid5(artifact.id, "record:" + stable[record.id]),
                    dataset_id=artifact.id,
                    game_id=manifest.game_id,
                    branch_id=manifest.root_branch_id,
                    external_id=record.id,
                    recorded_at=record.recorded_at,
                    valid_from=valid_from,
                    valid_to=record.valid_to,
                    supersedes_revision_id=uuid5(artifact.id, "revision:" + parent)
                    if parent
                    else None,
                    body=record.body,
                    revision_metadata={"effective_turn": record.effective_turn},
                )
            )
        session.flush()
        for record in records:
            revision_id = uuid5(artifact.id, "revision:" + record.id)
            for scope, disclosure in record.disclosures.items():
                available, recorded = _disclosure_times(disclosure)
                session.add(
                    Disclosure(
                        revision_id=revision_id,
                        dataset_id=artifact.id,
                        game_id=manifest.game_id,
                        scope_id=scope,
                        available_at=available,
                        recorded_at=recorded,
                    )
                )
            declarations = [
                *(
                    ReferenceDeclaration(purpose="evidence", target_id=value)
                    for value in record.source_refs
                ),
                *record.references,
                *manifest.references.get(record.id, []),
            ]
            for position, ref in enumerate(declarations):
                session.add(
                    DeclaredReference(
                        id=uuid5(revision_id, f"reference:{position}"),
                        revision_id=revision_id,
                        **ref.model_dump(),
                    )
                )
        relationship_ids = {item.stable_id for item in manifest.relationships}
        for stable_id in relationship_ids:
            first_relationship = next(
                item for item in manifest.relationships if item.stable_id == stable_id
            )
            session.add(
                Relationship(
                    id=uuid5(artifact.id, "relationship:" + stable_id),
                    dataset_id=artifact.id,
                    game_id=manifest.game_id,
                    branch_id=manifest.root_branch_id,
                    external_id=stable_id,
                    type_id=first_relationship.type,
                )
            )
        session.flush()
        relationship_revisions = {item.id: item for item in manifest.relationships}
        for item in manifest.relationships:
            if item.type not in relationship_types:
                raise ValueError("relationship uses an undeclared type")
            if any(endpoint.role not in relationship_roles for endpoint in item.endpoints):
                raise ValueError("relationship endpoint uses an undeclared role")
            if set(item.disclosures) - scopes:
                raise ValueError("relationship disclosure uses an undeclared scope")
            if item.valid_to is not None and item.valid_from >= item.valid_to:
                raise ValueError("relationship validity interval must be nonempty")
            prior, seen = item.supersedes, {item.id}
            while prior:
                if prior in seen or prior not in relationship_revisions:
                    raise ValueError("invalid relationship supersession")
                seen.add(prior)
                previous = relationship_revisions[prior]
                if previous.stable_id != item.stable_id:
                    raise ValueError("invalid relationship supersession")
                prior = previous.supersedes
            for endpoint in item.endpoints:
                known = endpoint.target_kind == "external" or endpoint.target_id in (
                    actions
                    if endpoint.target_kind == "action"
                    else ({r.id for r in records} | set(stable.values()))
                )
                if not known:
                    raise ValueError("unresolved relationship endpoint")
            revision_id = uuid5(artifact.id, "relationship-revision:" + item.id)
            session.add(
                RelationshipRevision(
                    id=revision_id,
                    relationship_id=uuid5(artifact.id, "relationship:" + item.stable_id),
                    dataset_id=artifact.id,
                    game_id=manifest.game_id,
                    branch_id=manifest.root_branch_id,
                    external_id=item.id,
                    recorded_at=item.recorded_at,
                    valid_from=item.valid_from,
                    valid_to=item.valid_to,
                    supersedes_revision_id=uuid5(
                        artifact.id, "relationship-revision:" + item.supersedes
                    )
                    if item.supersedes
                    else None,
                    body=item.body,
                )
            )
            session.flush()
            for scope, disclosure in item.disclosures.items():
                available, recorded = _disclosure_times(disclosure)
                session.add(
                    RelationshipDisclosure(
                        revision_id=revision_id,
                        dataset_id=artifact.id,
                        game_id=manifest.game_id,
                        scope_id=scope,
                        available_at=available,
                        recorded_at=recorded,
                    )
                )
            session.add_all(
                RelationshipEndpoint(
                    revision_id=revision_id,
                    position=position,
                    role_id=endpoint.role,
                    target_kind=endpoint.target_kind,
                    target_id=endpoint.target_id,
                )
                for position, endpoint in enumerate(item.endpoints)
            )
        state = session.get(RebuildState, artifact.id)
        if state:
            state.status, state.detail = (
                "loaded",
                "Rebuilt atomically from preserved source package",
            )
        else:
            session.add(
                RebuildState(
                    artifact_id=artifact.id,
                    status="loaded",
                    detail="Loaded atomically from preserved source package",
                )
            )
    return True


def fields(value: JsonValue, prefix: str = "") -> list[FieldView]:
    if isinstance(value, dict):
        return [
            field
            for key, child in value.items()
            for field in fields(child, f"{prefix} / {key}" if prefix else key)
        ]
    if isinstance(value, list):
        return [
            field
            for index, child in enumerate(value)
            for field in fields(child, f"{prefix} {index + 1}")
        ]
    return [
        FieldView(
            label=prefix.replace("_", " ").capitalize(),
            text=str(value) if value is not None else "Unspecified",
        )
    ]


def _remove_pointer(body: dict[str, Any], pointer: str) -> None:
    if not pointer.startswith("/"):
        return
    parts = [part.replace("~1", "/").replace("~0", "~") for part in pointer[1:].split("/")]
    current: Any = body
    for part in parts[:-1]:
        if isinstance(current, dict):
            current = current.get(part)
        elif isinstance(current, list) and part.isdigit() and int(part) < len(current):
            current = current[int(part)]
        else:
            return
    if isinstance(current, dict):
        current.pop(parts[-1], None)
    elif isinstance(current, list) and parts[-1].isdigit() and int(parts[-1]) < len(current):
        current.pop(int(parts[-1]))


class MemoryReader:
    def __init__(self, db: Database, cursor_secret: bytes | None = None):
        self.db = db
        self.cursor_secret = cursor_secret or secrets.token_bytes(32)

    def lineage(self, dataset_id: UUID, game_id: str) -> BranchLineage:
        with self.db.transaction() as session:
            dataset = session.get(Dataset, dataset_id)
            if dataset is None or dataset.game_id != game_id:
                raise LookupError("Not found")
            return BranchLineage(root=dataset.root_branch_id)

    def _filter_hash(self, query: MemoryQuery) -> str:
        value = query.model_dump(mode="json", exclude={"cursor", "limit"})
        return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()

    def _encode_cursor(self, payload: dict[str, Any]) -> str:
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        signature = hmac.new(self.cursor_secret, raw, hashlib.sha256).digest()
        return base64.urlsafe_b64encode(raw + signature).decode().rstrip("=")

    def _decode_cursor(self, token: str) -> dict[str, Any]:
        try:
            packed = base64.urlsafe_b64decode(token + "=" * (-len(token) % 4))
            raw, signature = packed[:-32], packed[-32:]
            if not hmac.compare_digest(
                signature, hmac.new(self.cursor_secret, raw, hashlib.sha256).digest()
            ):
                raise ValueError
            value = json.loads(raw)
            if not isinstance(value, dict):
                raise ValueError
            return value
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            raise ValueError("Invalid memory cursor") from exc

    def read_memory(
        self,
        principal: Principal,
        game_id: str,
        audience: str,
        branch_lineage: BranchLineage,
        known_at: datetime,
        effective_at: GameTime,
        query: MemoryQuery,
    ) -> MemoryView:
        if not principal.permits(game_id, audience):
            raise PermissionError("Visibility scope not permitted")
        if known_at.tzinfo is None:
            raise ValueError("Knowledge cutoff must include timezone")
        context = {
            "game": game_id,
            "branch": branch_lineage.root,
            "scope": audience,
            "known": known_at.isoformat(),
            "effective": effective_at.elapsed_microseconds,
            "filter": self._filter_hash(query),
        }
        cursor = self._decode_cursor(query.cursor) if query.cursor else None
        if cursor and any(cursor.get(key) != value for key, value in context.items()):
            raise ValueError("Memory cursor does not match this request")
        with self.db.transaction() as session:
            dataset = session.scalar(
                select(Dataset).where(
                    Dataset.id == query.dataset_id,
                    Dataset.game_id == game_id,
                    Dataset.root_branch_id == branch_lineage.root,
                )
            )
            scope = session.scalar(
                select(VisibilityScope).where(
                    VisibilityScope.dataset_id == query.dataset_id,
                    VisibilityScope.game_id == game_id,
                    VisibilityScope.id == audience,
                )
            )
            if dataset is None or scope is None:
                raise LookupError("Not found")
            authorized = (
                select(Revision)
                .join(Disclosure, Disclosure.revision_id == Revision.id)
                .where(
                    Revision.dataset_id == query.dataset_id,
                    Revision.game_id == game_id,
                    Revision.branch_id == branch_lineage.root,
                    Revision.recorded_at <= known_at,
                    Disclosure.dataset_id == query.dataset_id,
                    Disclosure.game_id == game_id,
                    Disclosure.scope_id == audience,
                    Disclosure.available_at <= known_at,
                    Disclosure.recorded_at <= known_at,
                )
            )
            if cursor:
                try:
                    watermark = IngestionWatermark.model_validate(cursor["watermark"])
                except (KeyError, TypeError, ValueError) as exc:
                    raise ValueError("Invalid memory cursor") from exc
            else:
                record_watermark = int(
                    session.scalar(
                        select(func.coalesce(func.max(Revision.ingestion_order), 0))
                        .select_from(Revision)
                        .join(Disclosure)
                        .where(
                            Revision.dataset_id == query.dataset_id,
                            Revision.game_id == game_id,
                            Revision.branch_id == branch_lineage.root,
                            Revision.recorded_at <= known_at,
                            Disclosure.scope_id == audience,
                            Disclosure.available_at <= known_at,
                            Disclosure.recorded_at <= known_at,
                        )
                    )
                    or 0
                )
                relationship_watermark = int(
                    session.scalar(
                        select(func.coalesce(func.max(RelationshipRevision.ingestion_order), 0))
                        .select_from(RelationshipRevision)
                        .join(RelationshipDisclosure)
                        .where(
                            RelationshipRevision.dataset_id == query.dataset_id,
                            RelationshipRevision.game_id == game_id,
                            RelationshipRevision.branch_id == branch_lineage.root,
                            RelationshipRevision.recorded_at <= known_at,
                            RelationshipDisclosure.scope_id == audience,
                            RelationshipDisclosure.available_at <= known_at,
                            RelationshipDisclosure.recorded_at <= known_at,
                        )
                    )
                    or 0
                )
                watermark = IngestionWatermark(
                    records=record_watermark, relationships=relationship_watermark
                )
            authorized = authorized.where(Revision.ingestion_order <= watermark.records)
            authorized_context = authorized
            if query.record_id or query.record_types:
                authorized = authorized.join(Record, Record.id == Revision.record_id)
            if query.record_id:
                authorized = authorized.where(
                    or_(
                        Revision.external_id == query.record_id,
                        Record.external_id == query.record_id,
                    )
                )
            if query.revision_id:
                authorized = authorized.where(Revision.id == query.revision_id)
            if query.record_types:
                authorized = authorized.where(Record.type_id.in_(query.record_types))
            if query.text:
                authorized = authorized.where(
                    func.to_tsvector("simple", cast(Revision.body, Text)).op("@@")(
                        func.plainto_tsquery("simple", query.text)
                    )
                )
            if query.related_target_id or query.relationship_types or query.relationship_role:
                relationship_targets = self._authorized_relationship_target_ids(
                    session,
                    query,
                    game_id,
                    audience,
                    branch_lineage.root,
                    known_at,
                    effective_at,
                    watermark,
                )
                authorized = authorized.where(
                    or_(
                        Revision.external_id.in_(relationship_targets),
                        Revision.record_id.in_(
                            select(Record.id).where(Record.external_id.in_(relationship_targets))
                        ),
                    )
                )
            count = int(
                session.scalar(select(func.count()).select_from(authorized.subquery())) or 0
            )
            page = authorized
            if cursor:
                page = page.where(
                    or_(
                        Revision.recorded_at > datetime.fromisoformat(cursor["position_time"]),
                        and_(
                            Revision.recorded_at == datetime.fromisoformat(cursor["position_time"]),
                            Revision.id > UUID(cursor["position_id"]),
                        ),
                    )
                )
            rows = list(
                session.scalars(
                    page.order_by(Revision.recorded_at, Revision.id).limit(query.limit + 1)
                )
            )
            has_more, rows = len(rows) > query.limit, rows[: query.limit]
            if (query.record_id or query.revision_id) and not rows:
                raise LookupError("Not found")
            visible_revision_ids = {
                value
                for value in session.scalars(authorized_context.with_only_columns(Revision.id))
            }
            visible_external = {
                value
                for value in session.scalars(
                    authorized_context.with_only_columns(Revision.external_id)
                )
            }
            all_visible = list(
                session.scalars(select(Revision).where(Revision.id.in_(visible_revision_ids)))
            )
            visible_external.update(
                stable_record.external_id
                for stable_record in session.scalars(
                    select(Record).where(Record.id.in_([row.record_id for row in all_visible]))
                )
            )
            action_owners = {
                action["action_id"]: row.external_id
                for row in all_visible
                for action in row.body.get("actions", [])
            }
            superseded = {
                row.supersedes_revision_id for row in all_visible if row.supersedes_revision_id
            }
            references = defaultdict(list)
            for ref in session.scalars(
                select(DeclaredReference).where(
                    DeclaredReference.revision_id.in_([row.id for row in rows])
                )
            ):
                authorized_target = ref.target_kind == "external" or ref.target_id in (
                    action_owners if ref.target_kind == "action" else visible_external
                )
                references[ref.revision_id].append((ref, authorized_target))
            relationship_map = self._relationship_summaries(
                session,
                query.dataset_id,
                game_id,
                audience,
                branch_lineage.root,
                known_at,
                effective_at,
                visible_external,
                action_owners,
                watermark,
            )
            result = []
            for row in rows:
                body = json.loads(json.dumps(row.body))
                for ref, allowed in references[row.id]:
                    if not allowed and ref.json_pointer:
                        _remove_pointer(body, ref.json_pointer)
                permitted_refs = tuple(
                    ReferenceView(
                        purpose=ref.purpose,
                        target_kind=ref.target_kind,
                        target_id=ref.target_id,
                        json_pointer=ref.json_pointer,
                    )
                    for ref, allowed in references[row.id]
                    if allowed
                )
                effective_status = (
                    "pending"
                    if row.valid_from > effective_at.elapsed_microseconds
                    else "expired"
                    if row.valid_to is not None
                    and row.valid_to <= effective_at.elapsed_microseconds
                    else "applicable"
                )
                revision_status = "superseded" if row.id in superseded else "current"
                actions = tuple(
                    ActionView(
                        id=item["action_id"],
                        title=item["Title"],
                        description=item["Description"],
                        intention=item["Intent of Action"],
                        anticipated_reaction=item["Anticipated reaction"],
                    )
                    for item in body.get("actions", [])
                )
                related = tuple(
                    summary
                    for target, summary in relationship_map
                    if target == row.external_id or target in {item.id for item in actions}
                )
                stable_record = session.get(Record, row.record_id)
                if stable_record is None:
                    raise RuntimeError("record identity missing")
                result.append(
                    RecordView(
                        id=row.external_id,
                        stable_id=stable_record.external_id,
                        revision_id=row.id,
                        title=body.get("title") or row.external_id.replace("-", " ").capitalize(),
                        overall_intention=body.get("overall_intention"),
                        actions=actions,
                        kind=stable_record.type_id,
                        recorded_at=row.recorded_at,
                        effective_turn=row.revision_metadata.get("effective_turn"),
                        valid_from=row.valid_from,
                        valid_to=row.valid_to,
                        status=body.get("status", "recorded"),
                        revision_status=revision_status,
                        effective_status=effective_status,
                        temporal_status="superseded"
                        if revision_status == "superseded"
                        else effective_status,
                        visibility_label=scope.label,
                        source_refs=tuple(
                            ref.target_id
                            for ref in permitted_refs
                            if ref.purpose == "evidence" and ref.target_kind == "record"
                        ),
                        references=permitted_refs,
                        relationships=related,
                        body=body,
                        fields=tuple(
                            fields(
                                {
                                    key: value
                                    for key, value in body.items()
                                    if key not in {"actions", "overall_intention"}
                                }
                            )
                        ),
                    )
                )
            next_cursor = None
            if has_more and rows:
                next_cursor = self._encode_cursor(
                    {
                        **context,
                        "dataset": str(query.dataset_id),
                        "watermark": watermark.model_dump(),
                        "position_time": rows[-1].recorded_at.isoformat(),
                        "position_id": str(rows[-1].id),
                    }
                )
            return MemoryView(
                records=tuple(result),
                audience=audience,
                scope=ScopeMetadata(id=scope.id, label=scope.label),
                known_at=known_at,
                effective_at=effective_at,
                authorized_result_count=count,
                next_cursor=next_cursor,
                ingestion_watermark=watermark,
            )

    def _authorized_relationship_target_ids(
        self,
        session: Any,
        query: MemoryQuery,
        game_id: str,
        scope_id: str,
        branch_id: str,
        known_at: datetime,
        effective_at: GameTime,
        watermark: IngestionWatermark,
    ) -> set[str]:
        summaries = self._relationship_summaries(
            session,
            query.dataset_id,
            game_id,
            scope_id,
            branch_id,
            known_at,
            effective_at,
            None,
            None,
            watermark,
        )
        result: set[str] = set()
        for _, summary in summaries:
            if query.relationship_types and summary.type not in query.relationship_types:
                continue
            if query.relationship_role and query.relationship_role not in {
                endpoint.role for endpoint in summary.endpoints
            }:
                continue
            if query.related_target_id and query.related_target_id not in {
                endpoint.target_id for endpoint in summary.endpoints
            }:
                continue
            result.update(
                endpoint.target_id
                for endpoint in summary.endpoints
                if endpoint.target_kind in {"record", "action"}
            )
        return result

    def _relationship_summaries(
        self,
        session: Any,
        dataset_id: UUID,
        game_id: str,
        scope_id: str,
        branch_id: str,
        known_at: datetime,
        effective_at: GameTime,
        visible_records: set[str] | None,
        action_owners: dict[str, str] | None,
        watermark: IngestionWatermark,
    ) -> list[tuple[str, RelationshipSummary]]:
        if visible_records is None or action_owners is None:
            visible_rows = list(
                session.scalars(
                    select(Revision)
                    .join(Disclosure)
                    .where(
                        Revision.dataset_id == dataset_id,
                        Revision.game_id == game_id,
                        Revision.branch_id == branch_id,
                        Revision.recorded_at <= known_at,
                        Disclosure.scope_id == scope_id,
                        Disclosure.available_at <= known_at,
                        Disclosure.recorded_at <= known_at,
                        Revision.ingestion_order <= watermark.records,
                    )
                )
            )
            visible_records = {row.external_id for row in visible_rows}
            visible_records.update(
                stable_record.external_id
                for stable_record in session.scalars(
                    select(Record).where(Record.id.in_([row.record_id for row in visible_rows]))
                )
            )
            action_owners = {
                action["action_id"]: row.external_id
                for row in visible_rows
                for action in row.body.get("actions", [])
            }
        revisions = list(
            session.scalars(
                select(RelationshipRevision)
                .join(RelationshipDisclosure)
                .where(
                    RelationshipRevision.dataset_id == dataset_id,
                    RelationshipRevision.game_id == game_id,
                    RelationshipRevision.branch_id == branch_id,
                    RelationshipRevision.recorded_at <= known_at,
                    RelationshipDisclosure.scope_id == scope_id,
                    RelationshipDisclosure.available_at <= known_at,
                    RelationshipDisclosure.recorded_at <= known_at,
                    RelationshipRevision.ingestion_order <= watermark.relationships,
                )
                .order_by(RelationshipRevision.recorded_at, RelationshipRevision.id)
            )
        )
        superseded = {
            item.supersedes_revision_id for item in revisions if item.supersedes_revision_id
        }
        result: list[tuple[str, RelationshipSummary]] = []
        for revision in revisions:
            endpoints = list(
                session.scalars(
                    select(RelationshipEndpoint)
                    .where(RelationshipEndpoint.revision_id == revision.id)
                    .order_by(RelationshipEndpoint.position)
                )
            )
            if any(
                endpoint.target_kind == "record"
                and endpoint.target_id not in visible_records
                or endpoint.target_kind == "action"
                and endpoint.target_id not in action_owners
                for endpoint in endpoints
            ):
                continue
            relationship = session.get(Relationship, revision.relationship_id)
            effective_status = (
                "pending"
                if revision.valid_from > effective_at.elapsed_microseconds
                else "expired"
                if revision.valid_to is not None
                and revision.valid_to <= effective_at.elapsed_microseconds
                else "applicable"
            )
            summary = RelationshipSummary(
                id=revision.external_id,
                revision_id=revision.id,
                type=relationship.type_id,
                revision_status="superseded" if revision.id in superseded else "current",
                effective_status=effective_status,
                endpoints=tuple(
                    EndpointView(
                        position=e.position,
                        role=e.role_id,
                        target_kind=e.target_kind,
                        target_id=e.target_id,
                    )
                    for e in endpoints
                ),
            )
            result.extend(
                (endpoint.target_id, summary)
                for endpoint in endpoints
                if endpoint.target_kind in {"record", "action"}
            )
        return result


def development_principal(identity: str) -> Principal:
    """Compatibility import; fixture-backed lookup lives in the explorer module."""
    from living_memory.fixture_principals import legacy_principal

    return legacy_principal(identity)
