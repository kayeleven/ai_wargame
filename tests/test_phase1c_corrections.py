# ruff: noqa: F811

"""Phase 1C correction probes against the guarded test database.

Promoted Phase 1C correction regressions; no expected failures.
All trade-policy numbers and events are fictional exercise assumptions.
"""

import hashlib
import json
import os
import re
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr, ValidationError
from sqlalchemy import select
from test_admin_database import database  # noqa: F401

from living_memory.administration import (
    AdminGame,
    ConfigurationRevision,
    ScenarioConfiguration,
    TeamOperationalState,
    activate_game,
    configuration_at,
    create_game,
    revise_game,
)
from living_memory.app import create_app
from living_memory.clocks import FixedClock, GameTime
from living_memory.db import DevelopmentArtifact
from living_memory.identity import (
    GameRole,
    TeamMembership,
    User,
    create_local_user,
    deactivate_user,
    resolve_principal,
)
from living_memory.memory import BranchLineage, MemoryQuery, MemoryReader, load_timeline

NOW = datetime(2040, 1, 1, tzinfo=UTC)
DAY = 86400000000
GAME = "audit-trade-war"


@pytest.fixture
def settings():
    from living_memory.config import Settings

    return Settings(_env_file=None, session_secret=SecretStr("audit-only-secret-" * 4))


def trade_configuration():
    return {
        "teams": [
            {
                "id": "us",
                "name": "United States",
                "actor_ids": ["us-federal"],
                "controllers": [{"kind": "human"}],
            },
            {
                "id": "canada",
                "name": "Canada",
                "actor_ids": ["ca-federal", "ca-provinces"],
                "controllers": [{"kind": "human"}],
            },
        ],
        "actors": [
            {"id": "us-federal", "name": "US federal negotiators"},
            {"id": "ca-federal", "name": "Canadian federal negotiators"},
            {"id": "ca-provinces", "name": "Canadian provincial alcohol authorities"},
        ],
        "rules": [
            "Fictional exercise: 20% US tariff threat; no claim about current law.",
            "Dairy access, automotive quotas, and US alcohol restrictions are negotiable.",
            "Provincial consent is required for the exercise alcohol concession.",
            "Only human-approved effects change state; release feedback separately.",
        ],
        "objectives": {
            "us": [
                "Ease dairy barriers",
                "Change automotive quotas",
                "Ease restrictions on US alcohol goods",
            ],
            "canada": ["Obtain tariff relief", "Protect domestic political support"],
        },
        "resources": [
            {
                "id": "negotiation-capacity",
                "name": "Negotiation capacity points",
                "initial_values": {"us": 10, "canada": 8},
            },
            {
                "id": "dairy-access",
                "name": "Synthetic dairy access index",
                "initial_values": {"us": 20, "canada": 80},
            },
        ],
        "relationships": [
            {
                "id": "alcohol-consent",
                "type": "requires-consent",
                "endpoints": [
                    {"entity_id": "ca-federal", "role": "negotiator"},
                    {"entity_id": "ca-provinces", "role": "authority"},
                ],
            }
        ],
        "turns": [
            {
                "number": n,
                "simulated_duration_minutes": 10080,
                "submission_deadline": (NOW + timedelta(days=n)).isoformat(),
            }
            for n in range(1, 5)
        ],
        "vocabulary": ["tariff", "dairy", "automotive-quota", "alcohol-access"],
    }


