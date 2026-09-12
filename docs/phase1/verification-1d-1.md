# Phase 1D-1 verification — 2026-09-12

Status: **1D-1 complete; 1D-2 outstanding.** This record covers shared drafting,
submission and explicit amendment decisions. It does not close the full
1D-remainder gate or claim integrated gameplay, rulings, release, or capacity.

## Delivered behavior

- Shared overall intention and ordered actions, optional responsible teammate,
  package/action comments, and immutable package revision history. Removed actions
  remain in history; ownership does not restrict teammate editing.
- Typed incomplete drafts and complete native submission, preserving text and
  ordering. Zero-action packages are valid. Initial submissions snapshot their
  governing deadline and time; late submissions are accepted and marked.
- Separate submit/amend operations, one pending amendment, immutable submitted
  action versions, and a database-backed effective submission version. Adjudicators
  accept/reject with reasons; no speculative closure/ruling flag is present.
- Transactional current authorization, game-before-user and draft aggregate locks,
  expected versions, authorized base/current/submitted conflict recovery, atomic
  request-key replay, and no administrator bypass of player/adjudicator access.
- One designated submitter per team, with explicit atomic administrative replacement,
  including an inactive predecessor. Deactivation still revokes sessions and blocks
  the team; replacing the designation restores submission capability.
- Revised explicit-DDL 0005 baseline and application/backup version 0.3.0. Old
  0005/0.2.0 archives are rejected before restore. Inventory includes Submission,
  CoordinationParticipant, package revisions and all workspace records.

## Checks and evidence

The final full-suite run used Python 3.12, PostgreSQL 16 in the project's local
Compose container, and Playwright Chromium. PostgreSQL client binaries and their
libpq library were copied from that container into `/tmp/lm-pg16-bin` for this host's
recovery tests; they are temporary test tools, not new application dependencies.

```text
PATH=/tmp/lm-pg16-bin:$PATH LD_LIBRARY_PATH=/tmp/lm-pg16-bin .venv/bin/pytest -q
120 passed, 2 warnings in 59.77s

.venv/bin/ruff check .
All checks passed!

.venv/bin/ruff check --no-respect-gitignore --exclude codex/state codex
All checks passed!

.venv/bin/mypy
Success: no issues found in 20 source files

UV_CACHE_DIR=/tmp/lm-uv-cache uv lock --check --offline
Resolved 47 packages

git diff --check
No errors
```

Warnings are existing Starlette/httpx and AnyIO deprecations. No tests were skipped.
The Python checks do not lint HTML or SQL: templates are exercised by HTTP and
Chromium tests; migration DDL is exercised by fresh installation, downgrade/rebuild,
Alembic metadata/catalog checks, and restore. There is no standalone HTML/SQL linter.

| Gate | Application evidence |
| --- | --- |
| Draft/content/history | `test_draft_history_submission_amendment`, `test_order_removal_and_history`, native validation/zero-action tests |
| Immutable submission/amendment | Original snapshots survive later edits and rejected/accepted amendments; deadline snapshots survive a later governing configuration; effective version advances only on acceptance; duplicate action and pending-amendment constraints tested |
| Conflict and replay | Authorized base/current/submitted comparison, original result reference resolves to a preserved record, inactive/noncurrent writes and replays leave no records, identical replay is once-only, changed-key content conflicts, revoked designation denies replay |
| Concurrency and rollback | Concurrent edit/edit, submit/submit, edit/submit, identical requests, amendment decisions, replacement and revocation; failed operations leave no partial history or request-key records |
| Authority | Nonmembers, opposing teams, ordinary administrators and non-adjudicators denied; nonexistent and foreign action references return equivalent failures; deactivation/replacement restores authority correctly |
| Browser workflow | Plain forms and HTMX: draft/submit smoke, two teammates resolve a conflict, submitter proposes an amendment, adjudicator accepts it; rejecting with a missing reason retains Reject after validation; no coordination/RFI/import affordances |
| Schema and recovery | Fresh revised 0005 installs; Alembic metadata matches; retained 1D-2 tables start empty; import/action cycle flushes under deferred FKs; old same-head archive rejection and populated current-format backup/restore pass |
| Existing behavior | Existing administration, temporal memory, browser, backup, recovery and schema tests remain passing |

The legacy populated-1B migration test previously left the shared test database at
populated 0004. Its cleanup now restores the empty current baseline in a `finally`
block, preserving its original migration-rejection assertion and isolating later
tests. Existing one-submitter-per-team fixtures needed no authority changes.

## Requirement coverage and remaining scope

PLAY-01 and PLAY-02 are covered for native drafting/submission and team collaboration.
PLAY-05 is covered for separation of drafts, discussion, submission and amendment
approval from world-state effects. These commands do not write framework memory or
canonical world state. OPS-07 and OPS-09 have bounded authorization/recovery evidence.

PLAY-03 coordination, RFI-01/02 submission workflows, and GAME-04 imports remain
1D-2. Their tables and deferrable import relationship are retained without application
writers. Draft-time coordination/RFI links preserving referenced revisions also
belong to 1D-2. PLAY-04 feedback, RFI answers, rulings, effects and release remain 1E;
framework-independent recovery is 1W. No full 1D, 1F, eight-user performance, or
150-user capacity claim is made.

The active current turn is the sole write context; historical turns are read-only.
1E must add ruling lifecycle restrictions when rulings are implemented. The local
baseline rebuild intentionally does not preserve old 0005 databases or archives.

Independent review identified and prompted correction of the amendment decision
select resetting to Accept after a validation error. Plain and HTMX Chromium tests
now choose Reject, omit the reason, retain Reject after the error, and record a
rejected outcome after correction. Desktop and 390-pixel-wide workspace rendering
were also inspected; the narrow view had no horizontal overflow.
