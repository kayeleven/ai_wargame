# Decisions and open questions

Status: updated 2026-09-15; B-16 incorporates the operational addendum. B-11–B-14 record the accepted roadmap revision and owner-selected defaults. They govern remaining work, not claims of implementation. Historical decisions and evidence are retained; candidate backend, worker and model selections remain open.

## Established direction

| ID | Direction | Consequence |
| --- | --- | --- |
| D-01 | Research focuses on AI pre-adjudication usefulness to humans. | Human effort, omissions, and refinements are primary evaluation evidence. |
| D-02 | The product also supports actual wargame play. | Player collaboration, RFIs, adjudication, state updates, and feedback are core workflows. |
| D-03 | Games are configurable and support human, AI, and imported actions. | Separate scenario configuration, actor identity, and controller implementation. |
| D-04 | Living memory must serve adjudicator and fog-of-war views. | Preserve history, provenance, action status, relationships, and knowledge boundaries. |
| D-05 | Historical replay, modified action sets, and added AI actors are intended capabilities. | Preserve versioned inputs and branch history from the outset. |
| D-06 | The target includes air-gapped operation with local inference. | Required services and dependencies need offline operation/provisioning. |
| D-07 | Installation and initial configuration are first-class workflows. | Normal administration must not require in-depth Compose or environment-file editing. |
| D-08 | Scale ranges from single-digit evaluation users to 150 simultaneous users with multi-user teams. | Validate collaboration and application concurrency separately from inference capacity. |
| D-09 | Design should be system-agnostic; Ubuntu and Windows VDI are likely deployment components. | Keep platform assumptions explicit and interfaces portable. |

## Provisional design choices

| ID | Proposal | Validation or decision needed |
| --- | --- | --- |
| P-01 | Browser access from Windows VDI to an Ubuntu-hosted application. | Confirm VDI topology, supported browser, network, and authentication constraints. |
| P-02 | Modular application plus background workers and a model adapter. | Verify initial operational simplicity and scaling needs. |
| P-03 | Append-only history, snapshots/views, and preserved source artifacts. | Choose transaction boundaries and the extent of event sourcing. |
| P-04 | Evaluate a graph relationship layer against a simpler baseline. | Use retrieval and operational evidence before selecting a database. |
| P-05 | Simultaneous submissions and joint review as the initial turn policy. | Adopted for Phase 0 by B-02; broader lifecycle configuration remains future work. |
| P-06 | Shared drafts, comments, revision history, and conflict detection before character-level live editing. | Validate that this meets team collaboration needs in pilots. |
| P-07 | Human approval for operational rulings; explicit automated research mode. | Phase 0 authority and release baseline adopted by B-02; automated mode remains Phase 2 work. |

## Open decisions

| ID | Question | Needed by |
| --- | --- | --- |
| O-01 | Initial fixture/action baseline resolved by B-01–02; real-game refinements may supersede it. | Phase 0 baseline recorded |
| O-02 | Initial simultaneous review, amendment, late-RFI, and release policies resolved by B-02. | AI walkthrough accepted by B-05; validate in Phase 1 |
| O-03 | Team-shared access remains; B-12 adds actor knowledge and an actor-only white-cell lens without restricting god-view access. Individual user compartments remain deferred. | Resolved direction; validate in 1E |
| O-04 | What local authentication/identity service, certificates, and administrator access are available? | First deployment design |
| O-05 | Wrapper stack resolved by B-06; candidate memory backends (roadmap N-02), worker mechanism and offline packaging remain open under B-11/B-14. | Phase 2 / 3A |
| O-06 | What local model service, hardware, context limits, and structured-output capabilities are available? How are model artifacts provisioned offline? | Phase 2 |
| O-07 | Which external game formats should be imported first, and how will missing context be represented? | Initial import and later adapter expansion |
| O-08 | What reviewer protocol and practical success thresholds will determine whether preparation helps? | First comparison study |
| O-09 | B-13 resolves the Phase 2 default as retain as attempted (N-05); detailed human revision/controller regeneration remains Phase 4 work. | Phase 2 baseline resolved / Phase 4 extension |
| O-10 | What representative workload, latency targets, inference queue targets, backup frequency, and recovery objectives define full-game readiness? | Set before phase 5 testing |
| O-11 | Current operational results remain internal (B-14/B-16). What retention, audit-access and internal diagnostic-handling policies apply? | Before 3A |
| O-12 | Future external export is required (OPS-10/B-16); what scope, contents, mechanism, authorization and delivery phase apply? | Unresolved; before export design |

