"""Read-only comparisons of immutable amendment packages, without HTML generation."""

from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from living_memory.workspace_service import ActionView, Package


@dataclass(frozen=True)
class FieldComparison:
    name: str
    label: str
    original: str | None
    proposed: str | None
    changed: bool


@dataclass(frozen=True)
class ActionComparison:
    identity: str
    title: str
    original_position: int | None
    proposed_position: int | None
    status: Literal["added", "removed", "changed", "unchanged"]
    reordered: bool
    fields: list[FieldComparison]


@dataclass(frozen=True)
class AmendmentComparison:
    amendment_id: UUID
    base_version: int
    proposed_version: int
    intention: FieldComparison
    actions: list[ActionComparison]
    counts: dict[str, int]


FIELDS = (
    ("title", "Title"),
    ("description", "Description"),
    ("intent", "Intent of Action"),
    ("anticipated_reaction", "Anticipated reaction"),
)


def compare_amendment(
    amendment_id: UUID,
    base_version: int,
    proposed_version: int,
    original: Package,
    proposed: Package,
    owners: dict[UUID, str],
) -> AmendmentComparison:
    before = {a.action_id: a for a in original.actions if not a.removed}
    after = {a.action_id: a for a in proposed.actions if not a.removed}
    original_positions = {key: i for i, key in enumerate(before, 1)}
    proposed_positions = {key: i for i, key in enumerate(after, 1)}
    # Compare surviving-action ranks so additions/removals alone are not reorders.
    old_ranks = {key: i for i, key in enumerate(k for k in before if k in after)}
    new_ranks = {key: i for i, key in enumerate(k for k in after if k in before)}

    def owner(action: ActionView | None) -> str | None:
        if action is None:
            return None
        if action.owner_user_id is None:
            return "Unassigned"
        return owners.get(action.owner_user_id, "Former teammate")

    actions = []
    counts = dict.fromkeys(("added", "removed", "changed", "unchanged"), 0)
    for key in list(after) + [k for k in before if k not in after]:
        left, right = before.get(key), after.get(key)
        fields = []
        for name, label in FIELDS:
            old = getattr(left.body, name) if left else None
            new = getattr(right.body, name) if right else None
            fields.append(FieldComparison(name, label, old, new, old != new))
        fields.append(
            FieldComparison(
                "owner",
                "Responsible teammate",
                owner(left),
                owner(right),
                (left.owner_user_id if left else None) != (right.owner_user_id if right else None)
                or (left is None) != (right is None),
            )
        )
        reordered = key in old_ranks and old_ranks[key] != new_ranks[key]
        status: Literal["added", "removed", "changed", "unchanged"] = (
            "added"
            if left is None
            else "removed"
            if right is None
            else "changed"
            if reordered or any(f.changed for f in fields)
            else "unchanged"
        )
        subject = right or left
        assert subject is not None
        actions.append(
            ActionComparison(
                key,
                subject.body.title,
                original_positions.get(key),
                proposed_positions.get(key),
                status,
                reordered,
                fields,
            )
        )
        counts[status] += 1
    return AmendmentComparison(
        amendment_id,
        base_version,
        proposed_version,
        FieldComparison(
            "intention",
            "Overall intention",
            original.overall_intention,
            proposed.overall_intention,
            original.overall_intention != proposed.overall_intention,
        ),
        actions,
        counts,
    )
