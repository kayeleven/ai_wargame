# ruff: noqa: F811
"""Administrative corrections through normal HTTP and transactional services."""

from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from test_admin_database import database  # noqa: F401
from test_phase1c_corrections import GAME, NOW, login, trade, trade_configuration  # noqa: F401

from living_memory.admin_access import review_access, set_role
from living_memory.administration import (
    AdminGame,
    AdministrationConflict,
    ScenarioConfiguration,
    TeamOperationalState,
    activate_game,
    configuration_at,
    revise_game,
)
from living_memory.app import create_app
from living_memory.clocks import FixedClock
from living_memory.identity import (
    AdministratorAlert,
    AuditEntry,
    AuthenticatedSubject,
    GameRole,
    PendingAccessRequest,
    ProviderScope,
    TeamMembership,
    User,
    create_local_user,
    issue_session,
    resolve_or_register_external_identity,
    resolve_principal,
)


def test_forms_grants_readback_and_directory(trade):
    db, settings, ids = trade
    with db.transaction() as session:
        outsider = create_local_user(session, "unrelated-account", "Unrelated", "password", NOW)
        outsider_id = outsider.id
        set_role(session, ids["admin"], GAME, ids["us"], "game_admin", NOW)
        us_token = issue_session(session, ids["us"], NOW)
    with TestClient(create_app(settings, db, FixedClock(NOW))) as client:
        csrf = login(client)
        duplicate = client.post(
            "/admin/users",
            data={
                "csrf_token": csrf,
                "username": "audit-us",
                "display_name": "Preserved",
                "password": "never-echo-this",
            },
        )
        assert duplicate.status_code == 409 and "Preserved" in duplicate.text
        assert "never-echo-this" not in duplicate.text
        assert client.get(f"/admin/games/{GAME}").status_code == 200
        change = f"/admin/games/{GAME}/memberships/{ids['us']}/us/change"
        assert (
            client.post(change, data={"csrf_token": csrf, "authority": "member"}).status_code == 200
        )
        with db.transaction() as session:
            assert session.get(TeamOperationalState, (GAME, "us")).blocked
        client.cookies.set("lm_auth", us_token)
        page = client.get("/admin")
        assert page.status_code == 200 and "unrelated-account" not in page.text
        assert (
            client.post(
                "/admin/roles",
                data={
                    "csrf_token": csrf,
                    "user_id": str(ids["us"]),
                    "game_id": GAME,
                    "role": "adjudicator",
                },
            ).status_code
            == 403
        )
        assert (
            client.post(
                "/admin/memberships",
                data={
                    "csrf_token": csrf,
                    "user_id": str(outsider_id),
                    "game_id": GAME,
                    "team_id": "us",
                    "authority": "member",
                },
            ).status_code
            == 403
        )
        assert client.post("/admin/provider-mappings", data={"csrf_token": csrf}).status_code == 404
        assert (
            client.post(
                f"/admin/games/{GAME}/roles/{ids['us']}/game_admin/remove",
                data={"csrf_token": csrf},
            ).status_code
            == 409
        )
        assert (
            client.post(
                f"/admin/games/{GAME}/memberships/{ids['canada']}/canada/remove",
                data={"csrf_token": csrf},
            ).status_code
            == 200
        )
        with db.transaction() as session:
            assert not resolve_principal(
                session, session.get(User, ids["canada"]), GAME, NOW
            ).grants
            alert = session.scalars(
                select(AdministratorAlert).where(
                    AdministratorAlert.recipient_user_id == ids["admin"]
                )
            ).first()
            assert alert is not None
            alert_id = alert.id
        assert (
            client.post(f"/admin/alerts/{alert_id}/read", data={"csrf_token": csrf}).status_code
            == 404
        )


def pending_subject(session, provider, subject):
    user = resolve_or_register_external_identity(
        session,
        provider,
        AuthenticatedSubject(
            provider_subject=subject, display_attributes={"display_name": subject}
        ),
        NOW,
    )
    session.flush()
    return user, session.scalars(
        select(PendingAccessRequest)
        .where(PendingAccessRequest.status == "pending")
        .order_by(PendingAccessRequest.created_at)
    ).first()