These questions do not block all progress. Resolve each before implementing behavior that depends on it; keep independent work moving.

## Phase 0 baseline decisions — 2026-09-09

### B-01 — Non-military scope and authentic submission content

Status: accepted baseline. Problem: the broad architecture could be read as requiring structured player inputs or military adjudication. Chosen approach: an overall free-text turn intention and any number of actions with Title, Description, Intent of Action, and Anticipated reaction; separate system metadata and source-linked interpretations. Content is versioned so the baseline can evolve. Military movement/combat and M&S integration are separate work.

Alternatives: mandatory structured resource/target fields; a unified military/non-military submission workflow. Evidence: project owner supplied the actual action format and explicitly limited this build to non-military actions. Consequence: preserve prose, treat anticipated reactions as expectations, and resolve missing context through review. Requirements: PLAY-01/05, GAME-04, MEM-01/05. Verification: C01, C08, C11 in the [acceptance cases](phase0/acceptance.md).

### B-02 — Small synthetic game and human authority

Scope note, 2026-09-11: B-12 extends the fixture's team-knowledge baseline with
actor beliefs and white-cell lenses. B-13 sets research replay defaults. The
original fixture, operational human authority and historical acceptance remain intact.

Status: accepted initial implementation baseline. Problem: behavior must be concrete before implementation. Chosen approach: two civilian teams and four turns, simultaneous submissions, team-shared knowledge, a designated submitter, explicit consent to named cross-team coordination, and one adjudicator approving rulings and separately releasing feedback. Freeze submitted packages; accept explicit amendments only before ruling and reassess affected review work. Late RFI answers apply prospectively; corrections preserve history.

Alternatives: a supplied historical game, sequential turns, individual information compartments, or split approval roles. Evidence: owner selected a synthetic fixture and these simpler role/turn defaults, then authorized the revised plan. Consequence: the fixture can be walked through without a running application; other policies remain extensions. Zero-action submissions are an initial default, not a claim about all real games. Requirements: GAME-01–02, PLAY-01–05, ADJ-02–04, RFI-04, MEM-04–05. Verification: C01–C10, C12.

### B-03 — Acceptance artifacts before executable tooling

Status: accepted delivery baseline. Problem: executable acceptance needs clear expected behavior without prematurely choosing a stack. Chosen approach: Markdown contracts, JSON sources and role/time snapshots, a separate answer key, and a human reviewer script; no validator or application implementation in Phase 0. Use a provider-neutral static model example with recoverable failure cases.

Alternatives: runnable fixture tooling now, provider-specific integration, or benchmark-first development. Evidence: owner selected fixtures and walkthrough and authorized implementation of that plan. Original consequence: cases were specified, not verified, and the exit gate awaited a human run. B-05 supersedes that human-run requirement and accepts the recorded AI walkthrough for Phase 0 completion; application verification remains future work. Synthetic import provenance exercises mapping without selecting a real external format. Requirements: GAME-04, MEM-01–05, EXP-03, OPS-05/08. Verification: C01–C13 and [walkthrough findings](phase0/findings.md).

### B-04 — Provisional deployment and pilot targets

Status: provisional operational assumptions. Problem: an initial target is needed without available deployment evidence. Chosen approach: offline Ubuntu hosting, Windows VDI browser clients, eight concurrent pilot users, and p95 ordinary interactive request/response latency at or below two seconds, measured separately from inference. Require all seeded mandatory facts/interactions and zero unauthorized disclosures in the walkthrough (AI substitute accepted for Phase 0 by B-05); collect measured human effort before selecting comparative AI improvement thresholds.

