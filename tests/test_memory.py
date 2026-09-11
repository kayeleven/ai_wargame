import json
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from test_database import database  # noqa: F401

from living_memory.app import create_app
from living_memory.clocks import FixedClock, GameTime
from living_memory.db import ROOT, DevelopmentArtifact
from living_memory.memory import (
    BranchLineage,
    Disclosure,
    MemoryQuery,
    MemoryReader,
    Revision,
    development_principal,
    load_timeline,
)
from living_memory.seed import stage_package

pytestmark = pytest.mark.integration


@pytest.fixture
def timeline(database):  # noqa: F811
    db, settings = database
    stage_package(db, FixedClock(datetime(2035, 1, 1, tzinfo=UTC)), ROOT / "fixtures/phase0")
    with db.transaction() as session:
        artifact = session.scalars(select(DevelopmentArtifact)).one()
        checksum, dataset_id = artifact.checksum, artifact.id
    assert load_timeline(db, checksum)
    assert not load_timeline(db, checksum)
    return db, settings, dataset_id


def read(timeline, audience="adjudicator", cutoff="2030-04-04T20:00:00Z", record=None):
    db, _, dataset_id = timeline
    return MemoryReader(db).read_memory(
        development_principal("reviewer"),
        "harbor-relief",
        audience,
        BranchLineage(root="main"),
        datetime.fromisoformat(cutoff),
        GameTime(elapsed_microseconds=21 * 86400 * 1000000),
        MemoryQuery(dataset_id=dataset_id, record_id=record),
    )


@pytest.mark.parametrize("checkpoint", ["t3", "review", "release"])
@pytest.mark.parametrize("audience", ["adjudicator", "estuary", "upland"])
def test_nine_oracles(timeline, checkpoint, audience):
    expected = json.loads(
        (ROOT / f"fixtures/phase0/views/{checkpoint}-{audience}.json").read_text()
    )
    actual = read(timeline, audience, expected["recorded_at_cutoff"])
    assert {r.id for r in actual.records} == {r["id"] for r in expected["records"]}
    by_id = {r.id: r for r in actual.records}
    for record in expected["records"]:
        found = by_id[record["id"]]
        assert found.body == record["body"]
        assert list(found.source_refs) == record["source_refs"]
        assert found.kind == record["kind"]
        assert found.effective_turn == record["effective_turn"]
        assert found.recorded_at == datetime.fromisoformat(record["recorded_at"])
        assert (
            found.visibility_label
            == {
                "estuary": "Visible to Estuary Council",
                "upland": "Visible to Upland Council",
                "adjudicator": "Visible to adjudicator",
            }[audience]
        )
    assert timeline[0].engine.pool.checkedout() == 0


def test_visibility_is_independent_of_other_audience_disclosures(timeline):
    before = read(timeline, "estuary", record="commitment-1-updated")
    db, _, dataset_id = timeline
    with db.transaction() as session:
        revision = session.scalars(
            select(Revision).where(
                Revision.dataset_id == dataset_id,
                Revision.source_id == "commitment-1-updated",
            )
        ).one()
        disclosure = session.get(Disclosure, (revision.id, "upland"))
        disclosure.available_at = datetime(2031, 1, 1, tzinfo=UTC)
        disclosure.recorded_at = datetime(2031, 1, 1, tzinfo=UTC)
    with pytest.raises(LookupError):
        read(timeline, "upland", record="commitment-1-updated")
    after = read(timeline, "estuary", record="commitment-1-updated")
    assert after == before
    assert after.records[0].visibility_label == "Visible to Estuary Council"


def test_time_status_and_late_recording(timeline):
    assert read(timeline, "estuary", "2030-04-04T17:59:59Z").records
    with pytest.raises(LookupError):
        read(timeline, "estuary", "2030-04-04T17:59:59Z", "observation-permits")
    assert read(timeline, "estuary", "2030-04-04T18:00:00Z", "observation-permits")
    with pytest.raises(LookupError):
        read(timeline, "upland", record="observation-permits")
    with pytest.raises(LookupError):
        read(timeline, "upland", "2030-04-04T18:59:59Z", "commitment-1-updated")
    assert read(timeline, "upland", "2030-04-04T19:00:00Z", "commitment-1-updated")
    db, _, dataset_id = timeline
    with db.transaction() as session:
        revision = session.scalars(
            select(Revision).where(
                Revision.dataset_id == dataset_id, Revision.source_id == "observation-permits"
            )
        ).one()
        disclosure = session.get(Disclosure, (revision.id, "estuary"))
        disclosure.recorded_at = datetime(2030, 4, 4, 19, tzinfo=UTC)
    with pytest.raises(LookupError):
        read(timeline, "estuary", "2030-04-04T18:30:00Z", "observation-permits")
    assert read(timeline, "estuary", "2030-04-04T19:00:00Z", "observation-permits")
    records = {r.id: r for r in read(timeline).records}
    for name in [
        "commitment-1",
        "estuary-t4-v1",
        "effect-guarantee-scheduled",
        "effect-customs-scheduled",
    ]:
        assert records[name].temporal_status == "superseded"
    assert records["effect-guarantee-cancelled"].status == "cancelled"
    reader = MemoryReader(db)
    t3 = reader.read_memory(
        development_principal("reviewer"),
        "harbor-relief",
        "adjudicator",
        BranchLineage(root="main"),
        datetime(2030, 4, 3, 23, tzinfo=UTC),
        GameTime(elapsed_microseconds=14 * 86400 * 1000000),
        MemoryQuery(dataset_id=dataset_id),
    )
    assert (
        next(r for r in t3.records if r.id == "effect-customs-scheduled").temporal_status
        == "pending"
    )
    assert "effect-customs-active" not in {r.id for r in t3.records}


