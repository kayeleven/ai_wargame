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


## PR 3a — Post-lock time, authorization and completed retries

PR 2 merged as GitHub #4 (`db62970`). The pre-agreed size fallback is now active:
combined PR 3 projected ~900 non-test changed lines; PR 3a projected ~405. This PR
branches from master and targets master. No milestone branch exists yet; create it
from master only after PR 3a merges. PR 3 must extend backup.py's expected history
set for `immediate_revision`, including a backup → restore round trip with one present.

### Boundary and intended changes

No submission-policy, confirmation, player UI, schema or backup-format changes.
Existing request fingerprints/results stay compatible. Completed authorized
submit/amend/decide retries return their original result after later edits, turn
advancement or completion. Fresh commands keep current-turn checks. Timestamps
reflect post-lock server time; authority revoked while waiting causes denial.
A replaced submitter's lost response cannot be recovered by their retry: existing
recovery retains that original operation as unknown, rather than issuing a new key.

### Verification

- Service lock tests observe `pg_blocking_pids` before advancing a controlled clock.
  No wall-clock deadline crossing is used. Coverage includes game, user, draft,
  submission and amendment locks; both fresh and completed operations; cached users
  and memberships; membership removal, submitter replacement, adjudicator removal
  and deactivation. SQL lock/statement and harness waits are bounded.
- Service replay tests cover submit/amend/decide after edits, turn advancement and
  completion, mismatched-key content, rejection of fresh stale writes and concurrent
  matching commands. History regression tests retain event/rollback checks.
- Ordinary/enhanced HTTP replays preserve original results and original-turn refresh
  destinations. A transaction retry reads a fresh clock value and leaves one event.
- Browser recovery drops a committed submission response, then advances the turn or
  replaces the submitter. Authorized replay clears pending state and refreshes turn 1;
  replacement denial retains the original key and unknown-outcome recovery state.

Full suite: **246 passed in 178.32s**, including browser coverage; two existing
FastAPI/Starlette dependency deprecation warnings. Ruff, mypy (21 source files),
offline lockfile and whitespace checks passed.

Code review checked lock order, the post-lock clock read, fresh membership loading,
authorization before replay, unchanged fingerprints/results, transactional uniqueness
and rollback, and browser pending-state outcomes. No unresolved findings. No browser
implementation changes were needed. Actual non-test size is recorded in the PR;
it is below the ~405-line projection and the 800-line ceiling.

Owner review is required; this PR does not satisfy the milestone acceptance gate.


### Owner review correction — cached adjudicator authority

The owner identified an identity-map dependency in `resolve_principal`: a retained
`GameRole` could survive revocation and incorrectly authorize a post-lock command.
`blocked_command` now retains the adjudicator role alongside cached users and
memberships. With only that test change, both adjudicator revocation cases (fresh
command and completed retry) failed: **2 failed, 25 deselected in 2.06s**, each because
the expected `LookupError` was not raised.

The role lookup now uses `populate_existing=True`, so the recheck queries the database
regardless of retained ORM references. After the fix, the hardening suite passed:
**27 passed in 14.39s**. Contracts explicitly cover cached user, membership or
adjudicator role. The full suite after the fix passed: **246 passed in 178.29s**,
including browser tests, with the same two existing dependency warnings. Ruff,
mypy (21 source files) and whitespace checks passed. The owner finding is fixed;
the strengthened tests retain the cached role throughout the real lock wait.

## PR 3.1 — Confirmation contract under current policy

PR 3a is merged. The owner created `milestone/1u-2`; this increment targets that
branch, not master. The approved remaining split is recorded in
[usability alignment](usability-alignment.md). Master and milestone both pointed to
`d5cf8a3` at the pre-PR synchronization check; no master changes needed integrating.

### Boundary and evidence

First submissions remain immediately effective and every amendment still requires
adjudicator acceptance. No schema, migration, backup-format or immediate-event
changes. Minimal ordinary/enhanced consequence, deadline and draft-baseline
confirmation is functional now; full package review and lifecycle presentation
remain PR 4. PR 3.2 must implement the immediate-event expected set and explicit
SubmissionVersion contiguity check in `_verify_effective_history`, with a backup →
restore round trip containing an immediate revision.

- `test_workspace_confirmation.py` compares all workspace rows before/after missing
  or stale expectations for submit and amend; neither a request key nor content,
  draft, history or completion records are written. It covers typed JSON, malformed
  deadlines, ordinary renewed confirmation, unchanged draft baselines, current
  before-deadline amendment policy, stored completion replay and legacy fingerprints.
