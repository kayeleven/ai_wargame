# ruff: noqa: F811
"""Real legacy archives and interrupted recovery against disposable databases."""

import io
import os
import subprocess
import sys
import tarfile
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import text
from test_admin_database import database  # noqa: F401
from test_phase1c_corrections import GAME, NOW, trade  # noqa: F401

from living_memory import backup
from living_memory.app import create_app
from living_memory.clocks import FixedClock
from living_memory.db import ROOT, Database
from living_memory.identity import issue_session, resolve_session

LEGACY_COMMIT = "0b781de949e999f36358079ee361f7f1ded5893d"


@pytest.fixture
def target_factory(trade):
    db, settings, _ = trade
    container = os.environ.get("LM_TEST_DB_CONTAINER", "living_memory-db-1")
    created = []

    def create():
        name = "lm_correction_" + uuid4().hex
        subprocess.run(
            [
                "docker",
                "exec",
                container,
                "createdb",
                "-U",
                "living_memory",
                "-T",
                "template0",
                "-O",
                "living_memory_test",
                name,
            ],
            check=True,
        )
        url = db.engine.url.set(database=name).render_as_string(hide_password=False)
        configured = settings.model_copy(update={"database_url": SecretStr(url)})
        target = Database(configured)
        created.append((name, target))
        return url, target, configured

    yield create
    for name, target in reversed(created):
        target.close()
        subprocess.run(
            ["docker", "exec", container, "dropdb", "-U", "living_memory", name], check=True
        )


def test_original_archive_and_second_generation_restore(trade, target_factory, tmp_path):
    db, _, _ = trade
    legacy = os.environ.get("LM_LEGACY_SOURCE")
    if legacy:
        checkout = Path(legacy)
    else:
        checkout = tmp_path / "legacy"
        checkout.mkdir()
        archived = subprocess.run(
            ["git", "archive", LEGACY_COMMIT, "src"], cwd=ROOT, check=True, capture_output=True
        ).stdout
        with tarfile.open(fileobj=io.BytesIO(archived)) as archive:
            archive.extractall(checkout, filter="data")
    output = tmp_path / "original.dump"
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(checkout / "src")
    environment["LM_RECOVERY_SOURCE"] = db.engine.url.render_as_string(hide_password=False)
    subprocess.run(
        [
            sys.executable,
            "-c",
            "import os,sys; from pathlib import Path; "
            "from living_memory.backup import create_backup; "
            "create_backup(os.environ['LM_RECOVERY_SOURCE'], Path(sys.argv[1]))",
            str(output),
        ],
        cwd=checkout,
        env=environment,
        check=True,
    )
    url, target, _ = target_factory()
    backup.restore_backup(url, output)
    assert target.ready() and not target.recovery_blocked()
    second = tmp_path / "second.dump"
    backup.create_backup(url, second)
    next_url, next_target, _ = target_factory()
    backup.restore_backup(next_url, second)
    assert next_target.ready() and not next_target.recovery_blocked()
    with target.transaction() as a, next_target.transaction() as b:
        assert a.scalar(
            text("SELECT configuration FROM admin_configuration_revision LIMIT 1")
        ) == b.scalar(text("SELECT configuration FROM admin_configuration_revision LIMIT 1"))


@pytest.mark.parametrize("failure", ["restore", "revoke", "verify", "interrupt"])
def test_persistent_guard_and_authentication(trade, target_factory, tmp_path, monkeypatch, failure):
    db, _, ids = trade
    with db.transaction() as session:
        token = issue_session(session, ids["us"], NOW)
    archive = tmp_path / "guard.dump"
    backup.create_backup(db.engine.url.render_as_string(hide_password=False), archive)
    url, target, settings = target_factory()
    assert not target.recovery_blocked()

    def fail(*args, **kwargs):
        if failure == "interrupt":
            raise KeyboardInterrupt()
        raise RuntimeError("injected recovery failure")

    if failure == "restore":
        monkeypatch.setattr(backup, "_run", fail)
    elif failure == "revoke":
        monkeypatch.setattr(backup, "revoke_all_sessions_after_restore", fail)
    else:
        monkeypatch.setattr(backup, "_verify_domain", fail)
    with pytest.raises(KeyboardInterrupt if failure == "interrupt" else backup.RecoveryFailure):
        backup.restore_backup(url, archive)
    assert target.recovery_blocked() and not target.ready()
    with target.transaction() as session:
        assert resolve_session(session, token, NOW) is None
    with TestClient(create_app(settings, target, FixedClock(NOW))) as client:
        for route in ("/", "/login", "/memory", "/admin", "/health/ready"):
            response = client.get(route)
            assert response.status_code == 503
            assert response.headers["X-Request-ID"]
        assert client.get("/health/live").status_code == 200
    with pytest.raises(ValueError, match="blocked"):
        backup.create_backup(url, tmp_path / "forbidden.dump")


def test_guard_catalog_visibility_and_empty_target_rules(trade, target_factory):
    url, target, settings = target_factory()
    with target.engine.begin() as connection:
        connection.execute(text("CREATE SCHEMA lm_recovery"))
        # PUBLIC has no schema privileges; catalog detection still works as another role.
    other_url = target.engine.url.set(username="living_memory", password="local-development-only")
    other = Database(
        settings.model_copy(
            update={"database_url": SecretStr(other_url.render_as_string(hide_password=False))}
        )
    )
    try:
        from living_memory.db import recovery_blocked

        with other.engine.begin() as connection:
            connection.execute(text("SET LOCAL ROLE pg_read_all_settings"))
            assert not connection.scalar(
                text("SELECT has_schema_privilege('lm_recovery', 'USAGE')")
            )
            assert recovery_blocked(connection)
    finally:
        other.close()
    backup._prove_empty(target)
    with target.engine.begin() as connection:
        connection.execute(text("CREATE VIEW public.unexpected AS SELECT 1 AS value"))
    with pytest.raises(ValueError, match="template0"):
        backup._prove_empty(target)
