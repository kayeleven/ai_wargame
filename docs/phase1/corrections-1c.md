# Phase 1C bounded correction — 2026-09-11

**Status: bounded correction implemented and verified**, with the explicit deferrals below.

This record supersedes the earlier unqualified 1C-admin completion claim. The local
Phase 1C audit was reviewed against source; its relevant reproductions are now
ordinary tests under `tests/`, rather than ignored `codex/` artifacts.

## Disposition and implemented behavior

| Finding | Correction / remaining boundary |
| --- | --- |
| A01 | Adjudicators derive governing team scopes plus `adjudicator`; only system administrators grant/revoke that role. Existing grants are retained and reported for review. |
| A02 | Recoverable administrative validation and recognized duplicate conflicts preserve non-secret input; commit-time failures are included. |
| A03 | Locked, refreshed draft-to-active transition; replay returns 409 without resetting turns. Completed-game revisions are rejected. |
| A04 | New configuration and pending-access subjects receive UUIDs before audit/alert creation. Historical `None` subjects are not fabricated. |
| A05 | New team/actor/controller topology changes are rejected. Governing-team filtering and transactional team-state reconciliation handle obsolete memberships/state. Roster editing is deferred to 1D/1E. |
| A06 | Unknown configuration keys, including nested keys, are rejected. Starting values use numeric team resources and scenario prose. |
| A07 | Full authorized context determines historical labels, evidence and relationships independently of result filters. Combined record/type filters join once. Search casts match the GIN expression. |
| A08 | An operational recovery schema blocks readiness, data routes and session authentication until restore/revocation/verification succeed. Legacy manifest inventory remains unchanged. |
| A09 | Recommendation creation UI/route removed; existing mappings preserved. Runtime group matching is deferred to organizational identity integration, no later than Phase 5. Manual placement remains available. |
| A10 | Scoped membership changes/removal and role removal, audited with team-state recalculation. Adjudicator changes require a system administrator. |
| A11 | Explicit memory metadata names match deployed constraints; temporal index declared; only the migration-owned search index is excluded from autogeneration and checked separately. |
| A12 | Top-level status and historical verification links now identify this correction record. |
| A13 | Authorized configuration/history/schedule, membership/role, team-state and alert readback, including recipient-only mark-read. Game-admin directory scope is limited to administered games. |

Pending-access requests now permit only pending-to-approved/denied transitions,
with locked status checks and atomic placement. Replays and competing transitions
return 409. Existing request-time permission narrowing and CSRF enforcement remain.

## Compatibility and rollout

Schema head remains `0004`, application backup version remains `0.1.0`, and the
manifest inventory keys/meanings are unchanged. The legacy `adjudicator_scopes`
column is retained but no longer supplies authority. No migration or historical
configuration rewrite is needed.

Before serving existing data, run:

```sh
uv run --locked python scripts/report_phase1c.py
```

The report requires an already migrated schema head `0004` and exits clearly otherwise.
The read-only JSON report identifies incompatible governing/scheduled rosters and
lists retained adjudicator assignments with available provenance for system-admin
review. It does not revoke access automatically. Inspect each reported game;
legacy team ID `adjudicator` yields no memory grants and blocks activation,
revisions and access expansion with 409, while administrative historical readback
and revocation remain available. Incompatible roster corrections require a new
game ID until operational roster editing exists. Historical audit subjects cannot
be reliably reconstructed from `None`; alerts without valid targets have no link.

The current grant convention requires team IDs to match dataset visibility scope
IDs and reserves `adjudicator` for adjudicator-only material. The authenticated
trade regression uses matching game/root/scope identities. Existing configuration-only
browser scenarios do not establish memory projection. Orchid's non-team `observer`
scope remains supported by development principals, not this administration mapping.

Before 1D writes, establish the authoritative admin-game to memory-dataset/root,
visibility, clock and vocabulary projection. Controllers are configurable at game
creation but cannot be reassigned by revisions in this bounded correction. Game
administrators need a system administrator to appoint an adjudicator before
activation. Broader administration UX/version comparisons remain later work.

## Recovery procedure

Install PostgreSQL 16 client tools (`pg_dump`, `pg_restore`) on PATH. Restore only
into an explicit fresh database created from `template0`; never point recovery at
the development or another populated database. Normal restore does not require an
application-schema migration.

The wrapper obtains a per-target advisory lock and commits an empty `lm_recovery`
schema before a single-transaction restore. Its existence is the blocking signal;
application roles read public catalogs and need no schema privileges. Absence is
unblocked; catalog errors fail closed. Liveness/static assets remain available.
Dump and restore exclude this operational schema. Backup of a blocked target is
refused.