def test_pending_transitions_ids_and_adjudicator_authority(trade):
    db, _, ids = trade
    with db.transaction() as session:
        set_role(session, ids["admin"], GAME, ids["us"], "game_admin", NOW)
        provider = ProviderScope(game_id=GAME, provider="test", created_at=NOW)
        session.add(provider)
        session.flush()
        user, pending = pending_subject(session, provider, "applicant")
        request_id, user_id = pending.id, user.id
        event = session.scalars(
            select(AuditEntry).where(AuditEntry.action == "external_access_requested")
        ).one()
        assert event.subject_id == str(request_id)
        assert all(
            row.subject_id == str(request_id)
            for row in session.scalars(
                select(AdministratorAlert).where(AdministratorAlert.kind == "pending_access")
            )
        )
    with pytest.raises(PermissionError):
        with db.transaction() as session:
            review_access(session, ids["us"], request_id, True, NOW, role="adjudicator")
    with db.transaction() as session:
        assert session.get(PendingAccessRequest, request_id).status == "pending"
        assert session.get(User, user_id).pending
        review_access(
            session, ids["admin"], request_id, True, NOW, team_id="us", role="adjudicator"
        )
    for approve in (True, False):
        with pytest.raises(AdministrationConflict):
            with db.transaction() as session:
                review_access(session, ids["admin"], request_id, approve, NOW)
    with db.transaction() as session:
        assert session.get(PendingAccessRequest, request_id).status == "approved"
        assert session.get(GameRole, (user_id, GAME, "adjudicator")) is not None


def test_activation_refresh_stale_memberships_and_concurrency(trade):
    db, _, ids = trade
    with db.transaction() as session:
        game = session.get(AdminGame, GAME)
        game.status, game.current_turn = "draft", 0
        session.add(
            TeamMembership(
                user_id=ids["us"],
                game_id=GAME,
                team_id="removed-team",
                authority="submitter",
                granted_at=NOW,
                granted_by=ids["admin"],
            )
        )
        session.add(
            TeamOperationalState(
                game_id=GAME, team_id="removed-team", blocked=False, reason="", updated_at=NOW
            )
        )
        session.delete(session.get(TeamOperationalState, (GAME, "us")))

    def activate():
        try:
            with db.transaction() as session:
                activate_game(session, session.get(AdminGame, GAME), ids["admin"], NOW)
            return "activated"
        except AdministrationConflict:
            return "conflict"

    with ThreadPoolExecutor(max_workers=2) as executor:
        assert sorted(executor.map(lambda _: activate(), range(2))) == ["activated", "conflict"]
    with db.transaction() as session:
        obsolete = session.get(TeamOperationalState, (GAME, "removed-team"))
        assert obsolete and obsolete.blocked
        assert obsolete.reason == "Team is not in the governing configuration"
        assert not session.get(TeamOperationalState, (GAME, "us")).blocked
        assert not resolve_principal(session, session.get(User, ids["us"]), GAME, NOW).permits(
            GAME, "removed-team"
        )
        assert (
            session.scalar(
                select(func.count())
                .select_from(AuditEntry)
                .where(AuditEntry.action == "game_activated")
            )
            == 2
        )  # fixture activation plus one transition


