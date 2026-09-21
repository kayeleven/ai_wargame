# Phase 1U-1 verification — 2026-09-21

Status: **awaiting owner review**. Automated checks establish the bounded
implementation; they do not constitute owner usability acceptance.

## Delivered behavior

- A shared signed-in shell identifies the user, provides Account and Sign out,
  and routes each user from Home to authorized game work. Player, adjudicator and
  administrator destinations are derived from current memberships and roles.
- Workspace context names the game, team and turn. Browser error pages retain a
  safe route home without disclosing foreign workspace details.
- Editors have independent dirty state and explicit save boundaries. JavaScript
  saves refresh the authoritative document while restoring unrelated dirty fields.
  Package-wide commands are blocked until dirty or uncertain editors are resolved.
- Stale intention and action commands compare their own immutable baseline scope.
  An unrelated save no longer creates a false conflict; same-action changes still
  do. Submit, amend, reorder and remove retain aggregate checks.
- Unknown workspace outcomes retain the original request key and are labelled as
  retries that may perform the original command. Stored commands are never replayed
  automatically. Existing authorization-before-replay and once-only results remain.
- The development fixture browser excludes operational datasets before fixture
  parsing. Invalid fixture metadata is isolated as unavailable rather than blocking
  valid fixtures.
- Production templates use shared semantic visual tokens, focus treatment,
  accessible status regions and responsive wrapping.

## Contracts and later dependencies

The editor contract consists of stable editor identity, authored values, immutable
baseline revision, dirty/pending state and a scoped operation result. Clean content
and its package-wide baseline advance together. Dirty content retains its older
baseline until save, discard or explicit recovery. An uncertain operation pauses
other mutations in that browser tab; database locking and conflict checks govern
other tabs.

1U-2 consumes request-key reconciliation and must add the B-18 confirmation and
effective-version history as one preserving change. 1U-3 consumes editor identity
and clean-region refresh for teammate updates. Administration writes still lack
request keys; 1U-4/5 must define operation-specific reconciliation before applying
the shared unknown-outcome presentation to those writes.

Authenticated Memory navigation is deferred. The operational dataset currently has
no application projection writers, so 1U-1 does not advertise an empty destination.

## Automated evidence

- Service tests cover independent intention/action saves, same-action conflicts,
  missing history, replay, authorization, aggregate submission and rollback.
- HTTP tests cover authorized workspace entry, role-specific Home destinations,
  shell account controls, equivalent denied resources and retained form errors.
- Chromium tests cover JavaScript and ordinary-form drafting/submission, dirty input
  preservation, dirty-submission blocking, conflict recovery, amendment decisions
  and fixture browsing with an activated operational game alongside Harbor/Orchid.
- Final automated run:

  ```text
  PATH=/tmp/lm-pg16-bin:$PATH LD_LIBRARY_PATH=/tmp/lm-pg16-bin .venv/bin/pytest -q
  124 passed, 2 warnings in 62.17s

  .venv/bin/ruff check .
  All checks passed!

  .venv/bin/mypy
  Success: no issues found in 20 source files

  UV_CACHE_DIR=/tmp/lm-uv-cache uv lock --check --offline
  Resolved 47 packages
  ```

The warnings are the existing Starlette/httpx and AnyIO deprecations. PostgreSQL
16 client binaries and libpq were copied from the local Compose container into
`/tmp/lm-pg16-bin` for recovery tests; they are temporary test tools.

## Acceptance adjustment and limitations

Without JavaScript, one scoped editor is opened from the overview at a time. A
successful save returns to the overview, where package commands operate on the
visible saved revision. Tests cover isolated saves and retained validation values.
A no-JavaScript reload cannot trigger an application-controlled dirty warning; this
is B-18's recorded limitation and is not claimed as passing.

1U-1 does not implement automatic teammate refresh, the B-18 revision policy,
effective-version events, action-volume navigation, account management or guided
setup. Existing amendment behavior remains until 1U-2.

## Owner review

The owner should perform unaided player and adjudicator navigation from Home,
including pending-review discovery and sign-out; then review independent saves,
same-action recovery, dirty-submission blocking and unknown-outcome wording. The
review should also inspect keyboard/focus behavior, announcements, 200% zoom,
narrow layouts, long text and recovered Harbor/Orchid fixture search. Record the
outcomes here before changing the milestone to accepted.