Restored sessions are revoked in a committed transaction before schema/domain and
legacy inventory verification. Successful verification drops the entire empty
recovery schema without CASCADE. Exceptions or interruption leave the guard in
place. A blocked-target CLI message instructs disposal and retry in another fresh
database. Do not manually remove the guard to expose an unverified target. An
otherwise empty interrupted target is recognized; application objects prevent
in-place reuse. Recovery does not automatically delete databases.

Manifest row counts are structural checks, not full semantic fingerprints.
Regression drills separately compare configuration and effective permissions.
Recovery objectives, scheduling, production deployment and 1F integrated gameplay
recovery remain open.

## Verification

The required suite includes PostgreSQL, browser and real Docker-backed recovery
checks; unavailable prerequisites fail rather than silently skip acceptance.
`LM_TEST_DB_CONTAINER` overrides the default `living_memory-db-1` recovery-test
container. `LM_TEST_DATABASE_URL` retains the dedicated localhost test-role/database
guard. Browser installation is selected with `PLAYWRIGHT_BROWSERS_PATH` when needed.

```sh
uv run --locked ruff check .
uv run --locked mypy
uv run --locked pytest tests -q
uv run --locked python scripts/verify_phase1c.py
```

The isolated gate copies current tracked/unignored source to a temporary directory,
uses locked dependency resolution, and creates a unique Compose project
and empty volume on a free localhost port. It runs migrations twice, both seeds
twice, the full suite, and restart/persistence checks, then removes only its own
project resources. It retains a transcript under `/tmp/lm-phase1c-gate-*/`.

Legacy compatibility is tested using an archive produced by original source at
`0b781de949e999f36358079ee361f7f1ded5893d`, followed by corrected-code restore and a
second backup/restore generation. Other tests inject restore, revocation,
verification and interruption failures and check guard behavior without schema
USAGE privileges. Alembic comparison is supplemented by catalog assertions for
CHECK definitions and GIN index validity/expression, plus a controlled index
eligibility EXPLAIN. Small fixtures need not naturally choose an index scan.

Catalog inspection confirmed that migration 0004 deployed doubled CHECK-name prefixes
on `admin_game`, `auth_global_role`, `auth_game_role`, and `auth_team_membership`.
Definitions are correct; those harmless deployed names are preserved. Autogeneration
is not treated as a CHECK-name comparison.

The configured development database predates the administration schema, so its
rollout report cannot assess grants yet; it was not migrated or modified by this
correction. Fresh and upgraded isolated databases supply the acceptance evidence.

Final execution results are recorded below. No interactive
latency, end-to-end gameplay, offline provisioning, VDI, or 150-user capacity claim
is made by this correction.


## Final execution evidence — 2026-09-11 UTC

| Check | Result |
| --- | --- |
| Ruff and strict mypy | Passed; 16 application source files checked by mypy. |
| Isolated fresh-copy full suite | **81 passed**, 2 upstream deprecation warnings, 35.18 seconds. Includes JavaScript/no-JavaScript browser controls, original-commit backups, repeated restore, recovery failures, and schema/catalog checks. |
| Final plan-reconciliation additions | **6 passed**, 4 existing cases deselected, 1.29 seconds: denial replay, competing approval/denial with cached rows, and four nested unknown-field cases. No application changes were required. |
| Fresh setup and persistence | Locked dependency setup; migrations twice; both seeds twice; restart preserved both staged artifacts. |
| Cleanup | Gate project container, network, and its uniquely named volume removed. Existing development resources retained. |
| Rollout report | Read-only report exercised on migrated test data; older development schema returns a clear prerequisite message without mutation. |

The final application gate used project `lm_correction_gate_22116fa2f759`.
Its [preserved transcript](evidence/1c-corrections-gate.txt) comes from
`/tmp/lm-phase1c-gate-57zzuqvd/verification.log`. The six supplemental cases were
added during final reconciliation and run separately; the already completed gate
was not repeated because application code was unchanged. Thus 87 distinct current
cases have passing execution evidence, rather than a claim that one gate ran 87.

After the gate, only the standalone rollout reporter's clear older-schema refusal,
its direct verification, supplemental tests, and final documentation were completed.
The earlier failed offline-cache attempt and browser-label failures are not acceptance
evidence; normal locked setup and corrected browser controls passed in the recorded gate.

No commit, deployment, development-database migration, or automatic legacy-grant
revocation was performed. Production rollout still requires schema head 0004 and
operator review of existing configuration/grant compatibility as described above.
