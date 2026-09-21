# Phase 1U-1 verification — 2026-09-21

Status: **awaiting owner review**. Automated checks establish the bounded
implementation; they do not constitute owner usability acceptance.

## Delivered behavior

- A shared signed-in shell identifies the user, provides Account and Sign out,
  and routes each user from Home to authorized game work. Player, adjudicator and
  administrator destinations are derived from current memberships and roles.
- Workspace context names the game, team and turn. Browser error pages retain a
  safe route home without disclosing foreign workspace details.
- Editors have independent saved, authored, baseline and pending-command state.
  JavaScript replaces named clean regions while retaining dirty editor DOM, focus,
  selection and text typed during a request. Package-wide commands are blocked until
  dirty or uncertain editors are resolved. No-JavaScript Cancel controls are ordinary
  overview links; JavaScript enhances them with keyboard-operable discard confirmation.
- Stale intention and action commands compare their own immutable baseline scope.
  An unrelated save no longer creates a false conflict; same-action changes still
  do. Submit, amend, reorder and remove retain aggregate checks.
- Successful mutations acknowledge the committed operation before a separate refresh.
  Unknown editor and package-command outcomes retain the exact frozen command and
  original request key across reload; retry never substitutes later typing and stored
  commands are never replayed automatically. Confirmed 401/403/404 failures remain
  distinct; rejection of a retry leaves the earlier unknown command available for
  reconciliation. Existing authorization-before-replay and once-only results remain.
- A committed save whose refresh fails remains committed, exposes a read-only refresh
  retry and blocks package commands until visible baselines are current. A 2xx response
  is acknowledged only when it carries the complete enhanced media contract.
- Conflicts show labelled Base, Current and Mine values with readable teammate names.
  Current, mine and combined recovery are explicit for editable content; aggregate
  commands require review and renewal. Validation messages use field labels and retain
  non-secret comment, decision and reason values.
- The development fixture browser excludes operational datasets before fixture
  parsing. Invalid fixture metadata is isolated as unavailable rather than blocking
  valid fixtures.
- Production templates use shared semantic visual tokens, focus treatment,
  accessible status regions and responsive wrapping.

## Contracts and later dependencies

The editor contract consists of stable editor identity, authoritative and authored
values, immutable baseline revision, dirty state, a separately frozen pending command
and a scoped operation result. Clean content and its package-wide baseline advance
together. Dirty content retains its older baseline until save, discard or explicit
recovery. An uncertain operation pauses other mutations in that browser tab; database
locking and conflict checks govern other tabs. Unavailable session storage falls back
to in-page retention with a visible warning.

1U-2 consumes request-key reconciliation and must add the B-18 confirmation and
effective-version history as one preserving change. 1U-3 consumes editor identity
and clean-region refresh for teammate updates. Administration writes still lack
request keys; 1U-4/5 must define operation-specific reconciliation before applying
the shared unknown-outcome presentation to those writes.

Authenticated Memory navigation is deferred. The operational dataset currently has
no application projection writers, so 1U-1 does not advertise an empty destination.

## Automated evidence

- Service tests cover independent intention/action saves, same-action conflicts,
  missing history, replay after target removal, authorization, aggregate submission
  and rollback.
- HTTP tests cover legacy and enhanced response contracts, stable new-action identity,
  readable conflict/validation data, confirmed rejection statuses, authorized entry,
  exact Home destinations, shell controls and equivalent denied resources.
- Chromium tests cover JavaScript and ordinary-form drafting/submission, explicit
  conflict recovery for intention, action, package and decision state, retained
  validation values, typing during an in-flight save and baseline advancement,
  exact once-only retry after a dropped response, reload and user isolation, blocked
  storage, unreadable acknowledgements, post-commit refresh failure, package-command
  recovery, same-tab mutation exclusion, removed-editor copy/discard recovery,
  latest-authoritative discard, removed-action conflicts in enhanced and ordinary
  forms, frozen retry destinations, dirty-submission blocking, keyboard Cancel and
  amendment decisions. Dropped acknowledgements for new actions and comments prove
  one durable result after exact retry. Administration forms retain their existing
  dirty navigation/reload protection. Explicit navigation discard clears recovery
  text, and schema-invalid ordinary comment/decision forms retain authored values.
  The broader
  browser suite retains the activated-game and
  Harbor/Orchid fixture recovery scenario.
- Final automated run:

  ```text
  PATH=/tmp/lm-pg16-bin:$PATH LD_LIBRARY_PATH=/tmp/lm-pg16-bin .venv/bin/pytest -q
  156 passed, 2 warnings in 105.21s

  .venv/bin/ruff check .
  All checks passed!

  .venv/bin/ruff check --no-respect-gitignore --exclude codex/state codex
  All checks passed!

  .venv/bin/mypy
  Success: no issues found in 20 source files

  UV_CACHE_DIR=/tmp/lm-uv-cache uv lock --check --offline
  Resolved 47 packages in 1ms
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
