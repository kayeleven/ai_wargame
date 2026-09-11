# Phase 1 architectural contracts

Accepted implementation direction, 2026-09-10. Milestone 1A establishes the
application foundation. The following domain rules govern subsequent milestones;
they do not imply those workflows are already implemented.

## Authorized retrieval: 1B and 1C-core

1B loads the **full source timeline and disclosure metadata into PostgreSQL**.
All nine audience/cutoff snapshots are test oracles, never runtime audience stores.
The temporary fixture loader is separate from player move import.
A development-only principal provider maps fixed identity IDs to game/audience
grants. Choosing an audience cannot enlarge grants. This is authorization
demonstration, not authentication.

Establish the permanent service boundary:

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
filter hash, page position, and ingestion watermark. Every page rechecks the
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

## Integration and deployment obligations

1F runs a small multi-turn browser game, concurrent operations and a restoration
drill without database edits, verifies prior commitments and nondisclosure, and
maps applicable C01–C12 requirements to application evidence. Real model-adapter
behavior remains Phase 2.

Title its performance artifact **“Local eight-user sanity check.”** Record host
specifications, workload, concurrency, durations, errors, pool waits, and observed
percentiles. Assess the provisional p95 two-second target only within that run.
State explicitly: **no 150-user capacity evidence**. OPS-04 requires a later
representative deployment with deadline-burst workload.

Developer-machine execution is the Phase 1 target. Offline installation,
organizational identity connectivity, TLS, Windows VDI qualification, and full-scale
capacity remain tracked deployment work. Offline runtime asset choices in 1A do
not qualify offline provisioning. Phase 2 inference uses separate processes and
budgets and never waits inside interactive transactions or the interactive pool.