Alternatives: early 150-user qualification or invented AI speedup thresholds. Evidence: project scale/offline requirements and the authorized Phase 0 plan; no performance measurements exist. Consequence: confirm identity/platform constraints under O-04, stack under O-05, model/hardware under O-06, and final workload/recovery targets under O-10. Requirements: EXP-03, OPS-01/03–05/07–08. Verification: AI substitute walkthrough accepted under B-05; measured human and application performance in later phases.

### B-05 — AI substitute walkthrough accepted for Phase 0

Date: 2026-09-09. Status: accepted by the project owner; Phase 0 complete. Supersedes the human-run exit requirement in B-03 and the Phase 0 reviewer requirement in B-04.

Problem: preliminary human review was of limited use because JSON was difficult to digest, confounding data-reading mistakes with the intended review task. Chosen approach: accept the completed AI substitute walkthrough as sufficient for Phase 0 closure. Evidence: the owner explicitly accepted the AI pass; the [recorded findings](phase0/findings.md) report Tasks 1–8 completed, C01–C13 met, zero mandatory omissions, and zero unauthorized disclosures.

Alternative: require another human walkthrough of the JSON fixtures before closure. Consequences: Phase 1 may proceed; recorded ambiguities remain handoff work. This decision establishes acceptance of the fixture baseline, not human usability, measured human effort, application correctness, or comparative AI benefit. Future human evaluation should use a readable presentation that separates data-reading difficulty from the intended task. Requirements and coverage remain those of Phase 0; application acceptance tests follow in Phase 1.

## Phase 1 foundation decisions — 2026-09-10

### B-06 — Stack and seven milestone sequence

Update, 2026-09-11: the stack remains selected. B-14 supersedes the remaining
milestone sequence; B-11 governs the wrapper/framework boundary before 1D-remainder.

Status: accepted by the implementation plan. Problem: a playable Phase 1 needs
smaller gates and an authorized database path before presentation conventions.
Choose Python 3.12, uv with a committed lockfile, FastAPI, Pydantic v2,
synchronous SQLAlchemy 2/Psycopg 3, Alembic, PostgreSQL 16, Jinja and local HTMX.
Use host Python and Docker PostgreSQL, one application process, explicit migrations,
injected clocks, shared CSRF/forms, and bounded thread/connection resources.

Deliver 1A, 1B, 1C-core, 1C-admin, 1D, 1E and 1F in dependency order.
Alternative: fixture-specific presentation before database authorization, or one
large domain milestone. Evidence: the owner's revised implementation plan.
Consequence: 1A stages original artifacts; 1B reads the shared full timeline and
uses nine snapshots only as oracles. Typed read models isolate templates from
persistence. See [contracts](phase1/contracts.md) and [setup](development.md).
Requirements: MEM-01/04/05, OPS-02/03/06/07/09; current evidence in
[1A verification](phase1/verification.md).

### B-07 — Temporal, identity, and write authority boundaries

Status: accepted architectural contracts for subsequent milestones. Problem:
historical cutoffs, late disclosure and concurrent writes must preserve meaning.
Choose immutable fact/relationship revisions with stable identities, non-null root
branches, separate simulated validity and UTC recording/disclosure times; authorize
all retrieval and references. Durable internal users remain separate from local
credentials/external subjects. Use optimistic 409 conflicts and transactional
effect idempotency with fingerprint/result storage plus unique effect identity.

Alternatives: overwriting history, null branches, username-based identity merging,
or unconditional retry of effects. Consequence: explicit historical and concurrency
acceptance gates in 1C-core/1D/1E; these domain capabilities are not claimed by 1A.
Requirements: MEM-01–05, PLAY-02–04, ADJ-02–04, RFI-04.

### B-08 — Developer scope and deferred qualification

Update, 2026-09-11: B-14 adds native Windows development setup in 1G and moves
operational research installation/update/recovery to 3A. Local evidence still does
not establish offline deployment or 150-user readiness.

