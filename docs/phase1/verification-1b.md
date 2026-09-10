# Phase 1B verification — 2026-09-10

The shared PostgreSQL retrieval slice and development-only readable explorer are
implemented. The outstanding Docker fresh-checkout gate is **blocked by daemon
access**, not closed by the native PostgreSQL checks below.

## Executed evidence

Environment: Linux x86-64, Python 3.12.3, PostgreSQL 16.15 on localhost port 55432,
locked project dependencies, and the existing Playwright Chromium installation.
Tests use the dedicated `living_memory_test` database and role; development CLI
checks use `living_memory_dev`. Socket/browser checks require sandbox escalation.

| Check | Evidence |
| --- | --- |
| Ruff and strict mypy | Passed; 10 source modules type-checked. |
| Full application and Chromium suite | Final `make test`: 33 passed; `make test-browser`: 5 passed. Two existing upstream deprecation warnings. |
| Nine independent oracles | Exact eligible record sets, body contents, source references, kinds, recording times and effective turns match fixture version 2. |
| Temporal access | Before/at 18:00 permit disclosure and 19:00 commitment release; independently late disclosure recording blocks retroactive access. |
| Historical status | Scheduled customs pending at T3; activation, guarantee cancellation, submission amendment and commitment supersession preserve earlier records. |
| Authorization | Forbidden audience selection, forged root, foreign game/dataset, cross-scope rows, direct/embedded references and hidden evidence; hidden/nonexistent direct targets both return 404. |
| Loader | Identical load is a no-op; changed package has separate dataset; invalid supersession rolls back the entire timeline; import text must match its staged artifact. |
| Browser presentation | All nine views with JavaScript on/off; context-preserving evidence links, explicit identity switching, keyboard submission, readable four-field action content, and no external requests. |
| CLI | Migration twice, seed twice, explicit-checksum load twice passed against the local development database. |
| Diff hygiene | `git diff --check` passed. |
| Docker empty-volume/restart gate | Not run: `docker info` receives socket permission denied; `sudo -n docker info` requires a password. |

The foundation schema-mismatch test previously restored a hard-coded `0001` head.
It now restores its actual original head, preserving recovery tests as migrations
advance. All database operations materialize results and release connections before
rendering. Templates receive `RecordSummary` and `ViewContext` models, without raw
source bodies or ORM objects. Dataset listing selects metadata columns only.

## Acceptance mapping

### Visibility-label follow-up — 2026-09-10

`RecordSummary` now carries a required `visibility_label`, displayed on every
record in task lists and direct record pages. Labels read “Visible to Estuary
Council”, “Visible to Upland Council”, or “Visible to adjudicator”, using only
the authorized selected audience. Future authorized audiences without a display
mapping receive “Visible to selected audience”. These describe audience access;
they do not classify records as shared/private or expose other audiences'
disclosure metadata. No migration or fixture revision was needed.

Validation: Ruff, strict mypy and diff checks passed. Running `.venv/bin/pytest
tests` with the dedicated local test database on port 55432 and existing Chromium
installation passed **39 tests** (34 application/integration and 5 browser), with
the same two upstream deprecation warnings. All nine oracle cases assert labels;
a regression check changes Upland's disclosure eligibility and confirms Estuary's
returned record remains identical. Browser checks verify list and direct-page
labels for all nine views with JavaScript on/off. The temporary native PostgreSQL
instance was restarted for this run; the Docker gate remains outstanding.

### Requirement coverage

- **C01/C08, PLAY-01/05:** overall intentions, action order/four-field prose,
  intention-only submissions, import source text and omissions are preserved.
- **C02/C04/C09, MEM-01/02/05:** historical pledges, scheduled/cancelled/active
  effects and amendments are retrievable with their original and later revisions.
- **C05–C07/C10, MEM-04, RFI-04:** named sharing and evidence filtering retain
  audience boundaries; later information cannot enter earlier checkpoints.
- **C03/C11:** the authorized source material is presented for human review;
  automatic conflict/relevance judgments are not implemented or claimed.
- **C12/C13:** configuration variants and model-example execution remain outside
  this milestone. They are not runtime retrieval inputs.

The original version 1 Phase 0 AI walkthrough remains historical evidence.
Version 2 explicitly shares the updated four-credit commitment at release, permits
deductions from authorized facts, and leaves announcement approval pending.
No human usability, AI benefit, eight-user latency or 150-user capacity claim is made.
HTML/CSS have browser coverage, not dedicated static lint or a full accessibility audit.

## Outstanding Docker acceptance procedure

An administrator must make the Docker daemon accessible to this session. Do not
relax socket permissions or delete an existing volume to complete the check.
Once access works, use a separate checkout containing this implementation, a unique
Compose project name, a new named volume and an unused localhost host port. Override
both development/test connection URLs to match that port. Follow the fresh-checkout
instructions in `docs/development.md`: setup, healthy database, migration twice,
seed twice, lint/type checks, application and browser tests. Load the staged
checksum twice as well. Stop and restart the same Compose project **without volume
removal**, and confirm both staged checksum and explorer contents persist.
Record the actual host, Compose/Engine versions and results here before closing
1A's Docker gate. The native PostgreSQL checks above do not substitute for it.
