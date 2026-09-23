# 1U — Phase 1 usability alignment

Created 2026-09-21. Delivery status is recorded per milestone below.
This document is the entry point for remediation sessions.

## Purpose and authoritative references

Bring the delivered Phase 1 workflow through 1D-1 into alignment with the design
baseline before starting 1D-2. Deliver bounded increments that the owner can
review and validate individually. Milestones are sequential but share contracts;
later work must preserve earlier guarantees.

- [Roadmap](../../roadmap.md#immediate-next-work--usability-remediation-and-template-implementation): phase order and the gate before 1D-2.
- [B-18](../decisions.md#b-18--usability-alignment-policies-1u): authoritative usability policies. Do not reopen these as undecided questions or infer different behavior from mockups or historical tests.
- [Usability review](usability-review-2026-09-15.md): historical observations, finding IDs and acceptance checks.
- [Design guide](../design-guide.md), [examples](../design-examples.md), [visual reference](../design-reference.html) and [navigation inventory](../navigation-inventory.md): structural and interaction baseline, preserving proposed/accepted distinctions.
- [1D-1 verification](verification-1d-1.md): earlier implementation evidence, not acceptance of 1U behavior.

The milestone descriptions below summarize delivery obligations; B-18 remains the
single policy source. The original review remains historical evidence. Its open
policy questions are resolved where B-18 supplies a decision.

Excluded: coordination, RFIs, move imports, 1E ruling/release workflows,
simultaneous editing, autosave, LDAP, pending-revision withdrawal and the Execution
Context alternative. Bulk local-account import is included and is distinct from
move import. No full-game, capacity or deployment qualification is claimed.

## Delivery and session protocol

Sequence: foundation preparation → 1U-1 → 1U-2 → 1U-3 → 1U-4 → 1U-5 → 1U-6.
Detailed implementation planning happens one milestone at a time, after inspecting
the current code and previous evidence. Do not execute the entire sequence from
this document without the intermediate reviews.

| Milestone | Outcome | Status | Verification |
| --- | --- | --- | --- |
| 1U-1 | Protected input, shared navigation and fixture recovery | Accepted | [Verification](verification-1u-1.md) |
| 1U-2 | Coherent submission/revision and dedicated amendment review | Implementing (PR 1 only) | [Verification](verification-1u-2.md) |
| 1U-3 | Practical action volume and safe automatic saved updates | Proposed | Not yet produced |
| 1U-4 | Account management and participant placement | Proposed | Not yet produced |
| 1U-5 | Guided configuration and activation | Proposed | Not yet produced |
| 1U-6 | Integrated usability acceptance and deferred checks | Proposed | Not yet produced |

Status progression: **proposed → ready → implementing → awaiting review → accepted**.
Ready means the bounded implementation plan and prerequisites are established.
Passing tests and completed code lead to awaiting review; owner acceptance is
required before advancing to the next milestone. Corrections remain in the current
milestone unless a scope change is explicitly agreed.

At the start of each session, read this document, the relevant authoritative
references and the preceding milestone's verification, then inspect current code
and working-tree changes. Identify missing dependencies before expanding scope.

At the end, update this status table and create or update
`docs/phase1/verification-1u-N.md` for the milestone worked on. Record changes,
finding IDs, checks and outcomes, evidence, limitations, unresolved issues and the
next concrete task. Distinguish automated results from human acceptance. Link the
implementation commit or PR when available. Update navigation placement and
implementation evidence in the inventory; record policy changes in the decision
log, not only in a task conversation. Include these documentation changes with
the implementation change.

### Foundation preparation and shared dependencies

Complete this bounded preparation as part of planning 1U-1; it is not a new
product milestone or another speculative design session:

- Establish independent editor/save boundaries, retained dirty state and the result states consumed by all templates. Design for 1U-3's clean-region refresh from the outset.
- Establish confirmation and operation-reconciliation contracts compatible with B-18. Distinguish confirmed failure, conflict, confirmation required and unknown outcome. Check existing request-key support per operation rather than assuming it covers all writes.
- Outline 1U-2's effective-version event and preserving migration/backfill requirements. Do not use an old disposable-database reset as authorization to erase history.
- Record which later milestone consumes each shared contract. Changes to an established contract must identify affected earlier acceptance checks and rerun them.

Before 1U-4 implementation, settle bulk transaction semantics, selection scope and
credential-safe recovery. Establish the draft-only team-creation service contract
there; 1U-5 reuses it for setup. Before 1U-3 implementation, select the saved-update
transport and reconnect behavior. These are bounded implementation choices, not
unresolved B-18 policies. New dependencies must satisfy offline packaging rules.

## Milestones

### 1U-1 — Protect input and restore navigation

**Deliver:** Shared signed-in shell with identity/account/sign-out, authorized
game entry, clear game/team/turn context, flat destinations and recoverable error
pages. Establish shared semantic visual tokens, controls and accessible feedback.
Protect independent editors through saves, navigation and errors. Fix fixture
enumeration after operational game activation.

**Acceptance:**

- Players and adjudicators reach their authorized existing tasks without supplied URLs and can sign out. Unauthorized destinations remain absent; denied pages provide safe navigation.
- Saving intention preserves a dirty action without saving it implicitly. Other saves and partial page updates cannot discard unrelated authored text.
- JavaScript navigation/reload paths retain recoverable input or warn before loss. Ordinary-form paths preserve save boundaries and recoverable validation input. Record B-18's no-JS reload limitation explicitly; do not count it as a pass.
- Feedback names the affected scope, retains useful focus/location and distinguishes failure from an unknown outcome. Reconcile an uncertain operation using its original identity before a fresh command.
- Activate a game alongside Harbor/Orchid fixtures, then browse/search both fixtures successfully without altering operational history or weakening access boundaries.

**Finding ownership:** UX-01/02/26/27/37/47/48, BUG-01. Shared controls and feedback
start here; each consuming milestone verifies their application to its writes.

**Dependency risk:** Whole-page replacement or generic fresh-key retries would
undermine 1U-2/3. Establish scoped recovery here; leave new revision policy delivery
to the complete 1U-2 increment.

### 1U-2 — Make submit, review and revise coherent

**Prerequisite:** 1U-1 accepted; confirmation/reconciliation foundation established.

**Deliver:** Visible draft/effective/pending/rejected states, deliberate revision
entry, package confirmation and Submit revision wording. Implement B-18's immediate
versus approval-required paths and visible late first submissions. Deliver a
dedicated adjudicator page for existing amendment decisions with changed-action
summaries, complete labeled comparisons and persistent player-facing reasons.
Add append-only effective-version mechanism records and preserving backfill.

**Acceptance:**

- Ordinary members can draft but cannot submit. Only the active current turn is writable. Late first submissions remain allowed and visibly late.
- Revisions strictly before the stored deadline become effective without an adjudicator decision; revisions at or after it require acceptance. Existing pending amendments still require decisions. A pending revision blocks another submission while draft editing remains available.
- Read server time after mutation locks. Exercise requests waiting across the deadline, stale effective versions and changed confirmation expectations. Confirmation required writes nothing and does not claim the request key.
- An authorized retry of a completed matching command returns its original result before deadline re-evaluation. Lost responses cannot duplicate submissions or change their meaning. Renewed confirmation uses a new key only after resolving any uncertain original operation.
- Every effective-version change records mechanism, responsible user and time. Backfill is traceable to immutable data, preserves versions/decisions/pending amendments and invents no historical events.
- Players and adjudicators complete submission, rejection, correction and acceptance with visible state and next steps. Compare changed/added/removed actions, cleared fields, long replacements and unchanged context without requiring sequential rereading of the whole package.

**Finding ownership:** UX-38/43–46/49–51. UX-46 is resolved through B-18's current-turn
and deadline semantics, not by adding a turn lock or banning late first submissions.

**Dependency risk:** Ship service policy, history, confirmation/retry behavior and
their presentation together. A UI-only milestone cannot satisfy this gate.

#### Agreed 1U-2 PR delivery sequence — 2026-09-23

One milestone, one accumulating [verification record](verification-1u-2.md) and
one owner acceptance gate. PR numbers below are delivery labels, not GitHub numbers.
Every PR gets a code review pass, fixes on that PR, and owner verification/approval
before merge. Do not automatically merge implementation PRs.

| Increment | Target | Deliverable and explicit boundary |
| --- | --- | --- |
| Macro prerequisite | `master` | Pure move of shared template macros; existing tests green. [GitHub #2](https://github.com/kayeleven/ai_wargame/pull/2) merged by owner. No behavior changes. |
| PR 1: dedicated amendment review | `master` | Immutable base/proposed comparisons, changed-action navigation, complete field comparisons and existing decision recovery. Player changes only a revision link and visible rejection reason. No policy, schema, confirmation or full player-state changes. |
| PR 2: effective-version history | `master` | New migration after 0005; append-only mechanism/user/time records; preserving backfill from first submissions and accepted decisions; transactional events for existing initial/acceptance paths. Backup compatibility and upgrade/restore docs. No policy, confirmation or UI changes. |
| PR 3: B-18 service policy | `milestone/1u-2` | Post-lock authoritative time/authorization, authorized replay before re-evaluation, expected effective version/deadline/consequence, no-write/no-key-claim `confirmation_required`, immediate versus approval-required revisions, immediate-revision events and pending-submission blocking. No player lifecycle UI. |
| PR 4: player lifecycle | `milestone/1u-2` | Deliberate revision entry preserving saved draft changes; states, package review/confirmation, Submit revision wording, ordinary/enhanced forms, frozen uncertain commands, renewed confirmation and replay-accurate feedback. No extra policy, migration or automatic teammate refresh. |
| Milestone PR | `milestone/1u-2` → `master` | Integrated regression/walkthrough evidence and final verification record; owner acceptance before merge and before 1U-3. |

Create `milestone/1u-2` from master after PRs 1–2 merge. While PRs 3–4 are open,
merge master changes into it promptly; review and test conflict resolutions on the
open PRs so the milestone PR contains no unreviewed resolution. Preparatory PRs 1–2
can merge independently of the milestone gate. The new policy reaches master only
with history, confirmation/recovery and presentation together through the milestone PR.

**Size:** aim for about 400–800 non-test changed lines per implementation PR,
counting additions plus deletions, including documentation. Project size before
starting and monitor actual changes. If a PR will exceed about 800 lines, stop and
propose a further split before continuing. Do not compress code to meet the limit.
The smaller pure-move prerequisite is exempt from the lower guideline.

**Pre-agreed PR 3 fallback:** if PR 3 exceeds the guideline, flag it and extract
PR 3a to master: read authoritative time after locks, recheck authorization after
locks and recognize completed matching retries before re-evaluation on existing
submit/amend/decide paths. Keep it behavior-preserving hardening. PR 3 retains B-18
policy, extended command expectations and `confirmation_required`; do not re-plan
the sequence from scratch. Bring the merged hardening into the milestone branch.

**PR 1 sizing decisions:** extract macros first (done); defer word-level highlighting.
Changed-field markers with complete original/proposed values satisfy this increment.
Do not introduce `TextSegment` until needed. Size the comparison model only for
amendment review; generalize for draft/effective comparisons in PR 4 if needed.
Comparison content is server-rendered and template-escaped; no new authored-content
`innerHTML` path. Reverify 1U-1 navigation protection when adding fragment navigation.

**Required evidence by increment:**

- PR 1: pure comparison tests; immutable/scoped HTTP reads; ordinary/enhanced decisions,
  validation/conflicts/retries; literal HTML-like title/field/reason content; keyboard,
  narrow layout and retained dirty-navigation checks. Create the verification file on master.
- PR 2: populated migration histories with accepted, rejected and pending amendments;
  traceable events, abort-with-diagnostics on unsupported history, no invented events,
  append-only enforcement, transaction/retry integrity and backup/restore round trip.
  Before merge, also run the upgrade against a restored copy of the current development
  database and record results. Never migrate the original as the dry run.
- PR 3: service and HTTP coverage before/at/after deadline, including a real lock wait
  across it; changed authority/expectations, stale versions, pending draft editing,
  zero writes/key claims on renewed confirmation and replay before deadline evaluation.
- PR 4: browser lifecycle/recovery coverage in enhanced and ordinary forms plus keyboard,
  feedback and narrow-screen walkthrough. Preserve 1U-1 guarantees.
- Milestone PR: full relevant regressions, lint/type checks and unaided cross-role
  submission/rejection/correction/acceptance walkthrough including both deadline paths.
  Append evidence in each PR; finalize the same record at the gate. Separate automated
  results from human acceptance and retain the no-JavaScript reload limitation.

### 1U-3 — Support realistic action volume and collaboration

**Prerequisite:** 1U-2 accepted; reuse editor and operation-state contracts.

**Deliver:** Compact searchable action navigation, readable view/edit modes,
independent summaries, scoped Save/Cancel, previous/next and context-preserving
return links. Keep overall intention independently editable and guidance
subordinate. Place existing comments with their composer after a bounded placement
trial. Move passive history out of normal player pages while preserving authorized
history access and meaningful event summaries. Automatically surface saved
teammate changes without autosave or simultaneous text editing.

**Acceptance:**

- With 90 actions and long text, find/read/edit a selected action, navigate between actions and restore search, display sort and list position on return.
- Incoming updates refresh clean regions, preserve dirty regions and offer current/mine/combined conflict recovery. Disconnect/reconnect and access changes leave visible, safe states.
- Display sorting changes no canonical order; only explicit reorder commands change it. Verify removal/reorder and original history retention.
- Comments are readable, attributable and writable beside their composer where authorized; read-only restrictions are explained. Do not assume the withdrawn chat sidebar is accepted.
- Repeat dirty-input, pending-revision and confirmation checks under automatic refresh; updates cannot silently invalidate what a user believes they are submitting.

**Finding ownership:** UX-28–31/33–36/39–42. UX-34 applies to the retained authorized
history surface; UX-40 removes its passive list from normal player work.

**Dependency risk:** Automatic updates must consume the established editing model,
not replace dirty DOM regions or reset list/confirmation state indiscriminately.

### 1U-4 — Consolidate accounts and participant placement

Effective-version provenance makes referenced users permanent: account management
must deactivate these users rather than delete them (see contracts.md).

**Prerequisite:** 1U-3 accepted; bulk transaction semantics and draft-team contract
defined in this milestone's implementation plan.

**Deliver:** Compact searchable/sortable/paginated account and game-participant
rosters; assigned/unassigned counts; inspectable bulk selection and named
team/authority placement. Provide bulk local-account preview/import, display-name
editing, password reset and previewed reactivation. Preserve placement context
through account creation. Provide controlled draft-only Add team, backed by a
service that keeps configuration and team state consistent. Use field-specific
recovery and readable historical attribution.

**Acceptance:**

- Place 50 users without an external checklist; hundreds of accounts do not bury primary commands. Full selected membership remains inspectable across filters/pages. Results identify changes and failures under the chosen transaction semantics.
- Duplicate/inactive usernames and stale selections have specific recovery. Passwords never enter retained values, errors, logs, history, operation records or evidence.
- Reactivation previews and restores only still-existing eligible grants; revoked sessions, removed grants and replaced submitter authority stay revoked. Password reset revokes existing sessions and retains the existing password policy.
- Preserve exactly one designated submitter per team, including explicit replacement and unavailable replacement states. Named controls make their subject clear.
- Recheck authorization for open workspace commands and retries after deactivation, replacement or grant removal. New teams can be added only in draft games, consistently with activation and roster rules.

**Finding ownership:** UX-03–08/10/11/17–23.

**Dependency risk:** Account changes affect active workspace sessions; run cross-role
regressions. Do not postpone the team service until 1U-5 and build a competing
placement-only representation meanwhile.

### 1U-5 — Guide game configuration and activation

**Prerequisite:** 1U-4 accepted; reuse its draft-team service and participant flow.

**Deliver:** Server-generated stable identifiers, named selectors, explained
field audiences/effects and required/optional labels. Guided controls cover the
supported configuration, including teams, actors, objectives and turns, with clear
prerequisites and activation results. Consolidate misleading duplicate navigation.

**Acceptance:**

- A facilitator creates/configures a game, places participants and activates it without typing internal IDs or composing JSON. An advanced JSON path may remain optional; JSON-only setup does not close this milestone.
- Editing round-trips every supported configuration field; unknown fields are explicitly rejected. Do not silently simplify away fields or introduce unimplemented scenario capabilities.
- Invalid configuration retains non-secret input and identifies fields/prerequisites. Adding teams and activating cannot leave inconsistent configuration/team state, including concurrent attempts.
- Started turns cannot be redefined. Active-game roster edits remain prohibited. Identifiers remain stable when display names change.
- Activation names the game/current turn and provides a clear next task.

**Finding ownership:** UX-12–14/25.

**Dependency risk:** Reuse the strict configuration model and roster service;
guided forms must not become a lossy alternative schema.

### 1U-6 — Demonstrate alignment and close the gate

**Prerequisite:** 1U-1 through 1U-5 accepted with verification records. Evidence is
collected throughout delivery; this is not the first integration-test milestone.

**Deliver and acceptance:**

- Repeat a fresh unaided player/admin/adjudicator walkthrough of the implemented workflow, including both immediate and approval-required revisions and rejection recovery.
- Exercise 90-action work and 50-user placement, keyboard/focus/announced feedback, 200% zoom, narrow layouts and long authored text in the actual application.
- Complete deferred memory navigation/search, historical retention, action removal/reorder and submitter-replacement checks. Automated authorization checks remain distinct from manual usability evidence.
- Run relevant browser/service/database regressions, lint and type checks. Earlier guarantees affected by later work must be retested when changed, not merely cited from obsolete evidence.
- Measure navigation against trial defaults: three steps from home, one drill-down level and seven destinations per role/context. Record justified exceptions; firm constraints still apply. Update navigation implementation status independently of design status.
- Reconcile every UX-01–51 finding and BUG-01 to behavior/evidence or an explicit disposition. Resolve blockers before 1D-2; owner-accepted deferrals name their reason and follow-up gate. Record the no-JS reload limitation separately.

**Finding ownership:** Cross-cutting feedback UX-09/15/16/24/32 is verified in the
milestones that deliver the respective writes and reconciled here. All remaining
findings are audited here; no earlier review or mockup constitutes acceptance.

**Exit:** Owner accepts the integrated evidence and remaining dispositions. Update
the roadmap to record 1U completion and allow 1D-2 planning. This gate establishes
bounded usability alignment, not full-game or capacity readiness.