Status: accepted revision to initial Phase 1 installation scope. Problem: local
evidence cannot establish offline deployment or 150-user readiness. Phase 1 targets
developer machines, with local runtime assets and bounded resources; offline
installation, organizational identity integration, TLS, VDI and full-scale capacity
remain deployment obligations. 1F records a “Local eight-user sanity check” with
host/workload/pool waits/latencies/errors and explicitly no 150-user capacity evidence.
OPS-04 needs representative deployment and deadline bursts. Alternative: treating
local pilot results as deployment qualification. Consequence: no such claim; B-04's
p95 two-second target applies only to the measured local run. Phase 2 inference
runs separately from interactive processes, budgets and transactions.

## Maintaining the log

For a consequential decision, record the date, status, problem, chosen approach, alternatives, evidence, and consequences. Link affected requirements and verification. Mark superseded decisions rather than deleting the history. Track optional niceties separately until their value and scope are established.

### B-09 — Phase 1B fixture clarification and development explorer

Status: owner-authorized implementation plan, 2026-09-10. Preserve explicit
asymmetric sharing: Estuary's pledge is public to both councils; Upland's request
is private. Deductions from permitted facts do not grant private source access.
Append a four-credit commitment revision at the 16:00 ruling and disclose it to
both councils at 19:00; retain the prior pledge. Announcement approval deliberately
remains pending. Alternative: symmetric or private pledges, or completing the
announcement storyline. The owner chose clarification of the existing continuation.

Version 2 revises the nine release/cutoff oracles without recharacterizing the
accepted version 1 AI walkthrough. The development explorer loads shared source
records from an explicitly selected staged checksum. Fixed identity selection is
an authorization simulation, not authentication. The read-only routes are absent
outside development. Temporary persistence is replaceable behind typed read models
in 1C-core. Requirements: MEM-01/04/05, PLAY-01/05; C01–C10 retrieval evidence.

### B-10 — Scenario-independent 1C-core and rebuild transition

Update, 2026-09-11: this remains the record of the implemented 1C backend. B-11
makes it a candidate behind the new seam; B-14 moves a second backend with multi-step
traversal and initial replay into Phase 2. The original evidence is unchanged.

Status: implemented direction, 2026-09-10. Replace the reconstructable 1B read
tables with normalized stable identities and immutable record/relationship
revisions. Revision-level disclosures preserve historical authorization. Explicit
purpose/target/pointer references replace JSON suffix inference; opaque bodies do
not acquire links merely because a string resembles an ID. Ordered typed
relationship endpoints are all-or-nothing under authorization.

The migration preserves staged packages and exposes a pending-rebuild state until
an explicit atomic load succeeds. Harbor Relief remains an oracle fixture and
Orchid Accord exercises different cardinality, control mapping, cadence,
vocabulary, custom types, corrections, delayed disclosure, and relationship
revision behavior. PostgreSQL `simple` full-text search and signed watermark
keyset cursors are the lexical/pagination baseline. Multi-hop traversal and
ancestor replay remain deferred to Phase 3. This destructive derived-data
transition is development-only and is not precedent for user data migration.

## Revised roadmap decisions — 2026-09-11

### B-11 — Wrapper ownership and framework contracts

Status: accepted by the project owner before 1D-remainder. Problem: game activation
and authenticated retrieval currently depend directly on the 1C memory schema, and
the former Phase 1 contract required that projection before player writes.

Chosen approach: the wrapper owns canonical input, rulings, facts, effects, world
state, actor beliefs, disclosures and all human review history. It also preserves
immutable run artifacts, including original proposals and exactly what reviewers
saw. Only derived projections, indexes and caches are disposable. A framework
combines an adjudication/preparation method with its memory/retrieval backend;
it receives frozen input and returns proposals through stable contracts.