def test_legacy_collision_and_controller_revision(trade):
    db, settings, ids = trade
    with db.transaction() as session:
        game = session.get(AdminGame, GAME)
        config = trade_configuration()
        config["teams"][0]["controllers"] = [{"kind": "ai", "reference": "future"}]
        with pytest.raises(AdministrationConflict, match="Roster"):
            revise_game(
                session, game, ScenarioConfiguration.model_validate(config), 2, ids["admin"], NOW
            )
        game.status = "completed"
    with pytest.raises(AdministrationConflict, match="Completed"):
        with db.transaction() as session:
            revise_game(
                session,
                session.get(AdminGame, GAME),
                ScenarioConfiguration.model_validate(trade_configuration()),
                2,
                ids["admin"],
                NOW,
            )
    with db.transaction() as session:
        config = trade_configuration()
        config["teams"][0]["id"] = "adjudicator"
        config["objectives"]["adjudicator"] = config["objectives"].pop("us")
        for resource in config["resources"]:
            resource["initial_values"]["adjudicator"] = resource["initial_values"].pop("us")
        session.get(AdminGame, GAME).status = "draft"
        configuration_at(session, GAME, NOW, 1).configuration = config
    with db.transaction() as session:
        assert not resolve_principal(session, session.get(User, ids["judge"]), GAME, NOW).grants
        assert ScenarioConfiguration.model_validate(
            configuration_at(session, GAME, NOW, 1).configuration
        )
    with TestClient(create_app(settings, db, FixedClock(NOW))) as client:
        csrf = login(client)
        page = client.get(f"/admin/games/{GAME}")
        assert page.status_code == 200 and "reserved" in page.text
        assert (
            client.post(f"/admin/games/{GAME}/activate", data={"csrf_token": csrf}).status_code
            == 409
        )
        assert (
            client.post(
                f"/admin/games/{GAME}/roles/{ids['judge']}/adjudicator/remove",
                data={"csrf_token": csrf},
            ).status_code
            == 200
        )


def test_denied_request_cannot_be_reopened(trade):
    db, _, ids = trade
    with db.transaction() as session:
        provider = ProviderScope(game_id=GAME, provider="denial", created_at=NOW)
        session.add(provider)
        session.flush()
        user, request = pending_subject(session, provider, "denied-applicant")
        request_id, user_id = request.id, user.id
        review_access(session, ids["admin"], request_id, False, NOW)
    for approve in (True, False):
        with pytest.raises(AdministrationConflict):
            with db.transaction() as session:
                review_access(session, ids["admin"], request_id, approve, NOW, team_id="us")
    with db.transaction() as session:
        assert session.get(PendingAccessRequest, request_id).status == "denied"
        assert session.get(User, user_id).pending
        assert session.get(TeamMembership, (user_id, GAME, "us")) is None


def test_competing_pending_reviews_commit_one_outcome(trade):
    from threading import Barrier

    db, _, ids = trade
    with db.transaction() as session:
        provider = ProviderScope(game_id=GAME, provider="competing", created_at=NOW)
        session.add(provider)
        session.flush()
        user, request = pending_subject(session, provider, "competing-applicant")
        request_id, user_id = request.id, user.id
    ready = Barrier(2)

    def review(approve):
        try:
            with db.transaction() as session:
                # Both transactions first cache the pending row; the lock must refresh it.
                cached = session.get(PendingAccessRequest, request_id)
                assert cached.status == "pending"
                ready.wait(timeout=10)
                review_access(session, ids["admin"], request_id, approve, NOW, team_id="us")
            return "approved" if approve else "denied"
        except AdministrationConflict:
            return "conflict"

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(review, (True, False)))
    assert outcomes.count("conflict") == 1
    winner = next(outcome for outcome in outcomes if outcome != "conflict")
    with db.transaction() as session:
        assert session.get(PendingAccessRequest, request_id).status == winner
        assert session.get(User, user_id).pending == (winner == "denied")
        membership = session.get(TeamMembership, (user_id, GAME, "us"))
        assert (membership is not None) == (winner == "approved")
        assert (
            session.scalar(
                select(func.count())
                .select_from(AuditEntry)
                .where(
                    AuditEntry.subject_id == str(request_id),
                    AuditEntry.action.in_(("external_access_approved", "external_access_denied")),
                )
            )
            == 1
        )


@pytest.mark.parametrize("target", ["team", "controller", "resource", "turn"])
def test_nested_unknown_configuration_fields_are_rejected(target):
    from pydantic import ValidationError

    config = trade_configuration()
    objects = {
        "team": config["teams"][0],
        "controller": config["teams"][0]["controllers"][0],
        "resource": config["resources"][0],
        "turn": config["turns"][0],
    }
    objects[target]["unsupported_setting"] = "must not disappear"
    with pytest.raises(ValidationError) as error:
        ScenarioConfiguration.model_validate(config)
    assert any(item["type"] == "extra_forbidden" for item in error.value.errors())
