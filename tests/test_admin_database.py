import os
import re
from datetime import UTC, datetime, timedelta

import pytest
from alembic import command
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import func, select, text
from sqlalchemy.engine import make_url

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
from living_memory.clocks import FixedClock
from living_memory.config import TEST_DATABASE
from living_memory.db import Database, migration_config
from living_memory.identity import (
    AdministratorAlert,
    AuditEntry,
    AuthenticatedSubject,
    AuthSession,
    ExternalIdentityBinding,
    GameRole,
    PendingAccessRequest,
    ProviderScope,
    SessionPolicy,
    TeamMembership,
    authenticate_local,
    create_local_user,
    deactivate_user,
    issue_session,
    remove_membership,
    resolve_or_register_external_identity,
    resolve_principal,
    resolve_session,
    revoke_all_sessions_after_restore,
    rotate_session,
)

pytestmark = pytest.mark.integration
DEFAULT_TEST_URL = (
    "postgresql+psycopg://living_memory_test:local-test-only@127.0.0.1:5432/living_memory_test"
)


@pytest.fixture
def database(settings):
    raw = os.environ.get("LM_TEST_DATABASE_URL", DEFAULT_TEST_URL)
    url = make_url(raw)
    if (
        url.database != TEST_DATABASE
        or url.username != "living_memory_test"
        or url.host not in {"localhost", "127.0.0.1"}
    ):
        raise ValueError("Tests require the dedicated localhost test database")
    configured = settings.model_copy(update={"environment": "test", "database_url": SecretStr(raw)})
    db = Database(configured)
    migration = migration_config()
    with db.engine.begin() as connection:
        migration.attributes["connection"] = connection
        command.upgrade(migration, "head")
        connection.execute(text("DELETE FROM admin_audit_entry"))
        connection.execute(text("DELETE FROM admin_game"))
        connection.execute(text("DELETE FROM auth_login_attempt"))
        connection.execute(text("DELETE FROM auth_user"))
    yield db, configured
    db.close()


def config(rule="Initial rule"):
    return ScenarioConfiguration.model_validate(
        {
            "teams": [
                {
                    "id": f"team-{index}",
                    "name": f"Team {index}",
                    "actor_ids": [f"actor-{index}"],
                    "controllers": [{"kind": "human"}],
                }
                for index in range(2)
            ],
            "actors": [{"id": f"actor-{index}", "name": f"Actor {index}"} for index in range(2)],
            "rules": [rule],
            "objectives": {"team-0": ["One"], "team-1": ["Two"]},
            "resources": [],
            "relationships": [],
            "turns": [
                {
                    "number": index,
                    "simulated_duration_minutes": 1440,
                    "submission_deadline": datetime(2040, 1, index, tzinfo=UTC),
                }
                for index in (1, 2, 3)
            ],
        }
    )


