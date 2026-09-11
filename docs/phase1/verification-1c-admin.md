# 1C-admin verification — 2026-09-11

> Historical record. Current status, corrected behavior, gate evidence and accepted
> deferrals are in [Phase 1C corrections](corrections-1c.md). Original results below are preserved.

Phase 1C-admin is **implemented and accepted**. Native PostgreSQL, HTTP, Chromium,
backup/restore, and the isolated fresh-copy Docker gate all pass.

## Implemented scope

- Durable UUID users, separately stored Argon2id credentials, normalized usernames,
  deactivation with preserved authorship, opaque hashed server-side sessions, rotation,
  expiry and revocation, generic failures, and durable two-bound throttling.
- Global and game roles, separate team authority, request-time principal derivation,
  immediate grant narrowing, submitter blocking/alerts, and diagnostics that separate
  principal resolution, memory query, and total request duration without sensitive labels.
- Provider-scoped immutable external subjects, exact group recommendations, a fake-provider
  contract, pending identities with public-only access, administrator alerts, and manual
  placement. Live LDAP networking/TLS remains deliberately deferred.
- CSRF-protected login/logout and administration workflows plus interactive initial-admin
  and password-reset commands that never accept passwords as arguments.
- Validated structured scenarios and immutable revisions with independent `recorded_at`
  and `effective_turn` axes, same-boundary supersession, scheduled future configuration,
  and activation prerequisites.
- Custom-format `pg_dump`/`pg_restore` wrappers with no shell, protected credential
  environment, checksum/version/schema checks, verified-empty targets, staged-package and
  rebuild-state inventory comparison, domain checks, and mandatory recovery revocation.

## Executed evidence

The final evidence run uses Python 3.12.3, PostgreSQL 16.15 on localhost port 55432,
and Chromium 151 through Playwright. The PostgreSQL binaries and browser are temporary
test installations, not Docker evidence.

| Check | Result |
| --- | --- |
| Locked dependency resolution | Passed; Argon2 packages and hashes recorded in `uv.lock`. |
| Ruff and strict mypy | Passed. |
| Alembic upgrade to `0004`, repeated | Passed against PostgreSQL 16. |
| Non-browser suite | Passed: 49 tests. |
| Chromium, JavaScript and no-JavaScript | Passed: 9 tests, including two scenario administration workflows. |
| Populated backup and verified-empty restore | Passed; sidecar checksum/inventory matched. |
| Pre-backup active session after restore | One structurally restored active session was atomically revoked; its prior cookie no longer authenticated. |
| Fresh-copy Docker workflow | Passed with a unique Compose project and empty named volume: setup, health, migration twice, both package stages, 49 tests, 9 browser tests, backup/restore, restart, and two persisted artifacts. |

`alembic check` reports only the pre-existing 1C-core metadata naming/index differences
for `memory_*` objects; it reports no drift for the new `auth_*` or `admin_*` schema.
Repeat upgrade and readiness checks are clean. Normalizing the older declarative metadata
is outside this phase and was not mixed into the administration change.

The two browser scenarios configure Harbor Relief and Orchid Accord with different team
and actor cardinalities, controller mixes, vocabulary, resources, relationships, and turn
durations without application-code changes. Existing temporal memory behavior and the
development-only manifest identity switch remain covered by the unchanged suites.

The gate used host port 55433 to avoid the existing development service. Its temporary
`lm_admin_gate` container, network, and volume were removed afterward; the existing
container and volume were not modified.

## Deferred

Live LDAP bind/network/TLS and certificate validation; email/external notifications;
scheduled backup policy and recovery objectives; player workflow; adjudication; and the
Phase 1F eight-user principal-resolution report remain future work.
