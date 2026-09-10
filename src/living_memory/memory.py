"""Temporary PostgreSQL timeline store behind the permanent authorized read boundary."""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid5

from pydantic import BaseModel, ConfigDict, JsonValue
from sqlalchemy import ForeignKey, UniqueConstraint, select
from sqlalchemy.dialects.postgresql import JSONB, insert
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import BigInteger, DateTime

from living_memory.clocks import GameTime
from living_memory.db import Base, Database, DevelopmentArtifact
from living_memory.seed import SourcePackage


class Timeline(Base):
    __tablename__ = "memory_timeline"
    id: Mapped[UUID] = mapped_column(
        ForeignKey("development_artifact.id", ondelete="CASCADE"), primary_key=True
    )
    game_id: Mapped[str]
    branch_id: Mapped[str]


class Revision(Base):
    __tablename__ = "memory_revision"
    __table_args__ = (UniqueConstraint("dataset_id", "source_id"),)
    id: Mapped[UUID] = mapped_column(primary_key=True)
    dataset_id: Mapped[UUID] = mapped_column(ForeignKey("memory_timeline.id", ondelete="CASCADE"))
    source_id: Mapped[str]
    record_id: Mapped[str]
    game_id: Mapped[str]
    branch_id: Mapped[str]
    kind: Mapped[str]
    valid_from: Mapped[int] = mapped_column(BigInteger)
    valid_to: Mapped[int | None] = mapped_column(BigInteger)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    supersedes_revision_id: Mapped[UUID | None]
    content: Mapped[dict[str, Any]] = mapped_column(JSONB)


class Disclosure(Base):
    __tablename__ = "memory_disclosure"
    revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("memory_revision.id", ondelete="CASCADE"), primary_key=True
    )
    audience: Mapped[str] = mapped_column(primary_key=True)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ReadModel(BaseModel):
    model_config = ConfigDict(frozen=True)


class Principal(ReadModel):
    identity: str
    game_id: str
    audiences: tuple[str, ...]


def development_principal(identity: str) -> Principal:
    grants = {
        "reviewer": ("adjudicator", "estuary", "upland"),
        "estuary-lead": ("estuary",),
        "estuary-member": ("estuary",),
        "upland-lead": ("upland",),
        "upland-member": ("upland",),
    }
    if identity not in grants:
        raise PermissionError("Unknown principal")
    return Principal(identity=identity, game_id="harbor-relief", audiences=grants[identity])


class BranchLineage(ReadModel):
    root: str


class MemoryQuery(ReadModel):
    dataset_id: UUID
    record_id: str | None = None


class FieldView(ReadModel):
    label: str
    text: str


class ActionView(ReadModel):
    id: str
    title: str
    description: str
    intention: str
    anticipated_reaction: str


class RecordSummary(ReadModel):
    id: str
    title: str
    overall_intention: str | None
    actions: tuple[ActionView, ...]
    kind: str
    recorded_at: datetime
    effective_turn: int
    valid_from: int
    valid_to: int | None
    status: str
    temporal_status: str
    visibility_label: str
    source_refs: tuple[str, ...]
    fields: tuple[FieldView, ...]


class RecordView(RecordSummary):
    body: dict[str, JsonValue]


class MemoryView(ReadModel):
    records: tuple[RecordView, ...]
    audience: str
    known_at: datetime
    effective_at: GameTime


def load_timeline(db: Database, checksum: str) -> bool:
    with db.transaction() as session:
        artifact = session.scalars(
            select(DevelopmentArtifact).where(DevelopmentArtifact.checksum == checksum)
        ).one()
        package = SourcePackage.model_validate_json(artifact.contents["source.json"])
        records = package.records
        scenario = next(r for r in records if r.kind == "scenario")
        game, branch = scenario.game_id, scenario.branch_id
        if any(r.game_id != game or r.branch_id != branch for r in records):
            raise ValueError("Fixture must have one game and root branch")
        result = session.execute(
            insert(Timeline)
            .values(id=artifact.id, game_id=game, branch_id=branch)
            .on_conflict_do_nothing()
            .returning(Timeline.id)
        ).scalar_one_or_none()
        if result is None:
            return False
        boundaries = {}
        elapsed = 0
        for turn in scenario.body["turns"]:
            boundaries[turn["number"]] = elapsed
            elapsed += turn["simulated_days"] * 86400 * 1000000
        by_id = {r.id: r for r in records}

        def parent(rid: str) -> str | None:
            body = by_id[rid].body
            return body.get("supersedes_ref") or body.get("previous_version_ref")

        def stable(rid: str) -> str:
            visited = set()
            while (prior := parent(rid)) is not None:
                if rid in visited or prior not in by_id:
                    raise ValueError("Invalid supersession chain")
                visited.add(rid)
                rid = prior
            return rid

        for r in records:
            if r.kind == "import":
                artifact_name = r.body.get("artifact")
                if artifact_name != "imported-move.txt" or r.body.get(
                    "original_text"
                ) != artifact.contents.get(artifact_name):
                    raise ValueError("Import source text must match its staged artifact")
            revision_id = uuid5(artifact.id, r.id)
            session.add(
                Revision(
                    id=revision_id,
                    dataset_id=artifact.id,
                    source_id=r.id,
                    record_id=stable(r.id),
                    game_id=game,
                    branch_id=branch,
                    kind=r.kind,
                    valid_from=boundaries[r.effective_turn],
                    valid_to=None,
                    recorded_at=r.recorded_at,
                    supersedes_revision_id=uuid5(artifact.id, prior)
                    if (prior := parent(r.id))
                    else None,
                    content=r.model_dump(mode="json", exclude={"disclosures"}),
                )
            )
        session.flush()
        for r in records:
            for audience, available in r.disclosures.items():
                session.add(
                    Disclosure(
                        revision_id=uuid5(artifact.id, r.id),
                        audience=audience,
                        available_at=available,
                        recorded_at=available,
                    )
                )
    return True