def test_identity_configuration_authorization_and_external_contract(database):
    db, _ = database
    start = datetime(2039, 1, 1, tzinfo=UTC)
    with db.transaction() as session:
        admin = create_local_user(
            session, " Admin ", "System Administrator", "admin password", start, system_admin=True
        )
        player = create_local_user(session, "Player", "Player", "player password", start)
        adjudicator = create_local_user(session, "Judge", "Judge", "judge password", start)
        game = create_game(session, "admin-test", "Admin test", config(), admin.id, start)
        revise_game(session, game, config("Draft replacement"), 1, admin.id, start + timedelta(1))
        session.add_all(
            [
                GameRole(
                    user_id=adjudicator.id,
                    game_id=game.id,
                    role="adjudicator",
                    granted_at=start,
                    granted_by=admin.id,
                ),
                TeamMembership(
                    user_id=player.id,
                    game_id=game.id,
                    team_id="team-0",
                    authority="submitter",
                    granted_at=start,
                    granted_by=admin.id,
                ),
                TeamMembership(
                    user_id=admin.id,
                    game_id=game.id,
                    team_id="team-1",
                    authority="submitter",
                    granted_at=start,
                    granted_by=admin.id,
                ),
            ]
        )

    with db.transaction() as session:
        admin = session.scalars(select(type(admin)).where(type(admin).username == "admin")).one()
        player = session.scalars(
            select(type(player)).where(type(player).username == "player")
        ).one()
        adjudicator = session.scalars(
            select(type(adjudicator)).where(type(adjudicator).username == "judge")
        ).one()
        game = session.get(AdminGame, "admin-test")
        assert game is not None
        activate_game(session, game, admin.id, start + timedelta(2))
        # Administrative status alone never grants private memory.
        assert resolve_principal(session, admin, game.id, start + timedelta(2)).audiences == (
            "team-1",
        )
        assert resolve_principal(session, player, game.id, start + timedelta(2)).audiences == (
            "team-0",
        )
        assert resolve_principal(session, adjudicator, game.id, start + timedelta(2)).audiences == (
            "adjudicator",
            "team-0",
            "team-1",
        )
        revise_game(session, game, config("Future rule"), 2, admin.id, start + timedelta(3))

    with db.transaction() as session:
        assert ScenarioConfiguration.model_validate(
            configuration_at(session, "admin-test", start + timedelta(4), 1).configuration
        ).rules == ("Draft replacement",)
        assert ScenarioConfiguration.model_validate(
            configuration_at(session, "admin-test", start + timedelta(4), 2).configuration
        ).rules == ("Future rule",)
        assert ScenarioConfiguration.model_validate(
            configuration_at(session, "admin-test", start + timedelta(2), 2).configuration
        ).rules == ("Draft replacement",)

        scope = ProviderScope(
            game_id="admin-test", provider="fake-external", created_at=start + timedelta(4)
        )
        session.add(scope)
        session.flush()
        subject = AuthenticatedSubject(
            provider_subject="immutable-directory-id",
            display_attributes={"display_name": "First Name"},
            external_group_ids=("exact-group", "unknown-group"),
        )
        pending_user = resolve_or_register_external_identity(
            session, scope, subject, start + timedelta(4)
        )
        assert pending_user.pending
        assert resolve_principal(session, pending_user, "admin-test", start).grants == ()
        first_id = pending_user.id

    with db.transaction() as session:
        scope = session.scalars(
            select(ProviderScope).where(ProviderScope.game_id == "admin-test")
        ).one()
        repeated = resolve_or_register_external_identity(
            session,
            scope,
            AuthenticatedSubject(
                provider_subject="immutable-directory-id",
                display_attributes={"display_name": "Changed Name"},
                external_group_ids=("changed-group",),
            ),
            start + timedelta(5),
        )
        assert repeated.id == first_id
        request = session.scalars(select(PendingAccessRequest)).one()
        assert request.observed_groups == ["changed-group"]
        assert session.scalar(select(func.count()).select_from(ExternalIdentityBinding)) == 1
        assert session.scalar(select(func.count()).select_from(AdministratorAlert)) >= 1

        player = session.scalars(
            select(type(player)).where(type(player).username == "player")
        ).one()
        token = issue_session(session, player.id, start + timedelta(5), SessionPolicy())
        assert token.encode() not in session.scalars(select(AuthSession.token_hash)).one()

    with db.transaction() as session:
        player = resolve_session(session, token, start + timedelta(5, minutes=1))
        assert player is not None
        replacement = rotate_session(session, token, player.id, start + timedelta(5, minutes=2))
        assert replacement != token
        assert resolve_session(session, token, start + timedelta(5, minutes=3)) is None
        assert resolve_session(session, replacement, start + timedelta(5, minutes=3)) is not None
        membership = session.get(TeamMembership, (player.id, "admin-test", "team-0"))
        assert membership is not None
        remove_membership(session, membership, admin.id, start + timedelta(6))
        deactivate_user(session, player, start + timedelta(6))

    with db.transaction() as session:
        state = session.get(TeamOperationalState, ("admin-test", "team-0"))
        assert state is not None and state.blocked
        assert "No active submitter" in state.reason
        admin = session.scalars(select(type(player)).where(type(player).username == "admin")).one()
        deactivate_user(session, admin, start + timedelta(6))
        other_state = session.get(TeamOperationalState, ("admin-test", "team-1"))
        assert other_state is not None and other_state.blocked
        assert (
            session.scalar(
                select(func.count())
                .select_from(ConfigurationRevision)
                .where(ConfigurationRevision.author_user_id.is_not(None))
            )
            == 3
        )
        judge = session.scalars(select(type(player)).where(type(player).username == "judge")).one()
        issue_session(session, judge.id, start + timedelta(6), SessionPolicy())
        session.flush()
        assert revoke_all_sessions_after_restore(session, start + timedelta(7)) >= 1
        assert (
            session.scalar(
                select(func.count())
                .select_from(AuthSession)
                .where(AuthSession.revoked_at.is_(None))
            )
            == 0
        )

        # Username-focused failures are enforced below the much looser shared-source bound.
        for _ in range(2):
            with pytest.raises(PermissionError, match="Invalid username or password"):
                authenticate_local(
                    session,
                    "judge",
                    "wrong",
                    "shared-vdi",
                    start + timedelta(8),
                    username_limit=1,
                    source_limit=20,
                )
        for username in ("missing-a", "missing-b"):
            with pytest.raises(PermissionError, match="Invalid username or password"):
                authenticate_local(
                    session,
                    username,
                    "wrong",
                    "second-shared-vdi",
                    start + timedelta(8),
                    username_limit=5,
                    source_limit=2,
                )
        with pytest.raises(PermissionError, match="Invalid username or password"):
            authenticate_local(
                session,
                "judge",
                "judge password",
                "second-shared-vdi",
                start + timedelta(8),
                username_limit=5,
                source_limit=2,
            )
        idle_token = issue_session(
            session,
            judge.id,
            start + timedelta(8),
            SessionPolicy(idle=timedelta(minutes=30), absolute=timedelta(days=7)),
        )
        session.flush()
        assert resolve_session(session, idle_token, start + timedelta(8, minutes=30)) is None
        actions = set(session.scalars(select(AuditEntry.action)))
        assert {
            "user_created",
            "game_created",
            "configuration_revised",
            "game_activated",
            "external_access_requested",
            "membership_removed",
            "user_deactivated",
            "recovery_sessions_revoked",
        } <= actions