The input contract includes submissions, scenario premise, prior rulings/facts,
RFI status, disclosures and cutoff. The output contract includes a review packet,
god view and per-actor fog-of-war views, with independent provenance and truth
status. Lookup resolves authorized game memory automatically and flags world
questions for humans; a future reference corpus can register as a resolver.
Frameworks do not write wrapper tables directly; the wrapper owns application of
proposals and does not depend on a candidate's schema. One framework is active per
game; others process saved moves in isolated replay histories.

Supersedes: the mandatory admin-to-memory projection prerequisite in the
[Phase 1 contracts](phase1/contracts.md) and the historical 1C correction handoff.
The decision governs 1D/1E now; 1W completes code decoupling, framework registration
independent of activation, query routing, atomic rebuild and independent recovery.

Alternative: keep the 1C store as mandatory platform persistence. Evidence: the
owner's revised roadmap and approval of the code-coupling review. Consequences:
the wrapper must run without an installed framework; rebuilding a backend must
preserve authoritative history and run artifacts. Existing code is not yet adapted.
Requirements: MEM-05/06, ADJ-02, EXP-02, OPS-06/09. Verification: future 1W gate
and Phase 2 second-method/backend acceptance; no new execution evidence claimed.

### B-12 — Open-world scope, white-cell lens and release

Status: accepted by the project owner. Problem: bounded fixture rules and team
permissions do not describe open-world claims, actor beliefs or white-cell work.

Chosen approach: scenarios have a start date and premise; rules and numeric
resources are optional. Player statements are claims, and scenario premises and
established rulings/RFI facts take precedence over contrary model world knowledge.
Truth, belief and effect remain separate. Military movement/combat and M&S
integration remain excluded under B-01; non-military components remain in scope
even when military activity is their context. No automated M&S routing is required.

The white cell plays unrepresented actors and retains god view. Its optional lens
selects an actor only, using the current game or replay context. No separate time
selector, truth/belief toggle or side-by-side lens requirement is introduced.
N-04 is resolved. Actor knowledge must be recorded, but the lens requires no actor
grants or migration of existing team grants. Controlled actor additions and changes
of control remain implementation work.

Internal evidence remains private unless separately authorized for disclosure.
Audience-visible citations require disclosure checks; approved observations can
be released without exposing confidential causal evidence. Citation checks do not
certify prose. Operational release remains a recorded human decision.

Alternatives: restrict white-cell users to actor permissions; treat citable claims
as facts; infer prose safety from citations. Evidence: the owner's god-view/lens
clarification, actor-only selection and accepted roadmap review. Consequences:
extend B-02 beyond the bounded fixture without rewriting its evidence. Requirements:
GAME-01/05, MEM-01/04/05, ADJ-04, OPS-07. Verification: future 1E lens-fidelity,
claim/precedent and release tests, including prose leakage with clean citations.

### B-13 — Replay defaults and preserved histories

Status: accepted by the project owner. Problem: replay must permit divergence
without contaminating original games or discarding research evidence.

Chosen approach: every replay creates its own wrapper-owned history of rulings,
facts, effects, disclosures, review history and artifacts; the original remains
unchanged. Automated research mode is the default, with a toggle for human review
(N-01 resolved). Record policy selections and changes. Recorded-ruling reuse is
an explicit alternative only where applicable. Operational games still require
human authority; the research default cannot authorize operational releases.

Retain incompatible historical moves as attempted by default (N-05 resolved),
adjudicating feasibility in the replay world. Flag/skip alternatives require a
recorded override. Record applicability of original RFIs, disclosures and rulings.
Phase 4 adds human revision and controller regeneration.

Report frozen-context and trajectory comparisons separately. The former controls
inputs; the latter measures downstream usefulness with divergence and reviewer
controls reported. Automated acceptance provides no measured human-review effort;
use human-review sessions for that evidence.

Alternatives: human review as default, silently inherit original rulings, or drop
incompatible moves. Evidence: the owner selected automated research with a human
toggle and retain-as-attempted, and accepted preserved replay histories. Requirements:
ADJ-03, EXP-02/03, REP-01–04. Verification: future Phase 2 isolation, policy,
cutoff and replay-review gates; Phase 4 continuation tests.

