import os
import shutil
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from time import perf_counter

import pytest
from alembic import command
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import func, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError

from living_memory.app import create_app
from living_memory.clocks import FixedClock
from living_memory.config import TEST_DATABASE
from living_memory.db import ROOT, Database, DevelopmentArtifact, migration_config
from living_memory.seed import stage_package

pytestmark = pytest.mark.integration
DEFAULT_TEST_URL = (
    "postgresql+psycopg://living_memory_test:local-test-only@127.0.0.1:5432/living_memory_test"
)


def safe_test_url(raw):
    url = make_url(raw)
    if (
        url.database != TEST_DATABASE
        or url.username != "living_memory_test"
        or url.host not in {"localhost", "127.0.0.1"}
    ):
        raise ValueError("Tests require localhost living_memory_test with its dedicated role")
    return raw


@pytest.fixture
def database(settings):
    raw = safe_test_url(os.environ.get("LM_TEST_DATABASE_URL", DEFAULT_TEST_URL))
    config_settings = settings.model_copy(
        update={
            "environment": "test",
            "database_url": SecretStr(raw),
            "pool_size": 1,
            "pool_timeout": 0.2,
            "statement_timeout_ms": 100,
        }
    )
    db = Database(config_settings)
    # An unavailable DB is a failure, never a silently skipped acceptance gate.
    with db.engine.connect() as connection:
        assert connection.scalar(text("SELECT current_database()")) == TEST_DATABASE
        assert connection.scalar(text("SELECT current_user")) == "living_memory_test"
    config = migration_config()
    with db.engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")
        command.upgrade(config, "head")
        connection.execute(text("DELETE FROM development_artifact"))
    yield db, config_settings
    db.close()


def test_test_database_guard():
    with pytest.raises(ValueError):
        safe_test_url(DEFAULT_TEST_URL.replace("living_memory_test", "living_memory_dev"))


def test_migrations_seed_and_clock(database, tmp_path):
    db, settings = database
    assert db.ready()
    clock = FixedClock(datetime(2032, 4, 2, tzinfo=UTC))
    directory = tmp_path / "package"
    shutil.copytree(ROOT / "fixtures/phase0", directory)
    other = Database(settings)
    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(
                executor.map(lambda engine: stage_package(engine, clock, directory), [db, other])
            )
    finally:
        other.close()
    assert sorted(results) == [False, True]
    with db.transaction() as session:
        artifact = session.scalars(select(DevelopmentArtifact)).one()
        assert artifact.staged_at == clock.now()
        assert artifact.package_version == 1
    with (directory / "imported-move.txt").open("a") as file:
        file.write("\n")
    assert stage_package(db, clock, directory)
    with db.transaction() as session:
        assert session.scalar(select(func.count()).select_from(DevelopmentArtifact)) == 2


def test_rollback_and_pool_cleanup(database):
    db, _ = database
    with pytest.raises(RuntimeError):
        with db.transaction() as session:
            session.add(
                DevelopmentArtifact(
                    package="rollback",
                    package_version=1,
                    checksum="rollback",
                    staged_at=datetime.now(UTC),
                    contents={},
                )
            )
            session.flush()
            raise RuntimeError("rollback")
    with db.transaction() as session:
        assert session.scalar(select(func.count()).select_from(DevelopmentArtifact)) == 0
    assert db.engine.pool.checkedout() == 0


def test_pool_timeout_http_recovery_and_schema_mismatch(database):
    db, settings = database
    with TestClient(create_app(settings, db)) as client:
        with db.engine.connect():
            start = perf_counter()
            assert client.get("/health/ready").status_code == 503
            assert 0.15 <= perf_counter() - start < 1.5
            assert client.get("/health/live").status_code == 200
        assert client.get("/health/ready").status_code == 200
        with db.engine.begin() as connection:
            connection.execute(text("UPDATE alembic_version SET version_num='wrong'"))
        try:
            assert client.get("/health/ready").status_code == 503
            assert client.get("/health/live").status_code == 200
        finally:
            with db.engine.begin() as connection:
                connection.execute(text("UPDATE alembic_version SET version_num='0001'"))
        assert client.get("/health/ready").status_code == 200


def test_statement_timeout_rolls_back(database):
    db, _ = database
    start = perf_counter()
    with pytest.raises(OperationalError):
        with db.transaction() as session:
            session.execute(text("SELECT pg_sleep(1)"))
    assert perf_counter() - start < 0.8
    assert db.ready()
    assert db.engine.pool.checkedout() == 0


def test_database_outage(settings):
    unreachable = settings.model_copy(
        update={
            "database_url": SecretStr(
                "postgresql+psycopg://living_memory_test:x@127.0.0.1:1/living_memory_test"
            ),
        }
    )
    with TestClient(create_app(unreachable)) as client:
        assert client.get("/health/ready").status_code == 503
        assert client.get("/health/live").status_code == 200
