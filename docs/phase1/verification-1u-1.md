# Phase 1U-1 verification — 2026-09-21

Status: **accepted following owner review — 2026-09-23**. Owner outcomes and
the bounded warning-label correction are recorded below. Automated evidence is
distinct from the owner-reported usability passes.

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
  Draft acknowledgements carry their immutable committed revision; request keys and editor
  baselines advance immediately, while dirty editors remain pinned across later refreshes.
  Unknown editor and package-command outcomes retain the exact frozen command and
  original request key across reload; retry never substitutes later typing and stored
  commands are never replayed automatically. Confirmed 401/403/404 failures remain
  distinct; rejection of a retry leaves the earlier unknown command available for
  reconciliation. Existing authorization-before-replay and once-only results remain.
- A committed save whose refresh fails remains committed, exposes a read-only refresh
  retry and blocks package commands until visible baselines are current. A 2xx response
  is acknowledged only when it carries the complete enhanced media contract. A refresh
  that returns 401, 403 or the authorization-preserving 404 reports that the workspace is
  unavailable, links Home and keeps package commands blocked without offering a futile retry.
- Conflicts show labelled Base, Current and Mine values with readable teammate names.
  Current, mine and combined recovery are explicit for editable content; aggregate
  commands require review and renewal. Combined mode keeps the comparison visible with
  its choices disabled, names the editor's save control and makes Current plus its matching
  metadata the confirmed-Cancel target. Acknowledged saves remove resolved comparisons.
  Validation messages use field labels and retain non-secret comment, decision and reason values.
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
- Correction regressions cover dirty package-command retry, failed-refresh resave,
  same-scope teammate changes during refresh, replayed committed revisions, retained
  conflict comparisons, disabled combined choices, combined cancellation to Current,
  acknowledgement cleanup with dirty typing and failed refresh, manual-copy fallback,
  membership-loss refresh handling and package-command blocking, literal stored operation
  labels, inline package-comment validation and access loss during error rendering.
- Final automated run:

  ```text
  PATH=/tmp/lm-pg16-bin:$PATH LD_LIBRARY_PATH=/tmp/lm-pg16-bin .venv/bin/pytest -q
  164 passed, 2 warnings in 116.84s

  .venv/bin/ruff check .
  All checks passed!

  .venv/bin/mypy
  Success: no issues found in 20 source files

  UV_CACHE_DIR=/tmp/lm-uv-cache uv lock --check --offline
  Resolved 47 packages in 5ms
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


### Partial owner review — 2026-09-23

Owner-reported passes:

- Player sign-in, navigation to the workspace and sign-out.
- Action and intention edits save successfully. With both fields edited, saving
  either editor saves only that editor's value.
- Adjudicator sign-in, navigation to the game view and sign-out.
- Two players editing the intention correctly encounter a conflict on the stale save.
- Fields adjust properly at narrow screen widths.

Owner-reported issue: **“Save combined” did not do anything.** The implementation
entered manual combined editing without saving, but its label implied a save and
its focus selector targeted the form's first hidden input. This is a usability
failure; conflict detection alone does not establish recovery acceptance.

Correction: rename the choice to **Edit combined value**, retain instructions in
the comparison stating that nothing has been saved yet and naming the editor's
save button, and focus the first editable field. The player manually combines
Mine with Current and then chooses **Save intention** or **Save action**.

Correction verification: three focused Chromium regressions passed, covering
intention/action focus, visible instructions, no premature save, persistence of the
combined intention in another player's view, and Cancel restoring Current for both
editor types. Ruff and `git diff --check` passed. The browser run reported the two
existing dependency deprecation warnings.

The owner considers the combined-edit correction sufficient for now (2026-09-23);
this is not a reported manual retest of that correction.

### Completed owner walkthrough — 2026-09-23

The owner reported all seven remaining walkthrough checks as passing:

1. Same-action conflict recovery.
2. Unsaved-text protection during Cancel, navigation and reload.
3. Submission blocked by unsaved editors, with the warning-label comment below.
4. Unknown-outcome wording and original-command retry.
5. Keyboard operation, feedback, zoom and long-text review (reported as an overall
   pass for this walkthrough item; no separate assistive-technology details supplied).
6. Harbor and Orchid fixture browsing/search alongside an active operational game.
7. Adjudicator discovery and completion of pending amendment review.

The comment on check 3 was that the warning named an action by its UUID rather
than a readable name. Corrected the shared editor label to use the visible action
heading (number and title); intention, new-action and package-comment editors use
plain names, and action comments/decisions use their enclosing heading. The same
readable label is used by the Cancel confirmation. No internal editor ID is shown.

These owner outcomes complete the 1U-1 review. The warning-label correction is
covered by automated verification, not a separately reported owner retest.

Warning-label verification: the focused Chromium regression for independent dirty
editors and submission blocking passed, including exact readable-label assertions
for both the blocking warning and Cancel confirmation. Ruff and `git diff --check`
passed; the browser run retained the two existing dependency deprecation warnings.
