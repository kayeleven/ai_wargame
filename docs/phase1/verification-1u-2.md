# Phase 1U-2 verification

Status: **PR 1 owner-approved; full-suite merge condition satisfied; milestone still implementing**. The full milestone is
not delivered or accepted. The agreed PR sequence, boundaries and gates are in
[usability alignment](usability-alignment.md#agreed-1u-2-pr-delivery-sequence--2026-09-23).
Append later PR evidence here; finalize this same record at the milestone gate.

## Prerequisite — macro extraction

[GitHub PR #2](https://github.com/kayeleven/ai_wargame/pull/2) was reviewed, merged
and its branch deleted by the owner. Exact macro bodies moved to a shared template,
with context imports and no behavior change. Verification: 166 tests passed,
Ruff/mypy and diff whitespace checks passed. Code review found no remaining issues.

## PR 1 — dedicated amendment review

Implementation: [GitHub PR #3](https://github.com/kayeleven/ai_wargame/pull/3).
Targets master independently of the milestone acceptance gate. No submission policy
or schema change. Non-test diff: 638 lines (additions plus deletions, including docs).

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
- Player additions are restricted to the latest completed decision when rejected,
  with its reason and submitted-revision link. It remains visible during a pending
  correction, clears on acceptance, and never resurrects an older rejection after
  an acceptance. Earlier reasons remain in the existing history.
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
- Pre-owner-review full suite: **179 passed, 2 warnings in 137.43s**. Includes every named
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

The owner subsequently completed the walkthrough, keyboard, 200% browser zoom and
narrow-screen checks recorded below. Approval applies to PR 1 only; it does not
constitute acceptance of the later PRs or the overall 1U-2 milestone.

## Later increments

PR 2 must append synthetic migration/backup evidence and an upgrade dry run against
a restored copy of the current development database before merge. PRs 3–4 append
service/HTTP/browser evidence on the milestone branch, incorporating master changes
promptly. The milestone PR finalizes end-to-end evidence and records owner acceptance.

## PR 1 owner review correction — rejection notice

The owner reported the rest of PR #3 passed review, with one required fix: a
rejected revision's notice remained after a later acceptance. The notice now
follows the latest completed amendment decision. Explicit pending rule: retain a
rejection while a later correction is pending; acceptance clears it, including
when another revision subsequently becomes pending. A new rejection replaces the
old notice. The rule is recorded in contracts.md and history is preserved.

Added web regressions cover rejected → pending, rejected → accepted → pending,
replacement by a new rejection and comparison summaries with no actions. Comparison
summaries now omit zero counts; the added/removed-action browser check was updated.
Code review checked descending amendment ordering, pending handling and historical
reason retention. The subsequent owner walkthrough and 200% zoom results are
recorded below.

Correction verification: **30 passed, 2 existing warnings in 31.13s**: all tests in
`tests/test_workspace_web.py`, plus the browser tests
`test_review_complete_comparison_and_literal_rejection`,
`test_review_added_removed_and_unchanged_context`,
`test_shared_conflict_and_amendment_decision` and
`test_rejected_decision_survives_validation` (including ordinary/enhanced variants).
Ruff, mypy (21 source files) and diff whitespace checks passed. The earlier 179-test
full-suite result above predates this correction; the affected suite was rerun here.

## PR 1 owner manual review

Reviewer: project owner · Date: 2026-09-23 · Environment: [browser + version], [OS],
local development server against [database name].

Automated results are recorded above; this section records manual observations only.

| # | Check | Result | Observations |
|---|---|---|---|
| 1 | Player proposes amendment; adjudicator sees it and its changes | Pass | |
| 2 | Adjudicator rejects with reason; player sees rejection and reason after re-login | Pass | |
| 3 | "View rejected revision" link opens the rejected submitted version | [Pass] | Scrolls to Submitted packages; prior version shown as effective. [Rejected version expanded] |
| 4 | Mixed comparison: changed, unchanged, added/removed, cleared field | [Pass] | |
| 5 | Unsaved reason kept on same-page link; warning on other amendment | [Pass] | |
| 6 | Correction pending keeps notice; acceptance clears it; new version effective | [Pass] | |
| 7 | Entry from Home; pending count updates after decision | [Pass] | |
| 8 | Keyboard-only navigation | Pass | Tab order effective through navigation, comparison and decision controls. |
| 9 | 200% browser zoom | Pass | Content remains readable. |
| 10 | Narrow window: Original/Proposed stack | [Pass] | |

Not checked manually: screen reader; no-JavaScript fallback; stale decision from
two concurrent adjudicator sessions (covered by automated tests only).

### Findings and follow-ups

- No blocking findings.
- UX follow-up for PR 4 (UX-50): after a rejection, the player's revision link shows
  the submitted versions but offers no next action. Players need a clear route to
  correct the draft and resubmit. Out of scope for PR 1 by design.

### Decision

PR 1 approved for merge to master: [yes], subject to a full-suite rerun after the
rejection-notice correction. This approves PR 1 only, not 1U-2 milestone acceptance.

### Merge-condition verification

After the rejection-notice correction, the required full-suite rerun passed:
**183 passed, 2 existing dependency deprecation warnings in 140.07s**. Ruff passed,
mypy passed for 21 source files, and diff whitespace checks passed. This satisfies
the owner's recorded full-suite condition for merging PR 1. The owner's manual
observations above are preserved as supplied, including unfilled environment details.
The next increment is PR 2 (effective-version history and preserving backfill);
the 1U-2 milestone acceptance gate remains open.


## PR 2 — Effective-version history and preserving backfill

### Pre-stated real-data prediction (before running the dry run)

The read-only development inventory at schema 0005 contains one submission,
seven content versions and six decisions: four accepted, two rejected.
**Prediction: 5 events = 1 initial + 4 adjudicator_acceptance; 0 events for the
2 rejections.** The upgrade must preserve all existing rows. This is a prediction,
not yet a successful migration result. The original development database must
remain on 0005; upgrade and application smoke run only on restored disposable copies.


### Implementation and review boundaries

Direct-to-master increment: new 0006 migration, append-only effective-version events,
existing initial/acceptance transaction writers, and 0.4.0 backup compatibility.
No B-18 policy, command expectations, confirmation, UI, or lock/time/replay behavior
changes. `immediate_revision` is reserved without a writer. Only UPDATE/DELETE guards
exist; test cleanup has no new reset exception.

Deletion audit: searched application, CLI, seeding, scripts and Makefile. The only
application deletes revoke a game role (`admin_access.py`) or team membership
(`identity.py`). No game, submission or user row deletion path exists. Existing
`db-down` retains volumes. Contracts now record permanent provenance and failed game
cascades; the 1U-4 plan requires deactivation of referenced accounts.

The migration's seven named checks are `initial_provenance`, `version_sequence`,
`amendment_content`, `decision_consistency`, `decision_provenance`, `effective_chain`,
and `submission_state`. Each emits at most five identifiers and has its own abort
case asserting unchanged source rows and revision 0005. Tied-time/inactive-actor
history, populated downgrade refusal, repeat upgrade, transaction rollback, replay,
concurrent winners, relational constraints and restore provenance are also covered.

### Development-data rehearsal — 2026-09-23

Old application pinned to `250033b2495e1049705be8d8eb8d29ead806bd3f` (0.3.0).
Used its backup and guarded restore against disposable template0 database
`lm_1u2_upgrade_1665ce34`, then upgraded with this PR's 0006 migration. The original
`living_memory_dev` stayed on 0005. Private archives and digest report were retained
locally under `/tmp/lm-1u2-rehearsal-d39ce33e` (not committed).

- **Prediction matched: 5 events, 1 initial + 4 adjudicator_acceptance; none for the
  2 rejections.** Source actor/time/decision provenance verification passed.
- Canonical complete-row counts and SHA-256 digests matched for **all 47 old tables**
  before/after migration (excluding `alembic_version`). Baseline was taken after
  old-app restore/session revocation. Repeat `upgrade head` changed no rows.
- New 0.4.0 archive restored successfully into `lm_1u2_roundtrip_8e18adba`. All table
  digests matched except exactly one verified `recovery_sessions_revoked` audit
  entry; all sessions remained revoked. The initial rehearsal assertion incorrectly
  expected the audit table to remain identical. Corrected both the regression test
  and rehearsal to verify this existing restore behavior explicitly, then reran.
- Application smoke used FastAPI TestClient with restored submitter/adjudicator
  sessions against the upgraded copy: workspace and adjudicator pages returned 200;
  ordinary-form amendment proposal and acceptance returned 303; the accepted review
  page returned 200. Proposal kept 5 events; acceptance added **exactly one (5 → 6)**.
  An event UPDATE failed with the append-only diagnostic. No source-database writes.
- Pre-upgrade archive SHA-256:
  `6578b4fdb8e30895005452c816b3d4777a4a8d1831ec532331e8b51da589567d`.
- Upgraded archive SHA-256:
  `464f122db27f7ef77c3255c5009de5d41a3af167ccd554d831891700b60472a2`.

### Automated verification and owner gate

Full suite: **209 passed**, including browser tests (156.96s); two existing
FastAPI/Starlette dependency deprecation warnings. Added an explicit initial-submission
rollback case during final review; final focused history suite: **27 passed**.
Ruff passed; mypy passed for 21 source files; offline lockfile and whitespace checks
passed. Real 0005/0.3.0 archive incompatibility with the new app was also confirmed
before any restore attempt.

Code review pass covered migration/source ordering, ORM/DDL agreement, transactional
writers and replay placement, deletion consequences, exact backup compatibility,
restore failure blocking, and scope. Fixed the round-trip audit assertion and removed
an obsolete legacy-backup comment. No unresolved implementation findings. Migration
SHA-256: `80ff1c74684ed775de9bafea1c28c6c038ebeeff02fb35e3f4c3f827c82e10bf`.
Non-test size is recorded in the PR description, including documentation.
Owner review remains required before merge; this increment does not accept 1U-2.
