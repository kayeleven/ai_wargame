# 1A verification — 2026-09-10

Implementation is complete. The application, database, form and browser checks
pass. **The full Docker-based fresh-checkout acceptance gate remains unverified**
because this host has no Docker/Compose installation. Later milestones are
specified in the roadmap and contracts, not implemented by this change.

## Executed evidence

Environment: Linux x86-64, host Python 3.12.3, uv 0.12.12, PostgreSQL 16.15,
Chromium 151.0.7922.34 via Playwright 1.62.0. uv, PostgreSQL executables,
browser binaries and missing browser libraries were downloaded into temporary
directories for verification; host prerequisites were not installed. PostgreSQL
ran on localhost port 55432 with separate development and test databases/roles.
Tests required execution outside the sandbox because socket restrictions stalled
TestClient startup and prevented the PostgreSQL listener.

| Check | Result |
| --- | --- |
| Locked dependency resolution/synchronization | Passed; committed `uv.lock`, public PyPI sources and hashes. |
| Prerequisite checker | Correctly fails with missing tool names; no automatic installation. |
| `make check` | Ruff passed; strict mypy passed for all 8 application modules. |
| `make migrate`, repeated | Passed against PostgreSQL 16; startup never migrates. |
| `make seed`, repeated | Initial run staged the package; repeats reported unchanged. |
| `make test` | **20 passed** (0.96 seconds in final run). |
| `make test-browser` | **3 passed** (3.02 seconds in final run). |
| `git diff --check` | Passed; existing Phase 0 changes preserved. |
| Docker Compose up/health/down/volume persistence | **Not run: Docker unavailable.** |

The final Make invocations used temporary tools on PATH and explicit local
database URLs. Both test groups use the locked project environment.

Unit and HTTP tests cover ordinary and HTMX field/form validation, preservation
of whitespace and repeated-field order, CSRF hidden-field/header handling,
invalid Unicode tokens, session cookie flags, fixed-code flash consumption,
development-route exclusion, local assets/checksum, safe configuration errors,
request IDs, generic unexpected errors and database failure diagnostics.

PostgreSQL tests cover repeat migrations, two-engine concurrent identical staging,
changed package staging, deterministic UTC timestamps, rollback after a flushed
insert, zero checked-out connections afterward, schema mismatch, actual database
connection failure, bounded pool exhaustion and recovery, and server-side
statement timeout with subsequent successful queries. The test URL guard runs
before any reset; the actual database and role are checked before deleting test
artifact rows. Source packages contain all nine snapshots; they are staged
artifacts, not playable or audience-filtered runtime data.

Chromium exercises keyboard entry, the skip link, ordinary forms with JavaScript
disabled, HTMX 422 rendering, 303/HX-Redirect success and one-use flashes, no
external page/asset requests, CSRF rejection, and 409 swapping. The 409 response
is a browser-test stub: actual aggregate conflict handling belongs to 1D.
The browser tests exposed and verified the fix for a skip-link focus layout shift.
These smoke tests do not constitute a full accessibility audit.

The locked Starlette release emits two upstream deprecation warnings for its
HTTPX TestClient adapter and AnyIO alias. They do not fail the test suite.

## Remaining acceptance step

On a host with Make, Python 3.12, uv, Docker and Compose v2, follow
[developer setup](../development.md) from a fresh checkout and empty volume:
setup, database health, migration twice, seed twice, both test commands, shutdown
and restart. Confirm the staged package persists. Do not remove an existing
volume containing user data to perform this check.

No eight-user performance workload was executed in 1A. Test-suite durations are
not interactive latency evidence. The future **“Local eight-user sanity check”**
belongs to 1F and must report host, workload, concurrency, durations, errors,
pool waits and percentiles. This work provides **no 150-user capacity evidence**.
Offline installation, organizational identity, TLS, VDI qualification and
representative OPS-04 deadline-burst testing remain follow-up obligations.

## Phase 1B environment recheck — 2026-09-10

Docker and Compose are now installed (Compose reports v5.5.1), superseding the
previous missing-installation diagnosis. `docker info` still fails with permission
denied on `/var/run/docker.sock`, including outside the sandbox. `sudo -n docker
info` requires a password. The current session therefore cannot run the isolated
fresh-checkout/empty-volume/restart gate. No socket permissions or existing volumes
were changed. An administrator must provide daemon access to the session before
this gate can be completed. Native PostgreSQL evidence is not Docker evidence.