- Delayed-original cases hold key A until fresh confirmed key B commits, for both
  submit and amend. Releasing A produces a conflict with no additional writes:
  exactly one new content version, no A request record. Thus a no-write confirmation
  response describes that attempt at response time; it does not prove an earlier
  lost request was dropped.
- The real PostgreSQL lock-wait test advances a controlled clock while blocked and
  obtains a no-write re-prompt after crossing the deadline. Existing bounded lock,
  cached-authority, original-turn replay and transaction-retry tests remain active.
- Browser coverage explicitly confirms ordinary/enhanced submissions and amendments.
  A 409 `confirmation_required` never creates an edit-conflict panel, leaves no
  pending/unresolved state or unresolved storage, and preserves unsaved input.
  This also holds after a lost prompt response and reload/retry. Lost committed
  confirmation responses retain the original frozen command; turn-advance recovery
  and replaced-submitter denial remain covered.
- The confirmation panel is server-rendered and template-escaped, inserted through
  DOM parsing/import. This increment adds no authored-content `innerHTML` path.

**Milestone upgrade note:** a stale pre-upgrade tab uses the previous generic 409
handler and shows a conflict panel for `confirmation_required`, without writing.
Reloading obtains the new explicit confirmation flow. This compatibility limitation
must remain in the milestone PR's verification/acceptance evidence.

Code review checked authorization/replay ordering, legacy fingerprint serialization,
validation before request-key claims, atomic completion metadata, immutable confirmed
draft baselines, delayed originals, HTTP result shape compatibility and browser
recovery. The review retained unrelated editor response shapes (no null completion
field) and the saved-message redirect from a standalone confirmation page.
No unresolved findings; owner review remains required.

Full suite: **268 passed in 193.71s**, including Chromium and PostgreSQL coverage;
two existing FastAPI/Starlette dependency deprecation warnings. No xfails.
Ruff, mypy (21 source files), offline lockfile and whitespace checks passed.
Actual non-test size: 319 changed lines (additions plus deletions, including
documentation and the new template), below the ~700 projection and 800-line ceiling.
Owner review and the milestone's final manual acceptance remain pending.

### Owner review correction — readable submission eligibility conflicts

Eligibility conflicts supplied a submission status that the conflict presenter did
not recognize, leaving Current blank. The payload now includes both submission
status and effective version; the presenter labels them and displays "Submitted"
or "Amendment pending". The missing-submission case displays "Not submitted".
Raw status values remain available in the enhanced conflict payload.

The new web regression covers a stale Submit after another tab submits and a stale
amendment command after another proposal becomes pending, in both ordinary and
enhanced responses. It asserts the Current side's labels/values, not merely text
elsewhere on the workspace. Before the fix all four cases failed (**4 failed,
30 deselected in 3.65s**). After the fix the affected web and confirmation suites
passed: **54 passed in 34.85s**.

Full suite after the fix: **272 passed in 196.41s**, including browser tests, with
the same two existing dependency deprecation warnings. Ruff, mypy (21 source files),
offline lockfile and whitespace checks passed. Review confirmed the presentation
mapping leaves raw conflict data unchanged and both response modes use the same
labels. The owner's finding is fixed; this update does not merge the PR.

## PR 3.1 owner manual review

Reviewer: project owner · Date: 2026-09-24 · Environment: [browser + version], [OS],
local development server against a freshly recreated development database at schema
0006. Test game created from a two-team configuration with turn deadlines on
2026-09-30, 2026-10-07 and 2026-10-14 (UTC), so first submissions were before the deadline.

Automated results are recorded above; this section records manual observations only.

| # | Check | Result | Observations |
|---|---|---|---|
| 1 | First submission shows confirmation before committing | Pass | Prompt stated effective immediately, before the deadline, current effective version "none" and the deadline. Nothing submitted until Confirm. |
| 2 | Amendment shows confirmation stating approval required | Pass | After Confirm, the amendment appeared pending adjudicator review. |
| 3 | Adjudicator accepts the pending amendment | Pass | Passed after the environment issue below was resolved. |
| 4 | Return to workspace without confirming | Pass | Nothing submitted; draft remained editable. |
| 5 | Stale confirmation (draft saved in another tab, then Confirm) | Pass | [Conflict / renewed prompt]; nothing submitted. |
| 6 | Second submitter's stale Submit after another submission | Pass | Conflict Current side shows "Submitted" (correction above). |
| 7 | Keyboard: prompt receives focus; Confirm and Return reachable by Tab | Pass | |

