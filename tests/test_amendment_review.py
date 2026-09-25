from uuid import uuid4

from living_memory.amendment_review import compare_amendment, compare_packages
from living_memory.workspace_service import ActionText, ActionView, Package


def action(identity, title=None, **values):
    return ActionView(
        id=uuid4(),
        action_id=identity,
        position=0,
        body=ActionText(title=title or identity, description="Original\n text"),
        **values,
    )


def compare(before, after, **kwargs):
    return compare_amendment(uuid4(), 1, 3, before, after, kwargs.get("owners", {}))


def test_identity_renaming_added_removed_unchanged_and_order():
    old = Package(actions=[action("one"), action("two"), action("three")])
    new = Package(actions=[action("new"), action("one", "Renamed"), action("three")])
    result = compare(old, new)
    assert result.base_version == 1 and result.proposed_version == 3
    assert [(a.identity, a.status) for a in result.actions] == [
        ("new", "added"),
        ("one", "changed"),
        ("three", "unchanged"),
        ("two", "removed"),
    ]
    assert result.counts == dict(added=1, removed=1, changed=1, unchanged=1)
    assert not any(a.reordered for a in result.actions)
    assert result.actions[1].original_position == 1
    assert result.actions[1].proposed_position == 2
    assert result.actions[0].fields[0].original is None
    assert result.actions[-1].fields[0].proposed is None
    reordered = compare(old, Package(actions=[old.actions[2], old.actions[0], old.actions[1]]))
    assert all(a.reordered and a.status == "changed" for a in reordered.actions)


def test_complete_values_clearing_whitespace_and_hostile_text():
    original = action("one", "<script>alert(1)</script>")
    long_text = ("New paragraph <img src=x onerror=alert(1)>\n" * 400) + "END"
    revised = original.model_copy(deep=True)
    revised.body = original.body.model_copy(update={"title": "", "description": long_text})
    result = compare(
        Package(overall_intention=" \n", actions=[original]),
        Package(overall_intention="", actions=[revised]),
    )
    assert result.intention.changed and result.intention.original == " \n"
    assert result.intention.proposed == ""
    fields = {f.name: f for f in result.actions[0].fields}
    assert fields["title"].original == "<script>alert(1)</script>"
    assert fields["title"].proposed == "" and fields["title"].changed
    assert fields["description"].original == "Original\n text"
    assert fields["description"].proposed == long_text
    assert not fields["intent"].changed


def test_ownership_uses_identity_even_with_identical_display_names():
    first, second = uuid4(), uuid4()
    old = action("one", owner_user_id=first)
    new = old.model_copy(update={"owner_user_id": second})
    result = compare(
        Package(actions=[old]),
        Package(actions=[new]),
        owners={first: "Same name", second: "Same name"},
    )
    owner = result.actions[0].fields[-1]
    assert owner.changed and owner.original == owner.proposed == "Same name"
    result = compare(Package(actions=[old]), Package(actions=[new]))
    assert result.actions[0].fields[-1].proposed == "Former teammate"
    result = compare(Package(), Package(actions=[action("unassigned")]))
    assert result.actions[0].fields[-1].original is None
    assert result.actions[0].fields[-1].proposed == "Unassigned"


def test_generic_comparison_projects_removed_draft_actions_but_keeps_effective_removals():
    effective = action("effective", "Effective action")
    live_draft = action("live", "Live draft action")
    removed_draft = action("discarded", "Removed draft action", removed=True)

    comparison = compare_packages(
        4,
        9,
        Package(actions=[effective]),
        Package(actions=[live_draft, removed_draft]),
        {},
    )

    assert comparison.base_version == 4 and comparison.proposed_version == 9
    assert [(item.identity, item.status) for item in comparison.actions] == [
        ("live", "added"),
        ("effective", "removed"),
    ]
    assert all(item.identity != "discarded" for item in comparison.actions)