def test_login_logout_admin_authorization_and_idle_expiration(database):
    db, settings = database
    now = datetime(2039, 2, 1, tzinfo=UTC)
    with db.transaction() as session:
        create_local_user(session, "operator", "Operator", "secret pass", now, system_admin=True)
        create_local_user(session, "ordinary", "Ordinary", "secret pass", now)

    with TestClient(create_app(settings, db, FixedClock(now))) as client:
        login_page = client.get("/login")
        csrf = re.search(r'name="csrf_token" value="([^"]+)', login_page.text)[1]
        failed = client.post(
            "/login",
            data={"csrf_token": csrf, "username": "missing", "password": "secret pass"},
        )
        assert failed.status_code == 401
        assert "Invalid username or password" in failed.text and "missing" in failed.text
        response = client.post(
            "/login",
            data={"csrf_token": csrf, "username": "OPERATOR", "password": "secret pass"},
            follow_redirects=False,
        )
        assert response.status_code == 303
        cookie = response.headers["set-cookie"].lower()
        assert "lm_auth=" in cookie and "httponly" in cookie and "samesite=lax" in cookie
        assert "secret pass" not in cookie
        dashboard = client.get("/admin")
        assert dashboard.status_code == 200 and "Administration" in dashboard.text
        logout_csrf = re.search(r'name="csrf_token" value="([^"]+)', dashboard.text)[1]
        assert client.post("/logout", data={}).status_code == 403
        assert (
            client.post(
                "/logout", data={"csrf_token": logout_csrf}, follow_redirects=False
            ).status_code
            == 303
        )
        assert client.get("/admin", follow_redirects=False).status_code == 303
