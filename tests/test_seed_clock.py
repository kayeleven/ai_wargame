import json
import shutil
from datetime import UTC, datetime

import pytest

from living_memory.clocks import FixedClock, GameTime
from living_memory.db import ROOT, Database
from living_memory.seed import read_package, seed


def test_clock_and_simulated_time():
    clock = FixedClock(datetime(2030, 1, 1, tzinfo=UTC))
    game_time = GameTime(elapsed_microseconds=7 * 24 * 3600 * 1_000_000)
    assert clock.now() == datetime(2030, 1, 1, tzinfo=UTC)
    assert game_time.elapsed_microseconds == 604800000000
    with pytest.raises(ValueError):
        FixedClock(datetime(2030, 1, 1))


def test_package_preservation_and_validation(tmp_path):
    shutil.copytree(ROOT / "fixtures/phase0", tmp_path / "package")
    directory = tmp_path / "package"
    version, checksum, contents = read_package(directory)
    assert version == 2
    assert len([k for k in contents if k.startswith("views/")]) == 9
    assert contents["imported-move.txt"] == (directory / "imported-move.txt").read_text()
    assert read_package(directory)[1] == checksum
    (directory / "imported-move.txt").write_text(contents["imported-move.txt"] + "\n")
    assert read_package(directory)[1] != checksum
    (directory / "views/t3-upland.json").write_text(json.dumps({"fixture_version": 1}))
    with pytest.raises(ValueError):
        read_package(directory)


def test_manifest_can_combine_multiple_record_sources_without_source_json(tmp_path):
    shutil.copytree(ROOT / "fixtures/phase0", tmp_path / "package")
    directory = tmp_path / "package"
    package = json.loads((directory / "source.json").read_text())
    split = len(package["records"]) // 2
    for name, records in (
        ("records-a.json", package["records"][:split]),
        ("records-b.json", package["records"][split:]),
    ):
        (directory / name).write_text(
            json.dumps({"fixture_version": package["fixture_version"], "records": records})
        )
    manifest_path = directory / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["source_files"] = ["records-a.json", "records-b.json"]
    manifest_path.write_text(json.dumps(manifest))
    (directory / "source.json").unlink()
    _, _, contents = read_package(directory)
    normalized = json.loads(contents["_records.json"])
    assert len(normalized["records"]) == len(package["records"])
    assert "source.json" not in contents


@pytest.mark.parametrize(
    "environment,database",
    [
        ("test", "living_memory_dev"),
        ("production", "living_memory_dev"),
        ("development", "living_memory_test"),
        ("development", "real_game"),
    ],
)
def test_seed_refuses_wrong_targets(settings, environment, database):
    from pydantic import SecretStr

    changed = settings.model_copy(
        update={
            "environment": environment,
            "database_url": SecretStr(f"postgresql+psycopg://localhost/{database}"),
        }
    )
    db = Database(changed)
    try:
        with pytest.raises(ValueError, match="development database"):
            seed(changed, db, FixedClock(datetime(2030, 1, 1, tzinfo=UTC)))
    finally:
        db.close()