def fields(value: JsonValue, prefix: str = "") -> list[FieldView]:
    if isinstance(value, dict):
        return [
            f
            for key, child in value.items()
            for f in fields(child, f"{prefix} / {key}" if prefix else key)
        ]
    if isinstance(value, list):
        return [f for i, child in enumerate(value) for f in fields(child, f"{prefix} {i + 1}")]
    return [
        FieldView(
            label=prefix.replace("_", " ").capitalize(),
            text=str(value) if value is not None else "Unspecified",
        )
    ]


class MemoryReader:
    def __init__(self, db: Database):
        self.db = db

    def lineage(self, dataset_id: UUID, game_id: str) -> BranchLineage:
        with self.db.transaction() as session:
            timeline = session.get(Timeline, dataset_id)
            if timeline is None or timeline.game_id != game_id:
                raise LookupError("Not found")
            return BranchLineage(root=timeline.branch_id)

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
        if principal.game_id != game_id or audience not in principal.audiences:
            raise PermissionError("Audience not permitted")
        if known_at.tzinfo is None:
            raise ValueError("Knowledge cutoff must include timezone")
        if self.lineage(query.dataset_id, game_id) != branch_lineage:
            raise LookupError("Not found")
        with self.db.transaction() as session:
            rows = list(
                session.scalars(
                    select(Revision)
                    .join(Disclosure)
                    .where(
                        Revision.dataset_id == query.dataset_id,
                        Revision.game_id == game_id,
                        Revision.branch_id == branch_lineage.root,
                        Revision.recorded_at <= known_at,
                        Disclosure.audience == audience,
                        Disclosure.available_at <= known_at,
                        Disclosure.recorded_at <= known_at,
                    )
                    .order_by(Revision.recorded_at, Revision.source_id)
                )
            )
            visible = {r.source_id for r in rows}
            actions = {a["action_id"] for r in rows for a in r.content["body"].get("actions", [])}
            superseded = {r.supersedes_revision_id for r in rows}

            def sanitize(value: Any, key: str = "") -> Any:
                if key.endswith("_refs") and isinstance(value, list):
                    return [ref for ref in value if ref in visible or ref in actions]
                if (key.endswith("_ref") or key == "destination_action_id") and isinstance(
                    value, str
                ):
                    return value if value in visible or value in actions else None
                if isinstance(value, dict):
                    return {
                        k: clean for k, v in value.items() if (clean := sanitize(v, k)) is not None
                    }
                if isinstance(value, list):
                    return [sanitize(v) for v in value]
                return value

            result = []
            for row in rows:
                if query.record_id is not None and row.source_id != query.record_id:
                    continue
                body = sanitize(row.content["body"])
                temporal = (
                    "superseded"
                    if row.id in superseded
                    else "pending"
                    if row.valid_from > effective_at.elapsed_microseconds
                    else "expired"
                    if row.valid_to is not None
                    and row.valid_to <= effective_at.elapsed_microseconds
                    else "applicable"
                )
                result.append(
                    RecordView(
                        id=row.source_id,
                        title=body.get("title") or row.source_id.replace("-", " ").capitalize(),
                        overall_intention=body.get("overall_intention"),
                        actions=tuple(
                            ActionView(
                                id=a["action_id"],
                                title=a["Title"],
                                description=a["Description"],
                                intention=a["Intent of Action"],
                                anticipated_reaction=a["Anticipated reaction"],
                            )
                            for a in body.get("actions", [])
                        ),
                        kind=row.kind,
                        recorded_at=row.recorded_at,
                        effective_turn=row.content["effective_turn"],
                        valid_from=row.valid_from,
                        valid_to=row.valid_to,
                        status=body.get("status", "recorded"),
                        temporal_status=temporal,
                        visibility_label={
                            "estuary": "Visible to Estuary Council",
                            "upland": "Visible to Upland Council",
                            "adjudicator": "Visible to adjudicator",
                        }.get(audience, "Visible to selected audience"),
                        source_refs=tuple(
                            ref for ref in row.content["source_refs"] if ref in visible
                        ),
                        body=body,
                        fields=tuple(
                            fields(
                                {
                                    k: v
                                    for k, v in body.items()
                                    if k not in {"actions", "overall_intention"}
                                }
                            )
                        ),
                    )
                )
            if query.record_id is not None and not result:
                raise LookupError("Not found")
            return MemoryView(
                records=tuple(result),
                audience=audience,
                known_at=known_at,
                effective_at=effective_at,
            )
