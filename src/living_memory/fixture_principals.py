"""Compatibility identities for the preserved development acceptance fixture."""

from living_memory.memory import Principal, VisibilityGrant


def legacy_principal(identity: str) -> Principal:
    grants = {
        "reviewer": ("adjudicator", "estuary", "upland"),
        "estuary-lead": ("estuary",),
        "estuary-member": ("estuary",),
        "upland-lead": ("upland",),
        "upland-member": ("upland",),
    }
    if identity not in grants:
        raise PermissionError("Unknown principal")
    return Principal(
        identity=identity,
        grants=tuple(
            VisibilityGrant(game_id="harbor-relief", visibility_scope_id=scope)
            for scope in grants[identity]
        ),
    )