@pytest.fixture
def trade(database):
    db, configured = database
    with db.transaction() as session:
        admin = create_local_user(
            session, "audit-admin", "Audit admin", "audit password", NOW, system_admin=True
        )
        us = create_local_user(session, "audit-us", "US negotiator", "audit password", NOW)
        ca = create_local_user(session, "audit-ca", "CA negotiator", "audit password", NOW)
        judge = create_local_user(session, "audit-judge", "Judge", "audit password", NOW)
        game = create_game(
            session,
            GAME,
            "US–Canada tariff bargaining",
            ScenarioConfiguration.model_validate(trade_configuration()),
            admin.id,
            NOW,
        )
        session.add(
            GameRole(
                user_id=judge.id,
                game_id=GAME,
                role="adjudicator",
                granted_at=NOW,
                granted_by=admin.id,
            )
        )
        for user, team in ((us, "us"), (ca, "canada")):
            session.add(
                TeamMembership(
                    user_id=user.id,
                    game_id=GAME,
                    team_id=team,
                    authority="submitter",
                    granted_at=NOW,
                    granted_by=admin.id,
                )
            )
        ids = {"admin": admin.id, "us": us.id, "canada": ca.id, "judge": judge.id}
        session.flush()
        activate_game(session, game, admin.id, NOW)
    return (db, configured, ids)


def test_trade_configuration_timing_revisions_and_deactivation(trade):
    db, _, ids = trade
    with db.transaction() as session:
        game = session.get(AdminGame, GAME)
        assert game.status == "active" and game.current_turn == 1
        config = trade_configuration()
        config["rules"].append("Prospective tariff reduction to 10% at turn 3")
        revised = revise_game(
            session,
            game,
            ScenarioConfiguration.model_validate(config),
            3,
            ids["admin"],
            NOW + timedelta(hours=1),
        )
        session.flush()
        assert configuration_at(session, GAME, NOW, 3).id != revised.id
        assert configuration_at(session, GAME, NOW + timedelta(hours=2), 2).id != revised.id
        assert configuration_at(session, GAME, NOW + timedelta(hours=2), 3).id == revised.id
        player = session.get(User, ids["us"])
        assert resolve_principal(session, player, GAME, NOW).permits(GAME, "us")
        assert not resolve_principal(session, player, GAME, NOW).permits(GAME, "canada")
        deactivate_user(session, player, NOW + timedelta(hours=2), ids["admin"])
        assert not resolve_principal(session, player, GAME, NOW).grants
        assert session.get(TeamOperationalState, (GAME, "us")).blocked
        author = session.get(User, ids["admin"])
        deactivate_user(session, author, NOW + timedelta(hours=3), ids["judge"])
        session.flush()
        assert session.get(ConfigurationRevision, revised.id).author_user_id == ids["admin"]


def login(client):
    page = client.get("/login")
    csrf = re.search('name="csrf_token" value="([^"]+)"', page.text)[1]
    result = client.post(
        "/login",
        data={"csrf_token": csrf, "username": "audit-admin", "password": "audit password"},
        follow_redirects=False,
    )
    assert result.status_code == 303
    return csrf


def test_new_game_adjudicator_has_god_view(trade):
    db, _, ids = trade
    with db.transaction() as session:
        principal = resolve_principal(session, session.get(User, ids["judge"]), GAME, NOW)
        assert principal.permits(GAME, "us") and principal.permits(GAME, "canada")


def test_invalid_configuration_is_recoverable(trade):
    db, configured, _ = trade
    with TestClient(create_app(configured, db, FixedClock(NOW))) as client:
        csrf = login(client)
        response = client.post(
            "/admin/games",
            data={
                "csrf_token": csrf,
                "game_id": "invalid-trade",
                "title": "Keep my values",
                "configuration": "{",
            },
        )
        assert response.status_code == 422, response.text
        assert "Keep my values" in response.text


def test_active_game_cannot_be_reactivated(trade):
    db, configured, _ = trade
    with db.transaction() as session:
        session.get(AdminGame, GAME).current_turn = 3
    with TestClient(create_app(configured, db, FixedClock(NOW))) as client:
        csrf = login(client)
        response = client.post(
            f"/admin/games/{GAME}/activate", data={"csrf_token": csrf}, follow_redirects=False
        )
        assert response.status_code == 409


def test_revision_audit_identifies_its_revision(trade):
    from living_memory.identity import AuditEntry

    db, _, ids = trade
    with db.transaction() as session:
        revision = revise_game(
            session,
            session.get(AdminGame, GAME),
            ScenarioConfiguration.model_validate(trade_configuration()),
            2,
            ids["admin"],
            NOW,
        )
        session.flush()
        entry = session.scalars(
            select(AuditEntry).where(AuditEntry.action == "configuration_revised")
        ).one()
        assert entry.subject_id == str(revision.id)