### B-14 — Delivery, setup and operational comparison

Status: accepted revised delivery direction. Problem: fixture results cannot
select a framework for operational game complexity, and offline updates constrain
iteration. Chosen order: B-11 → 1D-remainder → 1E → 1W → Phase 2 → 2M → 1F →
3A → 3B/3C → 4 → 5. Phase 1G runs alongside 1D/1E. This supersedes B-06's
remaining sequence and B-10's deferral of initial traversal/replay to Phase 3.

1G delivers one-command development/evaluation setup on Ubuntu and native Windows
PowerShell; WSL is supported but not required. Document prerequisites and generate
secrets. Dependencies must be pinned and packageable offline. This extends B-08's
development scope without claiming full installer parity or offline provisioning.
Phase 2 delivers queued inference, two methods and two backends; method definitions
are versioned configuration. Phase 2M tests open-world non-military cases, premise
adherence, claims, precedent, lenses, leakage, failure recovery and volume.

Mocks establish behavior on tested cases and eliminate candidates. With one
survivor, operational work validates it rather than claiming comparative selection;
with none, repair/replace and retest. Later variants must pass the same gates.
Phase 3A provides offline research install/update/recovery and internal analysis;
results cannot be exported from that environment. Phase 3 comparisons select on
operational evidence. Full-scale capacity, VDI and deployment qualification remain
Phase 5; 1F retains the original integrated game/recovery gate and local eight-user
report, with no 150-user claim.

Alternative: select on fixtures and defer packaging to Phase 5. Evidence: the
owner's rewritten roadmap and approval of coordinated documentation updates.
Consequences: preserve Phase 0 and completed verification as historical evidence;
collect human effort in the review surface and operational replay sessions.
Requirements: EXP-01–04, MEM-06, OPS-01–09. Verification: the future milestone
gates in the [roadmap](../roadmap.md), not new completion claims in this decision.

### B-15 — Bounded 1D-1 workflow and disposable baseline

Accepted by the owner during the 1D-remainder planning review, implemented 2026-09-12.
Split 1D into draft/submit/amend (1D-1) and coordination/RFI/import (1D-2), each with
its own verification gate. Ownership indicates accountability; all teammates edit.
Native submission requires complete text, permits zero actions, and accepts marked
late submissions. Explicit adjudicator amendment decisions belong to 1D-1; ruling
closure belongs to 1E, with no speculative guard in this increment.

The sole submitter designation remains occupied after deactivation. Add an explicit
atomic replacement workflow and preserve existing deactivation/session/team-blocking
semantics. Stable action IDs survive draft revisions and immutable submissions.
Draft-time coordination/RFI links preserving referenced revisions belong to 1D-2.

The owner confirmed all databases are local, disposable, and contain no real data.
Revise 0005 in place using fixed DDL; rebuild old databases and reject old archives
by bumping exact backup compatibility to 0.3.0. Retain the unused 1D-2 tables and
import FK cycle. This is a development-baseline reset, not a supported data migration.
Evidence: [1D-1 verification](phase1/verification-1d-1.md).

### B-16 — Operational addendum incorporation — 2026-09-15

Status: accepted by the project owner following review of [the addendum](revision.md).
This records intended work, not new implementation or verification evidence.

- Incorporate ADD-01–09 into existing requirements/contracts and milestone gates.
  Keep B-14's delivery order, including 1W after 1E; A/B/C are thematic groupings.
- Human authority governs operational games and release. Preserve B-13's automated
  research default, human-review toggle and isolated, policy-recorded histories.
- Keep the four free-text action fields and minimal player metadata. “Intended
  effect” means “Intent of Action.” No new mandatory tags, modifiers or structured
  targets/resources/timing; optional supplied material and derived interpretations
  remain distinct, with original versions preserved.
- Permit limited relevant game/scenario reference inclusion. Full, robust RAG is
  beyond this application; B-11's retrieval seam remains. This refines the earlier
  blanket reference-corpus exclusion without introducing general corpus ingestion.