Not checked manually: deadline crossing during confirmation, lost Confirm responses,
delayed originals and stale pre-upgrade tabs (covered by automated tests only);
screen reader; no-JavaScript confirmation page.

### Environment finding — development database not upgraded to 0006

During check 3, the adjudicator's acceptance and a new first submission failed with
503 and "Save outcome unknown". Amendment proposal succeeded. Cause: the development
database was still at schema 0005. PR 2 deliberately rehearsed 0006 on a restored
copy and left the real upgrade (development.md step 6) to the owner, and that step
had not been performed. Only operations that write effective-version events failed,
because `ws_effective_version_event` did not exist. Startup does not run migrations,
and ordinary requests do not check the schema, so pages loaded normally. The generic
database 503 message did not reveal the mismatch.

Resolution: the development data was disposable test content, so the owner
recreated the database (volume removed, `make db-up`, `make migrate`, `make seed`)
instead of performing the preserving backup-and-upgrade procedure. This was a
deliberate owner decision for non-valuable data. The preserving procedure remains
required for any database whose contents matter. The failed requests had rolled back
without claiming request keys, so no partial writes occurred. This was an
environment issue, not a PR 3.1 defect.

### Findings and follow-ups

- No blocking PR 3.1 findings from the manual review. The eligibility-conflict
  display finding was fixed and verified above.
- Follow-up (separate small PR to master): when schema heads do not match, refuse
  writes with an explicit "schema mismatch, run migrate" response instead of a
  generic database-unavailable 503. Readiness already detects the mismatch;
  ordinary requests do not.
- Process follow-up for the milestone PR checklist: a merged migration requires an
  explicit "development database upgraded or recreated" step, recorded here.
- Carried forward: a stale pre-upgrade tab shows a conflict panel for
  `confirmation_required` without writing (milestone upgrade note above).

### Decision

PR 3.1 approved for merge into `milestone/1u-2`. This approves PR 3.1 only; it
is not milestone acceptance. The basic confirmation presentation is expected to be
replaced in PR 4.

## PR 3.2 — B-18 immediate revisions and recovery

Based on merged PR 3.1 at milestone commit `5fc613b`, targeting `milestone/1u-2`.
No master-only commits needed integration at the initial synchronization check.
Approved projection was approximately 283 non-test changed lines, including docs;
this increment retains the approved smaller policy/recovery boundary.

### Delivered behavior and compatibility

- Revisions strictly before the stored submission deadline take effect immediately,
  without an amendment or adjudicator decision. At/after the deadline they require
  acceptance. Post-lock time governs; existing pending proposals still need decisions.
- Immediate events, immutable content/actions, effective state and stored completion
  commit together. Content allocation includes rejected proposals; effective history
  skips rejected/pending content, but content versions stay contiguous.
- Restore derives immediate provenance independently, checks no source decision and
  a timestamp strictly before the stored deadline, and explicitly checks contiguity.
- APP_VERSION, package version and lock metadata move together to **0.5.0**.
  Schema stays 0006 and archive format stays unchanged. Exact-version rejection
  occurs before restore opens a target. Restore 0.4.0 archives with 0.4.0 first,
  then upgrade the recovered database; never rewrite version fields in manifests.
- Ordinary redirects and enhanced responses use the stored completion consequence:
  “Revision is now effective.” or “Amendment proposed for adjudicator review.”
  Retries retain the original message after the deadline. Legacy completions without
  consequence retain proposal feedback.

### Verification coverage

- Service deadline matrix before/at/after; real PostgreSQL lock waits with bounded
  timeouts and a controlled clock; crossing the deadline writes nothing and requires
  fresh confirmation before creating the pending proposal.
- Ordinary/enhanced HTTP messages and replay after the deadline; immediate event
  actor/time/source, effective state, transaction rollback and concurrent retries.
- Rejected → immediate preserves content sequence `[1, 2, 3]` and effective events
  `[1, 3]`. The 0.5.0 archive round trip preserves domain rows and completion replay.
  Simulated 0.4.0 exact-version checking rejects that archive before target access.
- Same-count corruption tests cover an immediate event at/after the deadline,
  an attached decision reference and a content gap. Timestamp corruption also changes
  immutable content time to match, proving deadline validation independently of
  provenance equality. An invalid deadline archive leaves recovery blocked.
- Existing pre-policy pending proposal permits draft editing, blocks another
  submission before the deadline, and still records adjudicator acceptance.
- Chromium covers ordinary/enhanced messages for both outcomes. Lost-response replay
  additionally checks the enhanced message after the deadline without duplicate writes.

