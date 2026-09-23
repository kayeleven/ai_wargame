# Phase 1U-2 verification

Status: **PR 1 awaiting owner review; overall milestone still implementing**. The full milestone is
not delivered or accepted. The agreed PR sequence, boundaries and gates are in
[usability alignment](usability-alignment.md#agreed-1u-2-pr-delivery-sequence--2026-09-23).
Append later PR evidence here; finalize this same record at the milestone gate.

## Prerequisite — macro extraction

[GitHub PR #2](https://github.com/kayeleven/ai_wargame/pull/2) was reviewed, merged
and its branch deleted by the owner. Exact macro bodies moved to a shared template,
with context imports and no behavior change. Verification: 166 tests passed,
Ruff/mypy and diff whitespace checks passed. Code review found no remaining issues.

## PR 1 — dedicated amendment review

Implementation PR: link to be recorded when opened. Targets master independently
of the milestone acceptance gate. No submission policy or schema change.

- Dedicated adjudicator page selects pending or historical amendments. Comparisons
  use immutable base/proposed submission versions, never current drafts or later
  effective content. Missing source versions show unavailable, without a decision control.
- Changed/added/removed actions and changed fields have local navigation. Full
  original/proposed values, explicit empty/cleared/absent labels and unchanged
  context remain available; surviving-action rank changes identify reordering.
  Historical owner names remain readable after deactivation. Word highlighting
  and a general-purpose comparison abstraction are deliberately deferred.
- Existing accept/reject commands, required reasons, validation, stale-decision
  handling and request-key rules remain. Errors/refresh retain the selected amendment.
- Player additions are restricted to the latest rejection reason and a link opening
  its submitted revision. Earlier reasons remain in the existing history.
- Same-document fragment navigation retains unsaved input and recovery storage.
  Other navigation, reload, Cancel and sign-out keep existing protection.
- Comparison/rejection content is server-rendered and template-escaped. The JS diff
  adds no authored/comparison-content innerHTML path; existing escaped conflict and
  static-markup paths were inspected, not represented as absent.

Finding coverage: UX-49 and dedicated-review portion of UX-51; bounded reason/link
portion of UX-50. Full player states, revision entry, confirmation and B-18 policy
remain for later PRs, so UX-38/43–46/50/51 are not collectively closed here.

## Tests and review evidence

- Pure comparison tests: stable identity despite renames; additions/removals;
  relative reorder versus position shifts; owner identity changes even with equal
  display names; whitespace, clears, complete long replacements and literal text.
- HTTP: scoped selection and denied foreign IDs, default pending selection,
  immutable history despite later edits, inactive owners, missing versions,
  revision links, ordinary/enhanced validation and replay destinations, retained
  ordinary-form stale-decision reasons. Existing authorization and CSRF checks retained.
- Chromium: ordinary/enhanced decisions and player links, changed-action navigation,
  unchanged context, full long fields, narrow stacking and retained dirty reasons.
  HTML/script-like title, field and rejection reason render literally before and
  after enhanced refresh, with no injected elements or script execution.
- Replaced the synthetic two-pending-form test with one selected pending amendment
  alongside real rejected history; scoped error references remain verified.
- Recovery test exposed an existing orphaned-editor retry issue: a reconstructed
  decision retry used a command storage key instead of the original editor key.
  It now retains the original recovery-state identity and removes its recovery
  panel after acknowledgement. Dropped decision response + reload + retry creates
  one decision. Adjacent package/new-action/comment retry and stale-decision tests
  passed (5 focused tests).
- Agent code review completed: checked authorized source selection, literal rendering,
  stable editor/refresh identities, existing command semantics, recovery and scope.
  The orphaned-decision retry finding above was fixed on this branch; no remaining
  actionable findings from that review. This is not an independent owner review.
- Final full suite: **179 passed, 2 warnings in 137.43s**. Includes every named
  1U-1 navigation check below. Ruff passed; mypy passed for 21 source files;
  `git diff --check` passed. Warnings are the existing Starlette/httpx and AnyIO
  deprecations, not new failures.

Reproduction (host access to the dedicated test database and Chromium required):

```sh
PATH=/tmp/lm-pg16-bin:$PATH LD_LIBRARY_PATH=/tmp/lm-pg16-bin .venv/bin/pytest -q
.venv/bin/ruff check .
.venv/bin/mypy
```

The PostgreSQL 16 binaries in `/tmp/lm-pg16-bin` are the previously prepared local
client tools. Permanent host setup remains documented in the development guide.

### Consumed 1U-1 contract and acceptance checks

Affected acceptance: navigation/reload retains recoverable input or warns before
loss; saves/partial updates preserve unrelated authored text. Also recheck the
owner's 1U-1 walkthrough item 2 (Cancel/navigation/reload protection). This PR's
agent/automated checks are not a new owner acceptance report.

The full-suite run passed the following tests in `tests/browser/test_workspace_browser.py`:

- `test_confirmed_rejection_and_keyboard_cancel`
- `test_reload_restores_dirty_text_without_replay_or_cross_user_leak`
- `test_navigation_discard_clears_workspace_recovery_text`
- `test_admin_dirty_form_guards_shell_navigation`
- `test_independent_dirty_editor_survives_save_and_blocks_submission`
- `test_teammate_action_title_is_literal_in_cancel_confirmation`

New fragment tests additionally verify unchanged session storage, preserved reason,
keyboard focus, continued warnings for changed queries/pages and missing/malformed
targets, and reload recovery. No-JavaScript reload warnings remain unavailable and
are not claimed as passing.

### Agent walkthrough and owner review

A temporary test-database-only Chromium walkthrough completed keyboard comparison
navigation and decision submission; live status acknowledged the result. Visual
inspection at 1400px and 390px confirmed labeled side-by-side/stacked values with
complete text. A 700px viewport also reflowed without horizontal overflow; this
is a reduced-viewport check, not a claimed manual browser-zoom or screen-reader test.
Temporary screenshots are under `/tmp/lm-1u2-review-evidence`; they are not durable
repository evidence. Permanent automated coverage is in the tests listed above.

Owner review remains required: enter review from Home, inspect changed and unchanged
content, reject with a reason, follow the player's revision link, and check keyboard,
200% browser zoom and narrow-screen behavior. PR 1 may merge after owner approval;
it does not authorize implementation/acceptance claims for the later PRs.

## Later increments

PR 2 must append synthetic migration/backup evidence and an upgrade dry run against
a restored copy of the current development database before merge. PRs 3–4 append
service/HTTP/browser evidence on the milestone branch, incorporating master changes
promptly. The milestone PR finalizes end-to-end evidence and records owner acceptance.
