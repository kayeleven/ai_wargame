# Developer setup (1A)

The supported development layout is host Python **3.12** with **PostgreSQL 16**
in Docker Compose. One application process serves localhost. This is a development
foundation; seeding does not create a playable game or implement authentication.

## Fresh checkout

Install Make, Python 3.12, uv, Docker Engine, and Compose v2 through your normal host
administration process. Docker must be running and accessible to your account.
Setup reports missing prerequisites and never installs them.

1. Run `make setup` to check prerequisites and synchronize `uv.lock`.
2. Copy `.env.example` to `.env`. Generate the session secret using the command
   in the example and replace the placeholder. Never commit real environment files.
3. Run `make db-up`, `make migrate`, and `make seed`.
4. Run `make dev`; open http://127.0.0.1:8000.
5. Run `make check` and `make test`.
6. Install the browser with `uv run --locked playwright install chromium`.
   On Linux, Chromium also needs its OS libraries; install them via your host
   administrator or the documented Playwright `install-deps chromium` command.
   Run `make test-browser`.

Initial dependency and browser downloads need network access. Runtime shell and
form pages use local HTMX, local CSS, and system fonts. FastAPI's optional
`/docs` and `/redoc` interfaces remain available locally but use the framework's
default CDN assets; they are not required by the application workflow.
Offline provisioning is deferred and is not claimed by this setup.

| Command | Behavior |
| --- | --- |
| `make setup` | Check Python, uv, Docker and Compose; sync locked dependencies. |
| `make db-up` | Start PostgreSQL, wait for its health check; bind 127.0.0.1:5432. |
| `make migrate` | Explicitly upgrade to Alembic head; repeating is safe. |
| `make seed` | Validate and stage both manifest packages and declared files; repeating is a no-op. |
| `make dev` | Serve 127.0.0.1:8000 with reload and safe application request logs. |
| `make check` | Ruff and strict mypy; no files rewritten. |
| `make test` | Unit and actual PostgreSQL integration tests; unavailable DB fails. |
| `make test-browser` | Start an ephemeral server and run Chromium tests. |
| `make db-down` | Stop Compose; retain the named volume. |

## Configuration and database safety

Settings use the `LM_` prefix. `.env.example` lists the normal development
settings. Invalid startup configuration reports field names without values.
Cookies are signed, HttpOnly, SameSite=Lax; production configuration requires
`LM_SECURE_COOKIES=true`. Local HTTP requires false.

The Compose initialization script creates `living_memory_dev` and a separate
`living_memory_test` database with a dedicated test role. That role cannot connect
to the development database. Integration tests accept only localhost,
the exact test database name, and the exact test role; they confirm the actual
database and role before deleting staged test rows. Tests never downgrade or
drop the development schema. `LM_DATABASE_URL` does not select the test target.
For a different local port, set `LM_TEST_DATABASE_URL` to the dedicated test URL.

The initialization SQL runs only on the first creation of the volume. If an
existing volume lacks the test role/database, an administrator can run
`scripts/init-test-db.sql` once; do not delete a volume containing valuable data.
The development database's default credentials are solely for localhost use.

Seeding requires development mode, localhost, the exact
`living_memory_dev` database name, and an engine matching that URL. A package is
staged as original UTF-8 file texts with its fixture version, SHA-256 checksum,
and injected UTC staging time. Source and snapshot envelopes and JSON syntax
are validated, all nine snapshots are required, and duplicate source IDs fail.
The unique package/checksum constraint makes concurrent identical inserts safe.
Changed content creates another immutable staged entry, even if its upstream
fixture version stays the same. No seeded or user-authored game state is overwritten.
This loader is development tooling, separate from future player move import.

## Application conventions

Use `create_app(settings=..., database=..., clock=...)` for explicit dependency
injection. Liveness does not query PostgreSQL. Readiness compares the database's
Alembic heads with the checkout's migration heads and fails on an outage or mismatch.
Startup never runs migrations.

Keep every database unit of work inside one synchronous service call.
`Database.transaction()` owns session creation, commit/rollback, and cleanup.
Return materialized typed application models, release the connection, then render.
Templates must never receive ORM objects or access lazy relationships.
The async demo route only parses forms and renders; it performs no DB operation.

Use `Clock.now()` for UTC recording times. Tests inject `FixedClock`.
`GameTime.elapsed_microseconds` is game-relative simulated time and is never
calculated from the host clock. Request duration uses a separate monotonic timer.

All unsafe application requests use the shared CSRF dependency. Render
`csrf_token` as a hidden field or send `X-CSRF-Token`; HTMX includes the hidden
field automatically. No request content, game data, credentials, or attempted
form values belong in signed cookies. Only CSRF and fixed flash codes are stored
today. Signed cookies are readable, not encrypted.

Bind forms with Pydantic through `bind_form`, explicitly naming repeated fields.
Raw entered strings and repeated-field order survive 422 responses. Root
validation errors use `_form`; field paths identify individual errors.
Ordinary failures render the full page; HTMX failures render the form fragment.
Both 422 and future 409 responses are configured to swap in HTMX. Ordinary
success uses a 303; HTMX success uses `HX-Redirect`. Fixed-code flash messages
are consumed once. The demonstration is registered only in development and
performs no game mutation.

## Resource bounds and diagnostics

