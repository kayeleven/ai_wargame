from datetime import UTC, datetime
from uuid import uuid4

import pytest
from alembic import command
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from test_database import database  # noqa: F401

from living_memory.clocks import FixedClock, GameTime
from living_memory.db import ROOT, DevelopmentArtifact, migration_config
from living_memory.memory import (
    BranchLineage,
    Disclosure,
    MemoryQuery,
    MemoryReader,
    Principal,
    Record,
    Relationship,
    RelationshipDisclosure,
    RelationshipEndpoint,
    RelationshipRevision,
    Revision,
    VisibilityGrant,
    load_timeline,
)
from living_memory.seed import PackageManifest, Snapshot, stage_package

pytestmark = pytest.mark.integration


@pytest.fixture
def orchid(database):  # noqa: F811
    db, _ = database
    stage_package(
        db,
        FixedClock(datetime(2045, 1, 1, tzinfo=UTC)),
        ROOT / "fixtures/orchid-accord",
    )
    with db.transaction() as session:
        artifact = session.scalars(select(DevelopmentArtifact)).one()
    assert load_timeline(db, artifact.checksum)
    return db, artifact.id


def principal(*scopes: str) -> Principal:
    return Principal(
        identity="test-reader",
        grants=tuple(
            VisibilityGrant(game_id="orchid-accord", visibility_scope_id=scope) for scope in scopes
        ),
    )


def read(orchid, scope: str, known: str, effective: int, query: MemoryQuery | None = None):
    db, dataset_id = orchid
    return MemoryReader(db, b"test-cursor-key").read_memory(
        principal("amber", "violet", "observer"),
        "orchid-accord",
        scope,
        BranchLineage(root="origin"),
        datetime.fromisoformat(known),
        GameTime(elapsed_microseconds=effective),
        query or MemoryQuery(dataset_id=dataset_id),
    )


def test_irregular_fixture_temporal_disclosure_and_relationship_suppression(orchid):
    before = read(orchid, "amber", "2042-06-03T08:59:59Z", 259_200_000_000)
    assert "orchid-log-v1" not in {record.id for record in before.records}
    amber = read(orchid, "amber", "2042-06-05T09:00:00Z", 604_800_000_000)
    assert not any(record.relationships for record in amber.records)
    observer = read(orchid, "observer", "2042-06-05T09:00:00Z", 604_800_000_000)
    records = {record.id: record for record in observer.records}
    assert records["orchid-log-v1"].revision_status == "superseded"
    assert records["orchid-log-v1"].effective_status == "expired"
    assert records["orchid-log-v2"].effective_status == "applicable"
    revisions = {
        relationship.id: relationship.revision_status
        for record in observer.records
        for relationship in record.relationships
    }
    assert revisions == {"pollination-v1": "superseded", "pollination-v2": "current"}


def test_orchid_oracle_matches_authorized_reader_output(orchid):
    oracle = Snapshot.model_validate_json(
        (ROOT / "fixtures/orchid-accord/oracle.json").read_text(encoding="utf-8")
    )
    assert oracle.effective_at is not None
    actual = read(
        orchid,
        oracle.viewer,
        oracle.recorded_at_cutoff.isoformat(),
        oracle.effective_at,
    )
    assert {record.id for record in actual.records} == {record.id for record in oracle.records}
    expected = {record.id: record for record in oracle.records}
    for record in actual.records:
        assert record.kind == expected[record.id].kind
        assert record.body == expected[record.id].body
        assert record.source_refs == tuple(expected[record.id].source_refs)
    relationships = {
        relationship.id: relationship.revision_status
        for record in actual.records
        for relationship in record.relationships
    }
    assert relationships == oracle.relationship_revisions


def test_distinct_disclosure_availability_and_recording_times(orchid):
    available_but_unrecorded = read(
        orchid, "amber", "2042-06-03T12:00:00Z", 259_200_000_000
    )
    assert "orchid-log-v1" not in {record.id for record in available_but_unrecorded.records}
    recorded = read(orchid, "amber", "2042-06-04T09:00:00Z", 259_200_000_000)
    assert "orchid-log-v1" in {record.id for record in recorded.records}