- External export is a future requirement (OPS-10), with contents, scope, mechanism,
  authorization and delivery phase unresolved. B-14's current operational deployment
  and internal-analysis constraints remain; no present egress is authorized.
- Add explicit trigger review, bounded configurable state (GAME-06), advisory volume
  support (PLAY-06), retained operational validation approval (EXP-05), and reviewed
  observations (MEM-07). State/decisions/approvals belong to the wrapper; machine
  proposals and retrieval projections use the existing framework contracts.
- Keep the existing evaluation plan unchanged. Additional friction/trigger events
  support its human-effort and quality measures, not substitute success criteria.
  Learning Demand integration and broader capture adapters are not initial gates.

Alternatives: replace the roadmap with A/B/C, add mandatory player structure,
require human research rulings, or build full RAG now. These were not selected.
Evidence: the owner's explicit responses to the documentation review and instruction
to incorporate operational detail without code changes. Verification remains the
future gates in the roadmap; completed Phase 0/1 records remain historical evidence.

### B-17 — Usability delivery and agent-played research games — 2026-09-21

Status: accepted by the project owner following review of the player-capture
proposal and research scope. Documentation only; no new implementation evidence.

- Retain the application as both a playable wargame environment and the research
  platform that generates and preserves experimental histories. Do not replace it
  with a standalone synthetic-action generator or graph benchmark.
- The immediate next session resolves the recorded usability issues and implements
  the revised design in existing templates before advancing to 1D-2. Use the
  usability review's workstreams and acceptance checks, the design guide, examples,
  and navigation inventory. Proposed layouts are not implemented behavior; unresolved
  lifecycle choices still require explicit resolution, not a styling-side change.
- Preserve B-14's major phase order and B-16's operational scope. Complete the
  minimum game loop through 1D-2/1E and the framework boundary in 1W. Within Phase 2,
  make a small end-to-end agent-played research game an explicit checkpoint before
  the full two-method/two-backend comparison. One initial working framework suffices
  for that checkpoint, not for the Phase 2 exit gate.
- Use DATE World for this game. Region, countries, crisis, participants, turn count,
  action volume and reference-package selection are deferred until closer to the
  test. Earlier illustrative numbers and scenario suggestions are not requirements.
  Retain non-military DIME-FIL scope; military context does not add combat/movement
  adjudication or M&S integration.
- Preserve a versioned DATE reference package, exercise-specific additions and
  generated game history as distinct sources. Agents act through supported
  application operations under authorized views. Browser versus agent-tool access
  remains open; both must obey the same authority, validation and version rules.
- Use agent-played histories alongside curated cases with known expectations.
  Inspect generated histories for meaningful adaptation and cross-turn relationships;
  diversity and realism are hypotheses, not guaranteed properties. Freeze histories
  for controlled comparisons; separately report divergent trajectory experiments.
- Do not adopt the coworker's structured Execution Context form as a new player
  requirement. Keep natural-language submissions. Team confirmation of a system
  interpretation remains a later experiment, not a submission prerequisite or
  first-game gate. Confirmation would establish intended meaning, not game truth;
  timing, reviewer eligibility and correction mechanics remain undecided.
- Preserve the larger 2M narrowing workload, 1F integrated recovery gate, human
  evaluation and operational selection. Agent play supplies no human-usability or
  human-effort evidence and does not select graph storage in advance.

This refines B-14's delivery sequence with an immediate usability gate and a
Phase 2 checkpoint, and extends B-16's evaluation planning without changing its
human-authority or minimal-input boundaries. Verification is through the future
[roadmap gates](../roadmap.md); completed verification remains historical evidence.

### B-18 — Usability alignment policies (1U)

Status: decided by the project owner, recorded 2026-09-21. Governs the
[1U milestones](phase1/usability-alignment.md); no implementation is claimed.
Supersedes earlier policy statements where they conflict, including B-15's
requirement for explicit adjudicator decisions on every revision. Historical
verification remains evidence of the behavior tested at that time.

#### Submission and revision

