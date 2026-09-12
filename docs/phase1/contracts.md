# Phase 1 architectural contracts

Accepted implementation direction, updated 2026-09-11 under
[B-11–B-14](../decisions.md#b-11--wrapper-ownership-and-framework-contracts).
The existing 1C backend contracts remain documented below; the new boundary governs
1D-remainder onward. 1D-1 implements drafting, submission and amendment decisions; 1D-2 coordination,
RFI and import workflows remain outstanding alongside white-cell, framework and replay work.

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
| Lookup | Automatically resolve authorized game-memory needs; flag world-specific questions for human verification. A reference corpus is out of scope but can register later. |

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

## 1D-1 implementation boundary

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