### Known interim wording and owner gate

The **Propose amendment** button and amendment help wording remain until PR 4.
They are a known interim wording issue for immediate revisions; confirmation states
its actual consequence and success/replay feedback is accurate. Full player lifecycle
presentation and package review remain PR 4. Existing no-JavaScript reload recovery
limitations remain unchanged.

Owner verification and approval are pending. Suggested review: submit a revision
before the deadline, observe immediate effect and no adjudicator proposal; repeat
at/after it, reject and correct through the existing workflow; verify both success
messages and retry behavior. Review the matching-version restore instructions.
Do not merge this implementation PR automatically; this is not milestone acceptance.

### Automated checks and implementation review

The first complete run exposed corruption-test schema leakage and deferred-trigger
cleanup, plus an existing exact response-shape assertion for unrelated editor saves.
Corruption-only schema changes now roll back in the same connection after verification;
the new success fields are limited to `amend`. Restored the two affected constraints
only in the dedicated test database. The focused rerun passed **22 tests**, including
schema/catalog parity and both lost-response Chromium scenarios.

Implementation self-review checked transaction ordering, version allocation,
post-lock confirmation/replay, independent restore provenance, exact compatibility,
and ordinary/enhanced response scope. No outstanding implementation findings;
this does not substitute for owner review or milestone acceptance.

Final full suite: **296 passed, 2 warnings in 217.22s**, including PostgreSQL,
backup/restore and Chromium. Existing warnings are Starlette/httpx and AnyIO
deprecations. Ruff, mypy (21 source files) and `git diff --check` passed.
Reproduction uses the same PostgreSQL client PATH/LD_LIBRARY_PATH command above.
Actual non-test size (additions + deletions, including documentation): 221 lines.

## PR 3.2 owner manual review

Reviewer: project owner · Date: 2026-09-24 · Environment: [browser + version], [OS],
local development server against the recreated development database (schema 0006,
application 0.5.0; no migration required). Dedicated test game with a turn 1
deadline of [YYYY-MM-DDTHH:MM:SSZ], about 15 minutes after the start of testing,
so both B-18 paths could be exercised in one session.

Automated results are recorded above; this section records manual observations only.

| # | Check | Result | Observations |
|---|---|---|---|
| 1 | First submission before the deadline | Pass | Confirmation stated effective immediately and before the deadline. |
| 2 | Revision before the deadline is immediate | Pass | Confirmation stated effective immediately; message "Revision is now effective."; version 2 shown as effective; no amendment awaiting adjudicator review. |
| 3 | Revision after the deadline requires approval | Pass | Confirmation stated requires adjudicator acceptance and late; message "Amendment proposed for adjudicator review." |
| 4 | Adjudicator rejects with reason | Pass | Player saw the rejection and reason; version 2 remained effective. |
| 5 | Further proposal accepted | Pass | Content versions contiguous (1, 2, 3 rejected, 4); effective history 1 → 2 → 4. |
| 6 | Deadline crossed while confirming | Pass, with UX finding | Confirm after the deadline wrote nothing and returned a renewed prompt stating approval required. See finding below. |

Not checked manually: exact-deadline boundary, real lock waits, concurrent retries,
restore verification and corrupted-archive rejection (covered by automated tests only);
screen reader; no-JavaScript confirmation page.

Known interim wording, as recorded above: "Propose amendment" button and help text
remain before the deadline, even though the result is an immediate revision. Expected;
replaced in PR 4.

### Findings and follow-ups

- No blocking PR 3.2 findings. Policy, history and messages behaved correctly.
- **UX finding for PR 4 (check 6):** when the deadline passed during confirmation,
  the renewed prompt correctly showed "requires adjudicator acceptance". It did not
  make clear that the consequence had changed since the previous prompt, or that
  nothing had been submitted and the player had to confirm again. It read like the
  same prompt re-displayed. PR 4's confirmation presentation should state the
  change explicitly, for example: "The deadline passed while you were confirming.
  Nothing was submitted. This revision now requires adjudicator acceptance. Confirm
  again to propose it." The server already has both the command's previous
  expectations and the current ones, so the change can be described precisely.
  This applies to any changed expectation (effective version, deadline, late status),
  not just the deadline crossing.

### Decision

PR 3.2 approved for merge into `milestone/1u-2`. This approves PR 3.2 only; it is not
milestone acceptance. The B-18 service policy, confirmation contract, effective-version
history and recovery compatibility are now complete on the milestone branch. PR 4
(player lifecycle presentation) is the remaining implementation increment.