- **Late first submissions are allowed.** A first submission may be made in the active turn at or after the deadline. Players and adjudicators see a visible late indicator.
- **Revisions before the deadline take effect immediately.** A revision submitted strictly before the deadline becomes the effective submission when it commits. This does not create an adjudicator decision.
- **Revisions at or after the deadline need acceptance.** They become effective only when an adjudicator accepts them. The existing accept/reject workflow is kept, and rejection reasons stay visible to players.
- **Which deadline governs.** The deadline is copied from the governing configuration at first submission. Every later revision is judged against `Submission.deadline`. Turns that have started can't be redefined.
- **Server time decides.** The deadline and authorization are checked against server time read after acquiring the mutation locks, immediately before the policy check.
- **One pending revision at a time.** A pending revision blocks another submission. Teammates can keep editing the draft, and the UI explains why submission is blocked. Withdrawing a pending revision is deferred.
- **Wording.** The action is labelled Submit revision. The confirmation states the actual consequence: effective immediately, or adjudicator acceptance required.

#### Confirmation and retries

- **Confirmation states what the user expects.** It carries the effective version, the deadline and the outcome the user expects (immediate or approval required). If any of these changes before commit, the server returns "confirmation required," writes nothing and does not claim the request key.
- **A renewed confirmation is a new request.** It uses a fresh request key. If an outcome is uncertain, the application must first reconcile or retry the original command with its original key.
- **Retries keep their original meaning.** On retry, authorization is checked first. A completed matching request is then recognized before the deadline is re-evaluated, so a retry never duplicates a submission or changes what an operation meant.

#### Turns and history

- **Only the current turn is writable.** Writes stay limited to the active current turn. No new turn-lock, ruling or release lifecycle is introduced.
- **Existing history is preserved.** Submitted versions, decisions and pending amendments are kept. Existing pending amendments still require a decision.
- **How versions become effective is recorded.** Each change of effective version gets an append-only record of the mechanism (`initial`, `immediate_revision` or `adjudicator_acceptance`), the responsible user and the time. Existing records are backfilled from immutable data, with no invented events.

#### Collaboration and ordering

- **Explicit saves.** Users save explicitly, and saved changes from teammates appear automatically. There's no simultaneous text editing and no autosave.
- **Teammate updates never overwrite unsaved work.** Clean regions refresh on their own. Regions with unsaved edits are kept, and conflicts offer three choices: current, mine, or combined.
- **Sorting is not ordering.** Display sorting is local presentation only. Only explicit reorder commands change the saved submission order.

#### Accounts and participants

- **Reactivation.** Reactivating an account restores sign-in and the grants that still exist, re-checked against current authorization, roster and team-authority rules. The consequences are previewed first. Revoked sessions, removed grants and replaced submitter authority are never restored.
- **Password reset.** Resetting a password revokes existing sessions. The existing password policy is unchanged: no temporary passwords and no forced change at first sign-in.
- **Credentials stay out of records.** Passwords never appear in logs, history, operation records, result artifacts, retained form values or error echoes.
- **Submitter invariant.** Each team keeps exactly one designated submitter. When a replacement isn't available, the UI explains why.
- **LDAP is out of scope.** It remains a future integration.

#### Setup

- **Teams can be added only before activation.** Adding a team is allowed only in draft games and keeps the configuration and team state consistent. Roster changes in active games stay prohibited.
- **Identifiers are generated.** The server generates stable identifiers. Users select games and teams by name and never type internal IDs.
- **Configuration stays strict.** Editing preserves every supported configuration field. Unknown fields are rejected explicitly, consistent with the strict model.

#### Scope boundaries

- **What 1U excludes.** Coordination, RFIs, imports, 1E ruling/release workflows, simultaneous editing, LDAP and the Execution Context alternative are all outside 1U.
- **Adjudicator review.** 1U delivers a dedicated adjudicator page for the existing amendment accept/reject flow only.
- **No-JS limitation.** Without JavaScript, a browser reload can't trigger an application-controlled warning about unsaved changes. This limitation is documented and not claimed as passing.