def test_relationship_revision_disclosure_and_one_hop_filters(orchid):
    _, dataset_id = orchid
    before = read(orchid, "observer", "2042-06-05T08:59:59Z", 604_800_000_000)
    before_relationships = {
        relationship.id: relationship.revision_status
        for record in before.records
        for relationship in record.relationships
    }
    assert before_relationships == {"pollination-v1": "current"}
    at_boundary = read(
        orchid,
        "observer",
        "2042-06-05T09:00:00Z",
        604_800_000_000,
        MemoryQuery(
            dataset_id=dataset_id,
            relationship_types=("orchid:cross-pollinates",),
        ),
    )
    assert {record.id for record in at_boundary.records} == {
        "amber-move",
        "hidden-carrier",
        "orchid-log-v1",
        "orchid-log-v2",
    }
    hidden_endpoint = read(
        orchid,
        "amber",
        "2042-06-05T09:00:00Z",
        604_800_000_000,
        MemoryQuery(
            dataset_id=dataset_id,
            relationship_types=("orchid:cross-pollinates",),
        ),
    )
    assert hidden_endpoint.authorized_result_count == 0
    assert not hidden_endpoint.records


def test_simple_search_and_signed_cursor_context(orchid):
    _, dataset_id = orchid
    exact = read(
        orchid,
        "observer",
        "2042-06-05T09:00:00Z",
        604_800_000_000,
        MemoryQuery(dataset_id=dataset_id, text="petals"),
    )
    assert {record.id for record in exact.records} == {"orchid-log-v1", "orchid-log-v2"}
    stem = read(
        orchid,
        "observer",
        "2042-06-05T09:00:00Z",
        604_800_000_000,
        MemoryQuery(dataset_id=dataset_id, text="petal"),
    )
    assert not stem.records
    first = read(
        orchid,
        "observer",
        "2042-06-05T09:00:00Z",
        604_800_000_000,
        MemoryQuery(dataset_id=dataset_id, limit=2),
    )
    assert len(first.records) == 2
    assert first.next_cursor
    assert first.authorized_result_count == 6
    second = read(
        orchid,
        "observer",
        "2042-06-05T09:00:00Z",
        604_800_000_000,
        MemoryQuery(dataset_id=dataset_id, limit=2, cursor=first.next_cursor),
    )
    assert {record.id for record in first.records}.isdisjoint(
        record.id for record in second.records
    )
    with pytest.raises(ValueError, match="cursor"):
        read(
            orchid,
            "amber",
            "2042-06-05T09:00:00Z",
            604_800_000_000,
            MemoryQuery(dataset_id=dataset_id, limit=2, cursor=first.next_cursor),
        )