def test_revised_team_configuration_updates_operational_state(trade):
    db, _, ids = trade
    with db.transaction() as session:
        game = session.get(AdminGame, GAME)
        game.status, game.current_turn = ("draft", 0)
        config = trade_configuration()
        config["teams"].append(
            {
                "id": "province",
                "name": "Provincial delegation",
                "actor_ids": ["ca-provinces"],
                "controllers": [{"kind": "human"}],
            }
        )
        config["teams"][1]["actor_ids"] = ["ca-federal"]
        config["objectives"]["province"] = ["Negotiate alcohol access"]
        for resource in config["resources"]:
            resource["initial_values"]["province"] = 0
        with pytest.raises(ValueError, match="Roster"):
            revise_game(
                session,
                game,
                ScenarioConfiguration.model_validate(config),
                1,
                ids["admin"],
                NOW + timedelta(hours=1),
            )
        session.flush()
        assert session.get(TeamOperationalState, (GAME, "province")) is None


def test_unknown_configuration_field_is_rejected():
    config = trade_configuration()
    config["initial_state"] = {"us_tariff_percent": 20, "automotive_quota": 100}
    with pytest.raises(ValidationError):
        ScenarioConfiguration.model_validate(config)


@pytest.mark.parametrize("mode", ["baseline", pytest.param("search"), pytest.param("direct")])
def test_trade_memory_visibility_history_search_and_relationships(trade, mode):
    db, configured, ids = trade
    base = NOW.isoformat()
    late = (NOW + timedelta(days=2)).isoformat()
    scopes = ("us", "canada", "adjudicator")

    def record(identifier, kind, body, visible=scopes, **extra):
        return {
            "id": identifier,
            "kind": kind,
            "game_id": GAME,
            "branch_id": "main",
            "valid_from": 0,
            "recorded_at": base,
            "body": body,
            "disclosures": dict.fromkeys(visible, base),
            **extra,
        }

    records = [
        record(
            "tariff-threat",
            "intent",
            {
                "title": "Tariff bargaining package",
                "overall_intention": "Use tariff pressure to negotiate three concessions.",
                "actions": [
                    {
                        "action_id": "us-action",
                        "Title": "Conditional tariff",
                        "Description": "Propose 20% tariffs pending dairy, auto and alcohol deals.",
                        "Intent of Action": "Obtain negotiated concessions",
                        "Anticipated reaction": "Canada may retaliate; this is an expectation.",
                    }
                ],
            },
        ),
        record("dairy-pledge", "commitment", {"text": "Dairy access conditional on tariff relief"}),
        record(
            "auto-capacity",
            "claim",
            {"text": "Automotive quota talks consume negotiation capacity"},
        ),
        record(
            "alcohol-mandate",
            "assumption",
            {"text": "Secret provincial alcohol red line"},
            ("canada", "adjudicator"),
        ),
        record(
            "tariff-effect-v1",
            "effect",
            {"text": "Approved tariff scheduled: 20 percent"},
            stable_id="tariff-effect",
            valid_from=7 * DAY,
        ),
        record(
            "tariff-effect-v2",
            "effect",
            {"text": "Corrected tariff scheduled: 10 percent"},
            stable_id="tariff-effect",
            supersedes="tariff-effect-v1",
            recorded_at=late,
            valid_from=7 * DAY,
            disclosures=dict.fromkeys(scopes, late),
        ),
        record(
            "alcohol-answer",
            "rfi_response",
            {"text": "Provincial consent remains unresolved"},
            disclosures={
                "adjudicator": base,
                "canada": base,
                "us": {"available_at": base, "recorded_at": late},
            },
        ),
    ]
    manifest = {
        "package_id": "audit-trade",
        "label": "Trade audit",
        "game_id": GAME,
        "root_branch_id": "main",
        "relationship_types": [{"id": "conditional-bargain", "label": "Conditional bargain"}],
        "relationship_roles": [
            {"id": role, "label": role} for role in ("pressure", "concession", "authority")
        ],
        "visibility_scopes": [{"id": s, "label": s} for s in scopes],
        "development_principals": [{"id": "audit", "grants": list(scopes)}],
        "checkpoints": [{"id": "start", "label": "Start", "known_at": base, "effective_at": 0}],
        "relationships": [
            {
                "id": "bargain-v1",
                "stable_id": "bargain",
                "type": "conditional-bargain",
                "recorded_at": base,
                "valid_from": 0,
                "disclosures": dict.fromkeys(scopes, base),
                "endpoints": [
                    {"role": "pressure", "target_kind": "record", "target_id": "tariff-threat"},
                    {"role": "concession", "target_kind": "record", "target_id": "dairy-pledge"},
                    {"role": "authority", "target_kind": "record", "target_id": "alcohol-mandate"},
                ],
            }
        ],
    }
    contents = {
        "_manifest.json": json.dumps(manifest),
        "_records.json": json.dumps({"fixture_version": 1, "records": records}),
    }
    checksum = hashlib.sha256(json.dumps(contents, sort_keys=True).encode()).hexdigest()
    dataset_id = uuid4()
    with db.transaction() as session:
        session.add(
            DevelopmentArtifact(
                id=dataset_id,
                package="audit-trade",
                package_version=1,
                checksum=checksum,
                staged_at=NOW,
                contents=contents,
            )
        )
    try:
        assert load_timeline(db, checksum)
        assert not load_timeline(db, checksum)
        with db.transaction() as session:
            us = resolve_principal(session, session.get(User, ids["us"]), GAME, NOW)
            ca = resolve_principal(session, session.get(User, ids["canada"]), GAME, NOW)
        reader = MemoryReader(db, b"audit-cursor-key")

        def read(principal, scope, known=NOW, effective=0, **query):
            return reader.read_memory(
                principal,
                GAME,
                scope,
                BranchLineage(root="main"),
                known,
                GameTime(elapsed_microseconds=effective),
                MemoryQuery(dataset_id=dataset_id, **query),
            )

        early = read(us, "us")
        early_records = {r.id: r for r in early.records}
        assert "alcohol-mandate" not in early_records
        assert "alcohol-answer" not in early_records
        assert "tariff-effect-v2" not in early_records
        assert early_records["tariff-effect-v1"].effective_status == "pending"
        assert all(not r.relationships for r in early.records)
        assert any(r.relationships for r in read(ca, "canada").records)
        assert (
            read(ca, "canada", record_id="tariff-threat", record_types=("intent",))
            .records[0]
            .relationships
        )
        assert (
            read(
                us,
                "us",
                record_id="tariff-effect-v1",
                record_types=("effect",),
                known=NOW + timedelta(days=3),
            )
            .records[0]
            .revision_status
            == "superseded"
        )
        assert (
            read(us, "us", record_id="tariff-effect-v1", record_types=("effect",))
            .records[0]
            .revision_status
            == "current"
        )
        if mode == "baseline":
            with db.transaction() as session:
                session.delete(session.get(GameRole, (ids["judge"], GAME, "adjudicator")))
            with TestClient(create_app(configured, db, FixedClock(NOW))) as client:
                csrf = login(client)
                assert (
                    client.post(
                        "/admin/roles",
                        data={
                            "csrf_token": csrf,
                            "user_id": str(ids["judge"]),
                            "game_id": GAME,
                            "role": "adjudicator",
                        },
                    ).status_code
                    == 200
                )
                params = {
                    "dataset_id": str(dataset_id),
                    "game_id": GAME,
                    "scope_id": "adjudicator",
                    "known_at": NOW.isoformat(),
                    "effective_microseconds": 0,
                    "record_id": "alcohol-mandate",
                }
                assert client.get("/memory", params=params).status_code == 404
                client.post("/logout", data={"csrf_token": csrf})
                assert (
                    client.post(
                        "/login",
                        data={
                            "csrf_token": csrf,
                            "username": "audit-judge",
                            "password": "audit password",
                        },
                    ).status_code
                    == 200
                )
                assert client.get("/memory", params=params).status_code == 200
        assert not read(us, "us", text="secret").records
        with pytest.raises(LookupError):
            read(us, "us", record_id="alcohol-mandate")
        with pytest.raises(PermissionError):
            read(us, "canada")
        future = {r.id: r for r in read(us, "us", NOW + timedelta(days=3), 21 * DAY).records}
        assert "dairy-pledge" in future
        assert "alcohol-answer" in future
        assert future["tariff-effect-v1"].revision_status == "superseded"
        assert future["tariff-effect-v2"].revision_status == "current"
        assert future["tariff-effect-v2"].effective_status == "applicable"
        assert "tariff-effect-v2" not in {r.id for r in read(us, "us").records}
        assert (
            early_records["tariff-threat"].actions[0].anticipated_reaction
            == "Canada may retaliate; this is an expectation."
        )
        if mode != "baseline":
            query = {"text": "20"} if mode == "search" else {"record_id": "tariff-effect-v1"}
            selected = read(us, "us", NOW + timedelta(days=3), 21 * DAY, **query)
            old = next(r for r in selected.records if r.id == "tariff-effect-v1")
            assert old.revision_status == "superseded"
    finally:
        with db.transaction() as session:
            session.delete(session.get(DevelopmentArtifact, dataset_id))


