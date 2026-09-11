from datetime import UTC, datetime

import pytest
from argon2 import PasswordHasher
from pydantic import ValidationError

from living_memory.administration import ScenarioConfiguration
from living_memory.identity import (
    AuthenticatedSubject,
    FakeExternalProvider,
    authenticate,
    hash_password,
    normalize_username,
    verify_password,
)


def scenario(team_count=2, duration=1440):
    teams = []
    actors = []
    objectives = {}
    values = {}
    for number in range(team_count):
        team_id = f"team-{number}"
        actor_id = f"actor-{number}"
        teams.append(
            {
                "id": team_id,
                "name": f"Team {number}",
                "actor_ids": [actor_id],
                "controllers": [{"kind": "human"}],
            }
        )
        actors.append({"id": actor_id, "name": f"Actor {number}"})
        objectives[team_id] = ["Respond"]
        values[team_id] = number + 10
    return {
        "teams": teams,
        "actors": actors,
        "rules": ["Joint review"],
        "objectives": objectives,
        "resources": [{"id": "influence", "name": "Influence", "initial_values": values}],
        "relationships": [
            {
                "id": "alignment",
                "type": "aligned-with",
                "endpoints": [
                    {"entity_id": "actor-0", "role": "source"},
                    {"entity_id": "actor-1", "role": "target"},
                ],
            }
        ],
        "turns": [
            {
                "number": number,
                "simulated_duration_minutes": duration,
                "submission_deadline": datetime(2040, 1, number, tzinfo=UTC),
            }
            for number in (1, 2)
        ],
        "vocabulary": ["DIME-FIL"],
    }


def test_username_and_argon2id_passwords():
    assert normalize_username("  ＡdMiN  ") == "admin"
    with pytest.raises(ValueError):
        normalize_username("two words")
    encoded = hash_password("correct horse battery staple")
    assert encoded.startswith("$argon2id$v=19$m=65536,t=3,p=4$")
    assert verify_password(encoded, "wrong") == (False, None)
    assert verify_password(encoded, "correct horse battery staple") == (True, None)
    old = PasswordHasher(time_cost=1, memory_cost=8192, parallelism=1).hash("upgrade me")
    verified, upgraded = verify_password(old, "upgrade me")
    assert verified and upgraded is not None and upgraded.startswith("$argon2id$")


def test_external_provider_contract_uses_immutable_subject():
    expected = AuthenticatedSubject(
        provider_subject="directory-object-4",
        display_attributes={"display_name": "New Name"},
        external_group_ids=("CN=Exact Group,DC=example",),
    )
    provider = FakeExternalProvider({"directory-object-4": expected})
    assert authenticate(provider, {"subject": "directory-object-4"}) == expected
    with pytest.raises(PermissionError):
        authenticate(provider, {"subject": "New Name"})


def test_structured_scenarios_and_validation():
    harbor = ScenarioConfiguration.model_validate(scenario(2, 1440))
    orchid = ScenarioConfiguration.model_validate(scenario(3, 720))
    assert len(harbor.teams) == 2 and len(orchid.teams) == 3
    assert harbor.turns[0].simulated_duration_minutes != orchid.turns[0].simulated_duration_minutes
    invalid = scenario()
    invalid["relationships"][0]["endpoints"][0]["entity_id"] = "missing"
    with pytest.raises(ValidationError):
        ScenarioConfiguration.model_validate(invalid)
    invalid = scenario()
    invalid["turns"][1]["submission_deadline"] = datetime(2039, 1, 1, tzinfo=UTC)
    with pytest.raises(ValidationError):
        ScenarioConfiguration.model_validate(invalid)