def test_cursor_rejects_every_context_change_and_freezes_ingestion(orchid):
    db, dataset_id = orchid
    reader = MemoryReader(db, b"test-cursor-key")
    known_at = datetime.fromisoformat("2042-06-05T09:00:00Z")
    effective_at = GameTime(elapsed_microseconds=604_800_000_000)
    base = MemoryQuery(
        dataset_id=dataset_id,
        relationship_types=("orchid:cross-pollinates",),
        limit=2,
    )
    first = reader.read_memory(
        principal("observer"),
        "orchid-accord",
        "observer",
        BranchLineage(root="origin"),
        known_at,
        effective_at,
        base,
    )
    assert first.next_cursor
    legacy_payload = reader._decode_cursor(first.next_cursor)
    legacy_payload["watermark"] = first.ingestion_watermark.records
    with pytest.raises(ValueError, match="cursor"):
        reader.read_memory(
            principal("observer"),
            "orchid-accord",
            "observer",
            BranchLineage(root="origin"),
            known_at,
            effective_at,
            base.model_copy(update={"cursor": reader._encode_cursor(legacy_payload)}),
        )
    mismatches = (
        ("observer", BranchLineage(root="origin"), known_at.replace(hour=8), effective_at, base),
        (
            "observer",
            BranchLineage(root="origin"),
            known_at,
            GameTime(elapsed_microseconds=604_800_000_001),
            base,
        ),
        ("observer", BranchLineage(root="other"), known_at, effective_at, base),
        (
            "observer",
            BranchLineage(root="origin"),
            known_at,
            effective_at,
            base.model_copy(update={"text": "petals"}),
        ),
        (
            "observer",
            BranchLineage(root="origin"),
            known_at,
            effective_at,
            base.model_copy(update={"dataset_id": uuid4()}),
        ),
    )
    for scope, lineage, changed_known, changed_effective, changed_query in mismatches:
        with pytest.raises(ValueError, match="cursor"):
            reader.read_memory(
                principal("observer"),
                "orchid-accord",
                scope,
                lineage,
                changed_known,
                changed_effective,
                changed_query.model_copy(update={"cursor": first.next_cursor}),
            )
    with pytest.raises(ValueError, match="cursor"):
        reader.read_memory(
            principal("observer"),
            "orchid-accord",
            "observer",
            BranchLineage(root="origin"),
            known_at,
            effective_at,
            base.model_copy(update={"cursor": "malformed"}),
        )

    stable_id, revision_id = uuid4(), uuid4()
    with db.transaction() as session:
        session.add(
            Record(
                id=stable_id,
                dataset_id=dataset_id,
                game_id="orchid-accord",
                branch_id="origin",
                external_id="later-stable",
                type_id="platform:observation",
            )
        )
        session.flush()
        session.add(
            Revision(
                id=revision_id,
                record_id=stable_id,
                dataset_id=dataset_id,
                game_id="orchid-accord",
                branch_id="origin",
                external_id="later-revision",
                recorded_at=known_at,
                valid_from=0,
                valid_to=None,
                supersedes_revision_id=None,
                body={"title": "Later ingestion"},
                revision_metadata={"effective_turn": None},
            )
        )
        session.flush()
        session.add(
            Disclosure(
                revision_id=revision_id,
                dataset_id=dataset_id,
                game_id="orchid-accord",
                scope_id="observer",
                available_at=known_at,
                recorded_at=known_at,
            )
        )
        relationship_id, relationship_revision_id = uuid4(), uuid4()
        session.add(
            Relationship(
                id=relationship_id,
                dataset_id=dataset_id,
                game_id="orchid-accord",
                branch_id="origin",
                external_id="later-relationship",
                type_id="orchid:cross-pollinates",
            )
        )
        session.flush()
        session.add(
            RelationshipRevision(
                id=relationship_revision_id,
                relationship_id=relationship_id,
                dataset_id=dataset_id,
                game_id="orchid-accord",
                branch_id="origin",
                external_id="later-relationship-v1",
                recorded_at=known_at,
                valid_from=0,
                valid_to=None,
                supersedes_revision_id=None,
                body={},
            )
        )
        session.flush()
        session.add(
            RelationshipDisclosure(
                revision_id=relationship_revision_id,
                dataset_id=dataset_id,
                game_id="orchid-accord",
                scope_id="observer",
                available_at=known_at,
                recorded_at=known_at,
            )
        )
        session.add_all(
            (
                RelationshipEndpoint(
                    revision_id=relationship_revision_id,
                    position=0,
                    role_id="orchid:source",
                    target_kind="record",
                    target_id="accord-config",
                ),
                RelationshipEndpoint(
                    revision_id=relationship_revision_id,
                    position=1,
                    role_id="orchid:recipient",
                    target_kind="record",
                    target_id="violet-note",
                ),
            )
        )
    seen = {record.id for record in first.records}
    cursor = first.next_cursor
    while cursor:
        page = reader.read_memory(
            principal("observer"),
            "orchid-accord",
            "observer",
            BranchLineage(root="origin"),
            known_at,
            effective_at,
            base.model_copy(update={"cursor": cursor}),
        )
        assert page.authorized_result_count == first.authorized_result_count
        seen.update(record.id for record in page.records)
        cursor = page.next_cursor
    assert len(seen) == first.authorized_result_count
    assert "later-revision" not in seen
    with db.transaction() as session:
        later_relationship_order = session.get(
            RelationshipRevision, relationship_revision_id
        ).ingestion_order
    assert later_relationship_order > first.ingestion_watermark.relationships