@pytest.mark.parametrize("fail_validation", [False, pytest.param(True)])
def test_populated_backup_restore_access_and_revocation(
    trade, tmp_path, monkeypatch, fail_validation
):
    import subprocess

    from living_memory import backup
    from living_memory.db import Database
    from living_memory.identity import SessionPolicy, issue_session, resolve_session

    db, configured, ids = trade
    with db.transaction() as session:
        token = issue_session(session, ids["us"], NOW, SessionPolicy())
        source_config = configuration_at(session, GAME, NOW, 1).configuration
        source_grants = resolve_principal(session, session.get(User, ids["us"]), GAME, NOW)
    archive = tmp_path / "trade.dump"
    backup.create_backup(db.engine.url.render_as_string(hide_password=False), archive)
    assert archive.stat().st_mode & 511 == 384
    assert archive.with_suffix(".dump.json").stat().st_mode & 511 == 384
    target_name = "audit_phase1c_" + uuid4().hex
    subprocess.run(
        [
            "docker",
            "exec",
            os.environ.get("LM_TEST_DB_CONTAINER", "living_memory-db-1"),
            "createdb",
            "-U",
            "living_memory",
            "-O",
            "living_memory_test",
            target_name,
        ],
        check=True,
    )
    target_url = db.engine.url.set(database=target_name).render_as_string(hide_password=False)
    restored = Database(configured.model_copy(update={"database_url": SecretStr(target_url)}))
    try:
        if fail_validation:
            monkeypatch.setattr(backup, "_verify_domain", lambda database: {"mismatch": True})
            with pytest.raises(backup.RecoveryFailure, match="blocked"):
                backup.restore_backup(target_url, archive)
        else:
            assert backup.restore_backup(target_url, archive) >= 1
        with restored.transaction() as session:
            assert resolve_session(session, token, NOW + timedelta(minutes=1)) is None
            assert configuration_at(session, GAME, NOW, 1).configuration == source_config
            user = session.get(User, ids["us"])
            assert resolve_principal(session, user, GAME, NOW) == source_grants
            assert not resolve_principal(session, user, GAME, NOW).permits(GAME, "canada")
        with pytest.raises(ValueError, match="empty template0"):
            backup.restore_backup(target_url, archive)
    finally:
        restored.close()
        subprocess.run(
            [
                "docker",
                "exec",
                os.environ.get("LM_TEST_DB_CONTAINER", "living_memory-db-1"),
                "dropdb",
                "-U",
                "living_memory",
                target_name,
            ],
            check=True,
        )
