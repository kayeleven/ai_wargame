"""Manifest-driven development package staging and validation."""

import hashlib
import json
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import make_url

from living_memory.clocks import Clock
from living_memory.config import DEV_DATABASE, Settings
from living_memory.db import ROOT, Database, DevelopmentArtifact


class ReferenceDeclaration(BaseModel):
    purpose: str = Field(min_length=1)
    target_kind: Literal["record", "action", "external"] = "record"
    target_id: str = Field(min_length=1)
    json_pointer: str | None = None


class DisclosureSource(BaseModel):
    available_at: AwareDatetime
    recorded_at: AwareDatetime


DisclosureValue = AwareDatetime | DisclosureSource


class FixtureRecord(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str = Field(min_length=1)
    stable_id: str | None = None
    kind: str = Field(min_length=1)
    game_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    effective_turn: int | None = Field(default=None, ge=1)
    valid_from: int | None = Field(default=None, ge=0)
    valid_to: int | None = Field(default=None, ge=0)
    recorded_at: AwareDatetime
    supersedes: str | None = None
    source_refs: list[str] = Field(default_factory=list)
    references: list[ReferenceDeclaration] = Field(default_factory=list)
    body: dict[str, Any]

    @model_validator(mode="after")
    def valid_interval(self) -> "FixtureRecord":
        if self.effective_turn is None and self.valid_from is None:
            raise ValueError("a record needs effective_turn or valid_from")
        if (
            self.valid_to is not None
            and self.valid_from is not None
            and self.valid_from >= self.valid_to
        ):
            raise ValueError("validity interval must be nonempty")
        return self


class SourceRecord(FixtureRecord):
    disclosures: dict[str, DisclosureValue]


class SourcePackage(BaseModel):
    model_config = ConfigDict(extra="allow")
    fixture_version: int = Field(ge=1)
    records: list[SourceRecord] = Field(min_length=1)


class RelationshipEndpointSource(BaseModel):
    role: str = Field(min_length=1)
    target_kind: Literal["record", "action", "external"]
    target_id: str = Field(min_length=1)


class RelationshipRevisionSource(BaseModel):
    id: str = Field(min_length=1)
    stable_id: str = Field(min_length=1)
    type: str = Field(min_length=1)
    recorded_at: AwareDatetime
    valid_from: int = Field(ge=0)
    valid_to: int | None = Field(default=None, ge=0)
    supersedes: str | None = None
    disclosures: dict[str, DisclosureValue]
    endpoints: list[RelationshipEndpointSource] = Field(min_length=2)
    body: dict[str, Any] = Field(default_factory=dict)


class ScopeSource(BaseModel):
    id: str = Field(min_length=1)
    label: str = Field(min_length=1)


class PrincipalSource(BaseModel):
    id: str = Field(min_length=1)
    grants: list[str] = Field(min_length=1)


class CheckpointSource(BaseModel):
    id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    known_at: AwareDatetime
    effective_at: int = Field(ge=0)


class PresetSource(BaseModel):
    id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    record_types: list[str] | None = None


class TypeSource(BaseModel):
    id: str = Field(min_length=1)
    label: str = Field(min_length=1)


class PackageManifest(BaseModel):
    format_version: int = 1
    package_id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    game_id: str = Field(min_length=1)
    root_branch_id: str = Field(min_length=1)
    source_files: list[str] = Field(default_factory=lambda: ["source.json"], min_length=1)
    artifact_files: list[str] = Field(default_factory=list)
    oracle_files: list[str] = Field(default_factory=list)
    visibility_scopes: list[ScopeSource] = Field(min_length=1)
    development_principals: list[PrincipalSource] = Field(min_length=1)
    record_types: list[TypeSource] = Field(default_factory=list)
    relationship_types: list[TypeSource] = Field(default_factory=list)
    relationship_roles: list[TypeSource] = Field(default_factory=list)
    relationships: list[RelationshipRevisionSource] = Field(default_factory=list)
    references: dict[str, list[ReferenceDeclaration]] = Field(default_factory=dict)
    checkpoints: list[CheckpointSource] = Field(min_length=1)
    explorer_presets: list[PresetSource] = Field(default_factory=list)
    default_principal: str | None = None
    default_checkpoint: str | None = None
    default_preset: str | None = None
    reference_corrections: list[str] = Field(default_factory=list)


class Snapshot(BaseModel):
    fixture_version: int = Field(ge=1)
    records: list[FixtureRecord]
    viewer: str
    recorded_at_cutoff: AwareDatetime
    effective_at: int | None = Field(default=None, ge=0)
    relationship_revisions: dict[str, Literal["current", "superseded"]] = Field(
        default_factory=dict
    )


class ReconciliationItem(BaseModel):
    revision_id: str
    json_pointer: str
    target_id: str


class ReferenceReconciliation(BaseModel):
    matched: tuple[ReconciliationItem, ...]
    legacy_only: tuple[ReconciliationItem, ...]
    declared_only: tuple[ReconciliationItem, ...]
    corrections: tuple[str, ...]


def _legacy_references(record: SourceRecord) -> set[tuple[str, str, str]]:
    found = {
        (record.id, f"/source_refs/{index}", target)
        for index, target in enumerate(record.source_refs)
    }

    def walk(value: Any, pointer: str = "") -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                child_pointer = pointer + "/" + key.replace("~", "~0").replace("/", "~1")
                if isinstance(child, str) and (
                    key.endswith("_ref") or key == "destination_action_id"
                ):
                    found.add((record.id, child_pointer, child))
                elif isinstance(child, list) and key.endswith("_refs"):
                    found.update(
                        (record.id, f"{child_pointer}/{index}", target)
                        for index, target in enumerate(child)
                        if isinstance(target, str)
                    )
                walk(child, child_pointer)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                walk(child, f"{pointer}/{index}")

    walk(record.body)
    return found


def reference_reconciliation(
    source: SourcePackage, manifest: PackageManifest
) -> ReferenceReconciliation:
    """Compare the retired suffix heuristic with explicit package declarations."""
    legacy = set().union(*(_legacy_references(record) for record in source.records))
    declared = {
        (record.id, f"/source_refs/{index}", target)
        for record in source.records
        for index, target in enumerate(record.source_refs)
    }
    for record in source.records:
        for declaration in [*record.references, *manifest.references.get(record.id, [])]:
            if declaration.json_pointer:
                declared.add((record.id, declaration.json_pointer, declaration.target_id))

    def items(values: set[tuple[str, str, str]]) -> tuple[ReconciliationItem, ...]:
        return tuple(
            ReconciliationItem(revision_id=revision, json_pointer=pointer, target_id=target)
            for revision, pointer, target in sorted(values)
        )

    return ReferenceReconciliation(
        matched=items(legacy & declared),
        legacy_only=items(legacy - declared),
        declared_only=items(declared - legacy),
        corrections=tuple(manifest.reference_corrections),
    )


def legacy_manifest(source: SourcePackage) -> PackageManifest:
    """Compatibility adapter for preserved 1B packages; new packages require a manifest."""
    first = source.records[0]
    scopes = sorted({scope for record in source.records for scope in record.disclosures})
    turns = first.body.get("turns", [])
    elapsed = sum(int(turn["simulated_days"]) for turn in turns) * 86_400_000_000
    return PackageManifest(
        package_id="legacy-package",
        label="Legacy fixture",
        game_id=first.game_id,
        root_branch_id=first.branch_id,
        visibility_scopes=[ScopeSource(id=value, label=value) for value in scopes],
        development_principals=[PrincipalSource(id="reviewer", grants=scopes)],
        checkpoints=[
            CheckpointSource(
                id="latest",
                label="Latest",
                known_at=max(r.recorded_at for r in source.records),
                effective_at=elapsed,
            )
        ],
    )


def artifact_manifest(
    package_name: str, source: SourcePackage, contents: dict[str, Any]
) -> PackageManifest:
    """Adapt staged pre-manifest development packages without reference inference."""
    raw = contents.get("_manifest.json")
    if isinstance(raw, str):
        return PackageManifest.model_validate_json(raw)
    adapters = {"phase0": ROOT / "fixtures/phase0/manifest.json"}
    adapter = adapters.get(package_name)
    if adapter and adapter.is_file():
        return PackageManifest.model_validate_json(adapter.read_text(encoding="utf-8"))
    return legacy_manifest(source)


def artifact_supersession(package_name: str, record: SourceRecord) -> str | None:
    """Adapt the one preserved pre-manifest fixture's explicit version fields."""
    if record.supersedes:
        return record.supersedes
    if package_name == "phase0":
        value = record.body.get("supersedes_ref") or record.body.get("previous_version_ref")
        return value if isinstance(value, str) else None
    return None


def read_package(directory: Path) -> tuple[int, str, dict[str, Any]]:
    manifest_path = directory / "manifest.json"
    if manifest_path.exists():
        manifest = PackageManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
        packages = [
            SourcePackage.model_validate_json((directory / name).read_text(encoding="utf-8"))
            for name in manifest.source_files
        ]
        versions = {item.fixture_version for item in packages}
        if len(versions) != 1:
            raise ValueError("record source fixture versions must agree")
        source = SourcePackage(
            fixture_version=next(iter(versions)),
            records=[record for item in packages for record in item.records],
        )
    else:
        source_raw = (directory / "source.json").read_text(encoding="utf-8")
        source = SourcePackage.model_validate_json(source_raw)
        manifest = legacy_manifest(source)
    if manifest.game_id != source.records[0].game_id:
        raise ValueError("manifest and records disagree on game")
    collections = (
        manifest.visibility_scopes,
        manifest.development_principals,
        manifest.record_types,
        manifest.relationship_types,
        manifest.relationship_roles,
        manifest.checkpoints,
        manifest.explorer_presets,
    )
    if any(len(items) != len({item.id for item in items}) for items in collections):
        raise ValueError("manifest typed IDs must be unique within their category")
    scopes = {item.id for item in manifest.visibility_scopes}
    if any(set(item.grants) - scopes for item in manifest.development_principals):
        raise ValueError("development principal has an undeclared scope grant")
    defaults = (
        (manifest.default_principal, {item.id for item in manifest.development_principals}),
        (manifest.default_checkpoint, {item.id for item in manifest.checkpoints}),
        (manifest.default_preset, {item.id for item in manifest.explorer_presets}),
    )
    if any(value is not None and value not in choices for value, choices in defaults):
        raise ValueError("manifest default names an undeclared option")
    relationship_ids = [item.id for item in manifest.relationships]
    if len(relationship_ids) != len(set(relationship_ids)):
        raise ValueError("relationship revision IDs must be unique")
    names = set(manifest.source_files + manifest.artifact_files + manifest.oracle_files)
    if not manifest_path.exists():
        names.add("source.json")
    if manifest_path.exists():
        names.add("manifest.json")
    contents: dict[str, Any] = {}
    oracles: list[Snapshot] = []
    root = directory.resolve()
    for name in sorted(names):
        path = (directory / name).resolve()
        if not path.is_file() or root not in path.parents:
            raise ValueError(f"missing or unsafe package file: {name}")
        raw = path.read_text(encoding="utf-8")
        if name.endswith(".json"):
            json.loads(raw)
        if name in manifest.oracle_files and name.endswith(".json"):
            oracle = Snapshot.model_validate_json(raw)
            if oracle.fixture_version != source.fixture_version:
                raise ValueError("package fixture versions must agree")
            oracles.append(oracle)
        contents[name] = raw
    ids = [record.id for record in source.records]
    if len(ids) != len(set(ids)):
        raise ValueError("source record IDs must be unique")
    if any(name not in ids for name in manifest.references):
        raise ValueError("reference declaration names an unknown revision")
    oracle_relationship_ids = {item.id for item in manifest.relationships}
    if any(
        oracle.viewer not in scopes
        or {record.id for record in oracle.records} - set(ids)
        or set(oracle.relationship_revisions) - oracle_relationship_ids
        for oracle in oracles
    ):
        raise ValueError("oracle names an undeclared scope, record, or relationship revision")
    reconciliation = reference_reconciliation(source, manifest)
    if (reconciliation.legacy_only or reconciliation.declared_only) and not (
        reconciliation.corrections
    ):
        raise ValueError("reference reconciliation differences require an intentional correction")
    contents["_manifest.json"] = manifest.model_dump_json()
    contents["_records.json"] = source.model_dump_json()
    checksum = hashlib.sha256(
        json.dumps(contents, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()
    return source.fixture_version, checksum, contents


def seed(
    settings: Settings, db: Database, clock: Clock, directory: Path = ROOT / "fixtures/phase0"
) -> bool:
    url = make_url(settings.database_url.get_secret_value())
    if (
        settings.environment != "development"
        or url.database != DEV_DATABASE
        or url.host not in {"127.0.0.1", "localhost"}
        or db.engine.url != url
    ):
        raise ValueError("seeding requires the explicit localhost development database")
    return stage_package(db, clock, directory)


def stage_package(db: Database, clock: Clock, directory: Path) -> bool:
    """Validate and atomically preserve every declared package source."""
    version, checksum, contents = read_package(directory)
    manifest = PackageManifest.model_validate_json(contents["_manifest.json"])
    with db.transaction() as session:
        result = session.execute(
            insert(DevelopmentArtifact)
            .values(
                id=uuid4(),
                package=manifest.package_id,
                package_version=version,
                checksum=checksum,
                staged_at=clock.now(),
                contents=contents,
            )
            .on_conflict_do_nothing(index_elements=["package", "checksum"])
            .returning(DevelopmentArtifact.id)
        ).scalar_one_or_none()
    return result is not None