def test_database_rejects_cross_identity_supersession_and_invalid_interval(orchid):
    db, dataset_id = orchid
    with db.transaction() as session:
        revisions = list(
            session.scalars(select(Revision).where(Revision.dataset_id == dataset_id).limit(2))
        )
    first, second = revisions
    with pytest.raises(IntegrityError):
        with db.transaction() as session:
            session.add(
                Revision(
                    id=uuid4(),
                    record_id=first.record_id,
                    dataset_id=dataset_id,
                    game_id="orchid-accord",
                    branch_id="origin",
                    external_id="cross-identity-supersession",
                    recorded_at=datetime(2042, 6, 6, tzinfo=UTC),
                    valid_from=0,
                    valid_to=None,
                    supersedes_revision_id=second.id,
                    body={},
                    revision_metadata={},
                )
            )
    with pytest.raises(IntegrityError):
        with db.transaction() as session:
            session.add(
                Revision(
                    id=uuid4(),
                    record_id=first.record_id,
                    dataset_id=dataset_id,
                    game_id="orchid-accord",
                    branch_id="origin",
                    external_id="invalid-interval",
                    recorded_at=datetime(2042, 6, 6, tzinfo=UTC),
                    valid_from=10,
                    valid_to=10,
                    supersedes_revision_id=None,
                    body={},
                    revision_metadata={},
                )
            )


def test_core_has_no_fixture_vocabulary_or_fixed_cardinality():
    core = "\n".join(
        (ROOT / path).read_text(encoding="utf-8").lower()
        for path in ("src/living_memory/memory.py", "src/living_memory/explorer.py")
    )
    prohibited = {
        "harbor-relief",
        "orchid-accord",
        "estuary",
        "upland",
        "amber brief",
        "credits",
        "invoices",
        "funding",
        "council",
    }
    assert not {word for word in prohibited if word in core}
    manifests = [
        PackageManifest.model_validate_json((ROOT / path).read_text())
        for path in (
            "fixtures/phase0/manifest.json",
            "fixtures/orchid-accord/manifest.json",
        )
    ]
    assert len(manifests[0].visibility_scopes) != len(manifests[1].visibility_scopes)
    assert all(manifest.visibility_scopes for manifest in manifests)


def test_populated_1b_migration_requires_0005_rebuild(database):  # noqa: F811
    db, _ = database
    config = migration_config()
    try:
        with db.engine.begin() as connection:
            config.attributes["connection"] = connection
            command.downgrade(config, "0002")
        stage_package(
            db,
            FixedClock(datetime(2045, 1, 1, tzinfo=UTC)),
            ROOT / "fixtures/phase0",
        )
        with db.transaction() as session:
            artifact = session.scalars(select(DevelopmentArtifact)).one()
            preserved = dict(artifact.contents)
            preserved.pop("_manifest.json")
            preserved.pop("_records.json")
            preserved.pop("manifest.json")
            artifact.contents = preserved
            artifact.package = "phase0"
            session.execute(
                text(
                    "INSERT INTO memory_timeline (id, game_id, branch_id) "
                    "VALUES (:id, :game, :branch)"
                ),
                {"id": artifact.id, "game": "harbor-relief", "branch": "main"},
            )
        with db.engine.begin() as connection:
            config.attributes["connection"] = connection
            with pytest.raises(RuntimeError, match="empty 0004 schema"):
                command.upgrade(config, "head")
    finally:
        # This destructive legacy-schema exercise must not poison later tests.
        with db.engine.begin() as connection:
            assert connection.scalar(text("SELECT current_database()")) == "living_memory_test"
            connection.execute(text("DROP SCHEMA public CASCADE"))
            connection.execute(text("CREATE SCHEMA public"))
            config.attributes["connection"] = connection
            command.upgrade(config, "head")