def test_authorization_and_navigation(timeline):
    db, settings, dataset_id = timeline
    reader = MemoryReader(db)
    for game, branch, dataset, audience, error in [
        ("other-game", "main", dataset_id, "estuary", PermissionError),
        ("harbor-relief", "other-branch", dataset_id, "estuary", LookupError),
        ("harbor-relief", "main", uuid4(), "estuary", LookupError),
        ("harbor-relief", "main", dataset_id, "adjudicator", PermissionError),
    ]:
        with pytest.raises(error):
            reader.read_memory(
                development_principal("estuary-member"),
                game,
                audience,
                BranchLineage(root=branch),
                datetime(2030, 4, 5, tzinfo=UTC),
                GameTime(elapsed_microseconds=0),
                MemoryQuery(dataset_id=dataset),
            )
    dev = settings.model_copy(update={"environment": "development"})
    with TestClient(create_app(dev, db)) as client:
        params = {"identity": "upland-member", "dataset": str(dataset_id), "checkpoint": "release"}
        page = client.get("/dev/memory", params=params)
        assert page.status_code == 200
        for hidden in ["estuary-t4-v2", "rfi-permits-answer", "observation-permits", "ruling-fund"]:
            assert hidden not in page.text
            assert client.get("/dev/memory", params={**params, "record": hidden}).status_code == 404
        assert client.get("/dev/memory", params={**params, "record": "nonexistent"}).json() == {
            "detail": "Not found"
        }
        assert (
            client.get("/dev/memory", params={**params, "audience": "adjudicator"}).status_code
            == 403
        )
        assert page.headers["cache-control"] == "no-store"
        assert "commitment-1-updated" in page.text
    with TestClient(create_app(settings, db)) as client:
        assert client.get("/dev/memory").status_code == 404


def test_undeclared_id_shaped_strings_remain_opaque_content(timeline):
    db, _, dataset_id = timeline
    with db.transaction() as session:
        note = session.scalars(
            select(Revision).where(
                Revision.dataset_id == dataset_id, Revision.source_id == "coordination-1"
            )
        ).one()
        note.body = {
            **note.body,
            "private_ref": "upland-t4-v1",
            "embedded_refs": ["upland-t4-v1", "estuary-t3-v1"],
        }
    result = read(timeline, "estuary")
    note = next(r for r in result.records if r.id == "coordination-1")
    assert note.body["private_ref"] == "upland-t4-v1"
    assert note.body["embedded_refs"] == ["upland-t4-v1", "estuary-t3-v1"]
    assert not any(ref.target_id == "upland-t4-v1" for ref in note.references)


def test_loader_atomicity_and_changed_packages(timeline, tmp_path):
    import shutil

    from sqlalchemy import func

    from living_memory.memory import Timeline
    from living_memory.seed import read_package

    db, _, original = timeline
    directory = tmp_path / "fixture"
    shutil.copytree(ROOT / "fixtures/phase0", directory)
    source = directory / "source.json"
    package = json.loads(source.read_text())
    package["records"][0]["body"]["description"] = "Changed scenario text."
    source.write_text(json.dumps(package))
    stage_package(db, FixedClock(datetime(2035, 1, 2, tzinfo=UTC)), directory)
    assert load_timeline(db, read_package(directory)[1])
    with db.transaction() as session:
        assert session.scalar(select(func.count()).select_from(Timeline)) == 2
    assert "Changed scenario text." not in read(timeline, record="scenario-v1").model_dump_json()
    package["records"][-1]["supersedes"] = "nonexistent"
    source.write_text(json.dumps(package))
    stage_package(db, FixedClock(datetime(2035, 1, 3, tzinfo=UTC)), directory)
    with pytest.raises(ValueError, match="supersession"):
        load_timeline(db, read_package(directory)[1])
    with db.transaction() as session:
        assert session.scalar(select(func.count()).select_from(Timeline)) == 2
    assert db.engine.pool.checkedout() == 0