Per process: AnyIO has **16 thread tokens**; SQLAlchemy has **8 connections**,
**zero overflow**, **2-second checkout timeout**, **3-second connect timeout**,
**5-second PostgreSQL statement timeout**, and pre-ping enabled. The configurable
positive bounded settings are `LM_THREAD_TOKENS`, `LM_POOL_SIZE`,
`LM_POOL_TIMEOUT`, `LM_CONNECT_TIMEOUT`, and `LM_STATEMENT_TIMEOUT_MS`.
The thread limiter and connection pool are separate controls.
See [Starlette threads](https://www.starlette.io/threadpool/) and
[SQLAlchemy pooling](https://docs.sqlalchemy.org/en/20/core/pooling.html).

Pool exhaustion and database failures produce a recoverable 503 with Retry-After.
Unexpected failures produce a generic 500 with a request ID. JSON request log
records contain server-generated request ID, route pattern, status, elapsed
milliseconds, and DB timeout category. Raw paths, queries, request bodies, SQL
parameters, credentials, and exception strings are excluded. The dev command
disables Uvicorn's access log so raw query strings do not bypass this convention.
Avoid enabling SQL echo or adding sensitive values to diagnostic logs.

Phase 2 inference must use separate worker processes and resource budgets.
Do not hold interactive transactions or consume interactive thread capacity
while waiting for inference.

Troubleshooting: 503 with `schema mismatch` means run `make migrate` against
the intended database. A generic DB 503 means check Compose health, URL, and
pool/statement-timeout category. Liveness remains usable in either case.
A 403 form response means reload to obtain a session/CSRF token; clearing cookies
or rotating the session secret invalidates old forms. A missing browser executable
means run the Playwright installation step.

## Acceptance evidence

See [1A verification](phase1/verification.md) for the executed checks and remaining
host-specific gate. Tests cover real PostgreSQL migrations, versioned staging,
transaction rollback, statement and pool timeout recovery, and schema mismatch.
Browser checks exercise both JavaScript and ordinary form paths, keyboard use,
422/409 rendering, CSRF rejection, one-use flash messages, and local assets.

## Phase 1B memory explorer

After `make migrate`, run `make seed`. The seed command prints the staged package
checksum. Load each exact package explicitly:

```sh
uv run --locked python -m living_memory.cli load-memory --checksum CHECKSUM
```

Run `make dev` and open `/dev/memory`, or follow **Explore memory** on the home
page. Select a development identity first, then dataset, permitted audience,
checkpoint and task view. The reviewer can inspect all three audiences; each
council identity can inspect its council only. Identity switching is deliberately
available for development demonstrations and is not authentication. No explorer
routes are registered in test/production configuration. Browser tests explicitly
run the development configuration against the guarded test database.

The loader requires the localhost development database and an explicit staged
checksum. It is separate from staging and future player move import. Repeated
loads do nothing; changed source packages create separate selectable datasets.
Loading is atomic, preserves original import text, and never uses the nine
snapshot files, variant, answer key, or model examples as runtime inputs. Those
snapshots remain independent test oracles. Foreign-key cascades support isolated
test cleanup; there is no application timeline delete or editing endpoint.

Checkpoints, identities, visibility labels, record types, relationship types and
presets come from the selected dataset manifest. Switching datasets resets
invalid selections deterministically. A post-0003 staged package remains visible
as “reload required” until explicitly rebuilt. Harbor's three named checkpoints
continue to reproduce its T3/review/release tasks.
The service separately accepts UTC knowledge cutoffs and simulated effective time.
Historical revisions stay visible with a superseded label; scheduled records are
pending before their effective interval. A date passing does not apply an effect.
Evidence links retain dataset, identity, audience, checkpoint and task. Inaccessible
and nonexistent targets both return 404. Audience escalation returns 403. Responses
are not cached. Existing generic 503/retry and request-ID diagnostics still apply.

See [1B verification](phase1/verification-1b.md) for evidence and limitations.

Lexical search uses PostgreSQL's language-neutral `simple` dictionary. It does
not stem words, so plural and singular forms may require separate searches.
Pagination cursors are opaque and signed; changing scope, cutoff, effective time,
branch, game, or filters invalidates them. Their composite watermark freezes both
record and relationship ingestion for the entire page sequence. Package
disclosures may use the legacy single timestamp (availability and recording are
equal) or explicit `available_at` and `recorded_at` timestamps. Reads support only
the root branch and one relationship hop in 1C-core.

## Identity, administration, and recovery

After migration, create the first system administrator from an interactive terminal;
the password is read twice without echo and is never accepted as an argument:

```sh
uv run --locked python -m living_memory.cli create-admin --username administrator --display-name "System Administrator"
```

Sign in at `/login` and use `/admin` to create users, provider scopes and exact-group
recommendations, configure games, assign roles and memberships, review pending external
subjects, schedule revisions, and activate games. Administrators have no private memory
access solely because they are administrators. The manifest identity selector remains
available only under `/dev/memory` in development.

Reset a local password with `reset-password --username NAME`; this also revokes every
session for that user. Runtime session cookies are opaque random values whose hashes are
stored in PostgreSQL. Idle and absolute expiry and the username/source throttling bounds
are configured by the `LM_SESSION_*` and `LM_LOGIN_*` values in `.env.example`.

Create a protected custom-format PostgreSQL archive and sidecar manifest with:

```sh
make backup ARCHIVE=/protected/path/living-memory.dump
```

Restore requires a separately created, empty, explicitly named database using the same
server connection settings. It refuses a target with any public tables, verifies archive
checksum and compatibility, restores without owners or ACLs, checks Alembic/domain and
staged-package inventory, then revokes every restored session before returning success:

```sh
make restore ARCHIVE=/protected/path/living-memory.dump TARGET_DATABASE=living_memory_recovery
```

Never make the restore target the current source database. Scheduled backups, retention,
RPO/RTO, and portable domain export remain deferred.
