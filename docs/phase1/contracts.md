# Phase 1 architectural contracts

Accepted implementation direction, updated 2026-09-21 under B-17 and
[B-11–B-16](../decisions.md#b-11--wrapper-ownership-and-framework-contracts).
The existing 1C backend contracts remain documented below; the new boundary governs
1D-remainder onward. 1D-1 implements drafting, submission and amendment decisions; 1D-2 coordination,
RFI and import workflows remain outstanding alongside white-cell, framework and replay work.

## Immediate delivery and research checkpoint: B-17

Before advancing to 1D-2, implement the revised design in existing templates and
resolve the [usability review](usability-review-2026-09-15.md) findings through the
[roadmap's immediate gate](../../roadmap.md#immediate-next-work--usability-remediation-and-template-implementation).
This does not silently change late-submission or amendment policy; unresolved
lifecycle decisions must be settled explicitly. Historical verification is not
acceptance of the unimplemented design.

The remaining phase order stands. Phase 2 adds an early complete agent-played
DATE World game before its full method/backend comparison. Scenario specifics are
deferred until nearer the test. Controllers use supported operations under the
same authorization and version rules; browser versus tool access remains open.
Reference baseline, exercise additions and generated history remain distinguishable.
The small game supplements curated cases and 2M volume tests; it supplies no human
usability evidence. No mandatory structured player fields or interpretation
confirmation gate are added. See [B-17](../decisions.md#b-17--usability-delivery-and-agent-played-research-games--2026-09-21).

## Wrapper and framework boundary: B-11

The wrapper owns authoritative input, rulings, facts, effects, world state, actor
beliefs, disclosures and all human review history. It preserves immutable run
artifacts: original proposals/grouping, raw output, context, validation failures
and exactly what reviewers saw. Only projections, indexes and caches are disposable.
Human triage/regrouping and original framework proposals are never disposable.

Frameworks receive frozen input and return proposals; they never write wrapper
tables directly, and the wrapper does not depend on a candidate's schema.

| Contract | Required boundary |
| --- | --- |
| Input | Immutable submissions, premise, prior rulings/facts, RFI status, disclosures and temporal cutoff. Preserve player prose verbatim. |
| Output | Review packet, proposed god view and per-actor fog-of-war views. Independent provenance class (game record/world knowledge/assumption) and truth status (established/claimed/disputed/unresolved). |
| Lookup | Automatically resolve authorized game-memory needs; flag world-specific questions for human verification. Limited approved game/scenario references are permitted with provenance, authorization and cutoff controls; full RAG is outside this application, with an external resolver seam. |

This **supersedes the former admin-to-memory projection prerequisite for 1D writes**.
1D and 1E use wrapper-owned records. Existing activation/dataset and query/reader
coupling is adapted in 1W, after 1E and before Phase 2. Activation must succeed
without a framework; datasets are created through framework registration. Queries
use the retrieval seam. Backup/restore preserves wrapper history and artifacts
without candidate backends; projections rebuild atomically with pending status.

The temporal, authorization and once-only effect guarantees below remain binding.
Their current PostgreSQL representation describes the 1C candidate, not a required
schema for every framework. Phase 2 proves the seam with two methods/two backends.

## Authorized retrieval: 1B and 1C-core

1B loads the **full source timeline and disclosure metadata into PostgreSQL**.
All nine audience/cutoff snapshots are test oracles, never runtime audience stores.
The temporary fixture loader is separate from player move import.
A development-only principal provider maps fixed identity IDs to game/audience
grants. Choosing an audience cannot enlarge grants. This is authorization
demonstration, not authentication.

The existing 1C service boundary is:

`read_memory(principal, game_id, audience, branch_lineage, known_at, effective_at, query) → MemoryView`

Validate audience access and server-resolved lineage. Phase 1 has only a non-null
root branch. Future lineage entries carry ancestor cutoffs; the argument itself
does not implement branching. Templates receive typed summaries, action content,
status, effective intervals, permitted visibility labels, and authorized evidence
links. No fixture dictionaries or ORM instances cross the presentation boundary.
1C-core may replace temporary persistence without changing 1B presentation tests.

Every fact revision, including relationships, has stable record identity,
immutable revision identity, game ID, **non-null branch ID**, simulated
`valid_from`/`valid_to`, UTC `recorded_at`, and nullable
`supersedes_revision_id`. Simulated intervals are half-open and game-relative
elapsed durations. Turn numbers map through configured boundaries. Unknown end
times stay open; the next record does not imply expiry. Accounts and operational
metadata need no simulated-time fields.

Disclosure records have both availability and recording times. A late disclosure
cannot reveal a fact at an earlier knowledge cutoff. `known_at` controls
recording and disclosure eligibility; `effective_at` controls applicability.
Known future commitments and scheduled effects remain retrievable, labeled pending.
Resolve supersession among revisions eligible at the knowledge cutoff, preserving
earlier revisions for history. Corrections append immutable revisions. Current
projections may update transactionally.

Authorization covers direct access, source and embedded references, evidence
navigation, search, counts, and relationship traversal. 1B reproduces all nine
oracles and tests forbidden selection, hidden evidence, and late disclosure.
1C-core adds correction, effective validity, relationship traversal, cross-team,
cross-game, branch isolation, and historical reconstruction tests without changing
the presentation contract.

The 1C query supports stable record and revision selection, language-neutral
PostgreSQL lexical search, record types, one-hop relationship filters, and a
bounded page size. Search intentionally uses the `simple` configuration and has
no stemming (`sanctions` does not match `sanction`). Opaque HMAC-signed keyset
cursors bind the game, root lineage, visibility scope, both temporal cutoffs,
filter hash, page position, and a composite record/relationship ingestion
watermark. Every page rechecks the
principal grant; malformed or context-mismatched cursors are bad requests.

Direct nonexistent and inaccessible targets use the same authorized query and
return the same 404 body. Constant-time behavior is not claimed. Root-branch
isolation and a single authorized relationship hop are supported. Ancestor replay
and multi-hop dependency chains remain deferred; MEM-03 is therefore only
partially satisfied in this milestone.

## Durable identity: 1C-admin

Use stable internal user IDs for authorship and audits. Deactivate accounts rather
than removing historical identities. Store local credentials and external bindings
separately. Bindings carry directory/provider scope, immutable external subject,
and internal user ID. Never merge by display name or username. Per-game directory
configuration is distinct from game membership. LDAP connectivity is deferred;
the mapping seam is included in 1C-admin. Verify materially different scenario
configuration and backup/restore access-rule continuity.

## Concurrent writes and authority: 1D and 1E

Mutable aggregates carry a version token. Writes include the version read.
A mismatch returns HTTP 409, preserves submitted values, and provides an
**authorized base/current/submitted comparison**; never silently overwrite.

Effect application requires an idempotency key scoped to game, branch, and operation.
Persist request fingerprint and original result atomically with effects and state.
Same key/request returns the original result; changed content with the same key
returns 409. An effect identity constraint prevents reapplication under a new key.
Lock affected state consistently. Authorization, expected versions, ruling
authority, ledger entry, and state/effect changes all commit or roll back together.

Submissions, discussion, commitments, and RFI answers never independently authorize
world-state changes. 1D includes shared drafts/comments/ownership, immutable
submissions, explicit amendments, coordination consent, RFIs, and move import
preserving content and omissions. Consent to coordination does not expose private
submissions. 1E adds manual issues, evidence, relationship decisions, splitting and
merging, RFI answers, rulings, effects, and separately released feedback.

Test concurrent conflicts, repeated and simultaneous effects, stale amendments
and reviews, prospective late answers preserving historical rulings, and release
audience boundaries.

## Operational detail contracts: 1D-2, 1E and Phase 2

- **Ingest:** retain the four free-text fields; Intended effect means Intent of Action.
  Preserve optional supplied context, source attachments/metadata and exact submitted
  versions. Imports retain omissions. Preparation reads authorized immutable packages
  without re-entry; derived tags/trigger interpretations never overwrite player prose.
- **Trigger and feasibility review:** link proposed statuses (satisfied, not satisfied,
  uncertain, not applicable) to statements, dependency/source versions, temporal and
  visibility constraints, rationale and operational human decisions. Preserve distinct
  intent interpretation, feasibility, applicability, effect and release records.
  Amendments, RFI answers and state changes invalidate affected current evaluations;
  preserve prior ones, require reassessment and apply approved effects once only.
  An unresolved or merely submitted conditional action does not become active.
- **State:** variable definitions and value revisions are wrapper-owned. Capture type,
  units where applicable, baseline, source, authority, visibility, effective/recording
  times, uncertainty/dispute and update rationale. Link rulings/effects; use atomic
  version checks. Canonical values and actor beliefs/disclosures remain distinct.
- **Packets:** retain supplied source versions, retrieval query basis, provenance and
  independent truth status, authorization/cutoff, unsupported assumptions, unresolved
  needs, raw output and validation failures, plus exactly what reviewers saw.
- **Observations:** preserve source/collection method, actor/team/action/turn/time,
  assessment and review history. Imported/automated capture is unverified until reviewed;
  source evidence and approved player-facing release are separate records/decisions.
- **Operational validation:** retain cases/results and approval for a specified game
  context and method/model/prompt/retrieval configuration before operational AI-method activation.
  Record known limitations, acceptance criteria and human fallback; define material
  change criteria and invalidate approval when they apply. Test approval/configuration
  mismatch. Research mode follows B-13 and does not inherit operational release authority.
- **Measurement:** retain workflow/review events and method identity; distinguish
  active time, queue/processing time and elapsed time. Link proposal/duplicate/trigger
  outcomes to original artifacts. Report external bypass/re-entry explicitly; absence
  of events is not evidence of absence. The existing evaluation plan governs analysis.

1D-2 owns ingest and baseline workflow events; 1E owns manual decisions, state,
observations and review events; Phase 2 adds machine proposals and validation approval.
These are future contracts, not extensions of the completed 1D-1 verification claim.

## White-cell lens and release: 1E

White-cell users retain god view while playing unrepresented actors. An optional
actor-only lens filters presentation in the current game/replay context. Indicate
the active lens and allow return to god view; no separate time selector, truth/belief
toggle or side-by-side views are required. Actor belief/disclosure history must
support accurate lenses and fog-of-war views. No actor grants or migration of team
grants is required for the lens. Historical retrieval still obeys temporal cutoffs.

Separate private internal evidence, audience-visible citations and explicit approved
disclosures. Check visible citations under audience authorization, but do not infer
prose safety from valid citations. An approved observation may be released without
its confidential causal evidence. Human approval governs operational release.
Test lens fidelity and prose leakage with clean citations, rather than restricting
white-cell users' access to other actors' information.

## Replay and research: Phase 2

Each replay creates its own wrapper-owned authoritative history and immutable run
artifacts, leaving the original unchanged. Framework projections belong to one
trajectory; no later knowledge or unrelated replay data may contaminate retrieval.
Research replay defaults to automated mode with a human-review toggle; record the
policy and changes. Recorded-ruling reuse is an explicit alternative where applicable.
This research default does not authorize operational state or feedback release.

Retain incompatible recorded moves as attempted by default, adjudicating feasibility
in that trajectory; record flag/skip overrides. Record applicability of original
RFIs, rulings and disclosures. Phase 4 adds human revision/controller regeneration.
Report frozen-context and trajectory comparisons separately and preserve reviewer
effort and what was shown. Automated acceptance is not human-effort evidence.

## Integration and deployment obligations

After Phase 2M, 1F runs a small multi-turn browser game, concurrent operations and a restoration
drill without database edits, verifies prior commitments and nondisclosure, and
maps applicable C01–C12 requirements to application evidence. It exercises the
framework seam and model adapter introduced in Phase 2.

Title its performance artifact **“Local eight-user sanity check.”** Record host
specifications, workload, concurrency, durations, errors, pool waits, and observed
percentiles. Assess the provisional p95 two-second target only within that run.
State explicitly: **no 150-user capacity evidence**. OPS-04 requires a later
representative deployment with deadline-burst workload.

1G adds one-command development/evaluation setup on Ubuntu and native Windows
PowerShell with optional WSL, documented prerequisites and generated secrets.
Dependencies must be pinned and packageable offline. This is not full installer
parity or offline provisioning evidence. Phase 3A delivers offline research
install/update/recovery and internal reporting; results cannot be exported.
Future external export is required under OPS-10/B-16, but scope, contents, mechanism,
authorization and delivery phase remain unresolved; no current egress is authorized.
Organizational identity, TLS, VDI and full-scale capacity remain Phase 5 qualification.
Phase 2 inference uses separate processes/budgets, with queued status, priority,
retry, cancellation and failure recovery, never waiting in interactive transactions.

## Phase 1C correction authority and compatibility

The [bounded correction record](corrections-1c.md) governs current administration.
Only system administrators may grant/revoke adjudicators; existing grants remain
subject to operator review. Request-time principals use the governing configuration
at the injected current time and `max(1, current_turn)`, independently of historical
memory cutoffs. Game administrators can manage scoped ordinary membership/roles,
but cannot place unrelated accounts or expand themselves into adjudication.

Current code rejects roster/controller topology changes; controlled additions and
control changes remain planned work. B-11 supersedes this section's former mandatory
admin-to-memory projection prerequisite. Recovery remains blocked until restoration,
session revocation and verification complete. Populated 0004 databases and their
archives are intentionally incompatible with 0005. See the [developer guide](../development.md)
for current compatibility limitations; do not treat the historical correction's
0004 rollout procedure as the current checkout's upgrade path.

## 1U-1 protected browser operation contract

Workspace editors keep authoritative saved values, current authored values, immutable
baseline revision and a frozen pending command as separate state. A successful command
is acknowledged before the browser requests fresh saved regions. Clean regions advance
to the returned revision; dirty editor DOM and its older baseline remain in place until
save, discard or explicit conflict recovery.

Enhanced browser forms opt in with the workspace media type and header. A committed
response uses that media type and must match the dispatched operation and key. Responses
distinguish committed, validation, edit conflict, request-key conflict and confirmed
rejection outcomes, and supplies the operation, original key, stable editor identity and
refresh destination. A draft-operation acknowledgement also supplies the immutable
committed draft revision identified by its package-revision result, including on replay;
the browser rotates the request key and advances the saved editor to that revision before
refresh. A retained dirty editor never adopts a later refresh revision as its save baseline.
Network failures, 5xx responses and unreadable acknowledgements are uncertain. Retrying an
uncertain operation sends the exact frozen command and original
key to the frozen endpoint with the current anti-forgery token; stored commands never
run automatically. Rejection of a retry rejects only that request and does not erase
the original unknown operation.

Conflict recovery presents labelled Base, Current and Mine values. Editable text offers
Use current, Save mine and Edit combined value; aggregate commands require current-state review
and a newly selected operation from the refreshed state. Entering combined mode retains
the comparison but disables its choices; the editor's own save control commits the combined
value. Current and its matching revision, request key and anti-forgery token become the
discard target, so confirmed Cancel loads Current without creating another stale save.
An acknowledged save removes its resolved comparison before refresh. If an editor disappears
or becomes read-only, its authored text remains available for copy or explicit discard.
When a dirty editor survives a scoped refresh, its latest authoritative snapshot is
retained separately and becomes the discard target without changing its save baseline.
Internal identifiers are not presentation labels. Recovery
storage is scoped by signed-in user and workspace; unavailable browser storage degrades
to in-page retention with a visible warning.

### 1U-2 PR 1 amendment review and local navigation

Adjudicator comparisons read the selected amendment's immutable base and proposed
submission versions within the authorized game/team/turn. Current drafts and later
effective versions never substitute for these sources. Missing source versions
produce an unavailable comparison and no decision control. Decision commands,
authorization and original-key reconciliation retain the 1U-1 contract.

`/adjudicate` accepts an optional scoped `amendment_id`; absent selection chooses
the pending amendment, otherwise the latest amendment. `/play` accepts an optional
scoped submitted `revision`, opening its disclosure. Unknown or foreign selections
return not found. Decision errors and refresh destinations retain the attempted
amendment; these presentation URLs do not modify persisted command results.

The player rejection notice follows the newest completed amendment decision. Show
it when the newest amendment is rejected, and retain that rejection's reason/link
while a later correction is pending. A later acceptance clears the notice; starting
another pending revision after that acceptance must not resurrect an older rejection.
A new rejection replaces the earlier notice. Historical decisions/reasons remain
accessible regardless of whether the notice is shown.

The 1U-1 dirty-navigation contract now permits same-document fragment links to an
existing element when origin, path and query match. This only moves within the
page: editor DOM, authored text, baselines and recovery storage are retained.
Other destinations and missing/malformed fragment targets retain the existing
warning; reload and Cancel protection are unchanged. The consuming PR must rerun
and record the affected 1U-1 browser checks in the 1U-2 verification record.

## 1D-1 implementation boundary

The amendment-only lifecycle below records the delivered 1D-1 implementation.
[B-18](../decisions.md#b-18--usability-alignment-policies-1u) supersedes it as
current policy: revisions strictly before the stored deadline become effective
immediately, while revisions at or after it require adjudicator acceptance. That
policy, confirmation contract and effective-version event history are delivered
together in 1U-2; 1U-1 does not partially change submission behavior.

The completed increment is draft → submit → explicit amendment → decision, with
one pending amendment per submission and a separate effective content version.
Submission status is `submitted` or `amendment_pending`; acceptance/rejection
belongs to amendment decisions. No ruling/closure flag exists yet. 1E must add
ruling lifecycle restrictions together with its adjudication model.

Stable action identity is scoped by game/team/turn. Submitted action rows are
immutable per content version; 1D-2 will extend coordination/RFI links to draft-time
revision references. The retained import, coordination and RFI tables have no
application writers in 1D-1. Request-key branch IDs always come from the game's root
branch. A historical view never changes current authorization.

One submitter designation per team is database-enforced. Inactive designation
replacement is explicit, authorized, atomic and audited. Native text must be
complete on submission; ownership does not restrict teammate editing; late
submission is allowed with the governing deadline snapshotted.

The disposable 0005 baseline is revised in place for application version 0.3.0.
Exact backup-version verification rejects old 0005/0.2.0 archives before restore.
See [1D-1 verification](verification-1d-1.md) for evidence and limitations.

### Effective-version provenance (1U-2 delivery PR 2)

Schema 0006 records one append-only event for each effective content version.
Initial events retain version 1's submitter and creation time. Adjudicator acceptance
retains the decision ID, adjudicator and decision time. Rejection and pending proposals
create no event. Event ordering follows content-version numbers, including gaps for
rejected revisions; tied timestamps do not determine order. Recording is transactional
with the existing command; a matching replay creates no event. `immediate_revision`
is reserved, with no writer or policy change in this increment.

UPDATE and DELETE are rejected. RESTRICT foreign keys retain the referenced content,
decision and responsible user: **provenance makes these rows permanent**. Submission
and game deletion (including the game's workspace cascade) therefore fails when it
would erase this history. Referenced users must be deactivated, not deleted. An audit
of application code, CLI, seed and development scripts found no game, submission or
user deletion path; current deletions revoke roles/memberships. Disposable test cleanup
uses TRUNCATE; there is deliberately no TRUNCATE guard or special reset exception.

Migration 0006 validates named invariants before writing history and aborts atomically
with bounded identifier-only diagnostics if provenance cannot be established. It does
not infer actors or timestamps, repair history, or skip rows. A populated downgrade is
refused; rollback requires restoring the pre-upgrade backup with its matching application.


### Post-lock commands and completed retries (1U-2 PR 3a)

PR 3a makes **no submission-policy change**: late first submissions remain allowed,
all revisions still require adjudicator decisions, and only the active current turn
accepts new writes. It intentionally changes three observable results:

- Completed `submit`, `amend` and `decide` retries after turn advancement, game
  completion or later edits return the original stored result instead of a fresh
  current-turn/version/status error. Authorization is checked first. Changed payloads
  using the same key still conflict. Other editor operations retain their prior rules.
- Command timestamps come from authoritative server time read after all mutation
  locks, not from before a lock wait. Each transaction retry reads a fresh time.
- Authority revoked during a lock wait causes denial, even if the session previously
  loaded the user or membership. Locks retain game → sorted users ordering, followed
  by draft, submission and the scoped amendment; authorization is rechecked afterward.

A replaced submitter cannot retry even their own completed submission. If its response
was lost, they cannot recover that result through their retry. The existing unknown-
outcome recovery retains the exact original command and its key as unresolved after
such a denial; it neither declares the original command failed nor starts a new write.
An authorized enhanced replay instead returns `committed` and refreshes the original
turn, clearing pending state even if that turn is now read-only. Existing request-key
fingerprints, result formats, schema and backup compatibility remain unchanged.
