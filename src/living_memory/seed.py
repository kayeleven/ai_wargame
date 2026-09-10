import hashlib
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import make_url

from living_memory.clocks import Clock
from living_memory.config import DEV_DATABASE, Settings
from living_memory.db import ROOT, Database, DevelopmentArtifact


class FixtureRecord(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str = Field(min_length=1)
    kind: str = Field(min_length=1)
    game_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    effective_turn: int = Field(ge=1)
    recorded_at: AwareDatetime
    source_refs: list[str]
    body: dict[str, Any]


class SourceRecord(FixtureRecord):
    disclosures: dict[str, AwareDatetime]


class SourcePackage(BaseModel):
    model_config = ConfigDict(extra="allow")
    fixture_version: int = Field(ge=1)
    records: list[SourceRecord]


class Snapshot(BaseModel):
    fixture_version: int = Field(ge=1)
    records: list[FixtureRecord]
    viewer: str
    recorded_at_cutoff: AwareDatetime


def read_package(directory: Path) -> tuple[int, str, dict[str, Any]]:
    required = {"source.json", "variant.json", "model-examples.json", "imported-move.txt"}
    required.update(
        f"views/{cutoff}-{viewer}.json"
        for cutoff in ("t3", "review", "release")
        for viewer in ("adjudicator", "estuary", "upland")
    )
    contents: dict[str, Any] = {}
    for name in sorted(required):
        raw = (directory / name).read_text(encoding="utf-8")
        if name.endswith(".json"):
            parsed = json.loads(raw)
            if name == "source.json":
                SourcePackage.model_validate(parsed)
                ids = [record["id"] for record in parsed["records"]]
                if len(ids) != len(set(ids)):
                    raise ValueError("source record IDs must be unique")
            elif name.startswith("views/"):
                snapshot = Snapshot.model_validate(parsed)
                if not name.endswith(f"-{snapshot.viewer}.json"):
                    raise ValueError("snapshot viewer does not match filename")
        # Preserve original text (including import omissions and formatting).
        contents[name] = raw
    version = SourcePackage.model_validate_json(contents["source.json"]).fixture_version
    for name, raw in contents.items():
        if (name == "variant.json" or name.startswith("views/")) and (
            json.loads(raw).get("fixture_version") != version
        ):
            raise ValueError("package fixture versions must agree")
    checksum = hashlib.sha256(
        json.dumps(contents, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()
    return version, checksum, contents


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
    """Internal staging service; CLI authorization is enforced by seed()."""
    version, checksum, contents = read_package(directory)
    with db.transaction() as session:
        result = session.execute(
            insert(DevelopmentArtifact)
            .values(
                id=uuid4(),
                package="phase0",
                package_version=version,
                checksum=checksum,
                staged_at=clock.now(),
                contents=contents,
            )
            .on_conflict_do_nothing(index_elements=["package", "checksum"])
            .returning(DevelopmentArtifact.id)
        ).scalar_one_or_none()
    return result is not None
