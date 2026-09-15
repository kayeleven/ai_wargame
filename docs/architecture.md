# Architecture and data model

Status: accepted direction updated 2026-09-15 under B-11–B-16. The [Phase 1 contracts](phase1/contracts.md) govern remaining work; the [developer guide](development.md) describes the current runtime. The implemented 1C store and 1D persistence foundation do not yet implement the framework boundary, white-cell lens, AI or replay described here.

## System boundaries

The wrapper owns identity, teams, actors, configuration, player and adjudication
workspaces, the white-cell lens, release, replay orchestration and experiment records.
Frameworks combine an adjudication/preparation method with memory and retrieval.
One framework is active per game; alternatives process saved moves in isolated
replays. Browser access supports Windows VDI. Workers handle AI and long-running jobs.

Begin with a modular application rather than requiring many independently deployed services. Allow workers, the database, and local inference to run separately when capacity requires it. Keep model providers, storage/retrieval implementations, and import adapters behind explicit contracts.

The wrapper must run a game with no framework installed and continue when inference
fails. Frameworks return proposals and never directly write wrapper tables. Operational
authority comes from human decisions. Research replay defaults to automated acceptance
with a human-review toggle; its selected policy is recorded and cannot authorize
operational releases.

The initial slice handles non-military DIME-FIL actions. Military movement/combat submission and adjudication remain in the separate M&S workflow; its integration is outside this build. The [Phase 0 contracts](phase0/contracts.md) define the initial submission and review baseline.

Non-military components remain in scope when military activity is their context;
military components are handled outside this application, with no automated routing.
Scenarios have a start date and premise, optional rules/resources, and no fixed
action space or numeric win condition. Player statements are claims. Scenario
premises and established precedent take priority over contrary model world knowledge.

## Ownership and transition

| Data | Ownership and durability |
| --- | --- |
| Canonical input, rulings, established facts, effects, world state, actor beliefs, disclosures, human triage/edits/regrouping and effort | Wrapper-owned authoritative history, preserved across framework changes. |
| Original proposals, grouping, raw output, supplied context, validation failures and exactly what reviewers saw | Immutable wrapper-held run artifacts; never replaced by regenerated model output. |
| Indexes, caches, embeddings and derived projections/materializations | Framework-owned, disposable and rebuildable from preserved history/artifacts. |

B-11 supersedes the old requirement to project player writes into 1C before 1D.
Current activation still creates a memory dataset and `/memory` directly uses the
1C reader/schema. Phase 1W moves creation behind framework registration, routes
queries through the interface, and verifies atomic rebuild and wrapper recovery
without a framework. B-11 governs 1D/1E before that code transition is complete.

## Living memory

Living memory combines preserved source material, structured facts and relationships, temporal history, and derived retrieval views. A narrative summary is a convenience, not the sole record of truth.

The existing Phase 1C-core implementation is a scenario-independent PostgreSQL projection
and will become the first candidate backend.
Datasets own a minimal game and non-null root branch, visibility scopes, stable
record and relationship identities, immutable revisions, revision-level
disclosures, explicit references, and ordered role-labelled relationship
endpoints. Bodies remain opaque JSON; only scalar text is indexed. Authorization
is applied in SQL before search, counts, pagination, references, or one-hop
relationships. An unauthorized record/action endpoint suppresses its whole
relationship, preserving endpoint arity and topology.

The `0003` migration is an exceptional development transition: it preserves
staged source artifacts, marks them pending rebuild, and drops the reconstructable
1B projection. Each manifest package must then be rebuilt explicitly and
atomically. This is not a policy for future non-reconstructable user data.

| Record | Essential distinctions |
| --- | --- |
| Game / scenario version | Start date, premise, initial conditions, optional rules/resources, actors and lifecycle policy. |
| Branch | Parent, divergence point, changes, and downstream replay policy. |
| User / team / actor / controller | Identity, collaboration membership, represented entity, and who supplies its actions. |
| Turn | Simulated interval, wall-clock deadlines, status, and state version. |
| Turn submission / action version | Overall free-text turn intention and variable-length actions with Title, Description, Intent of Action, and Anticipated reaction; immutable submitted package versions, stable action IDs, author/controller, and submission status. Derived resources, targets, and timing are separate source-linked interpretations. |
| Coordination record | Participants, shared purpose, linked actions, explicit commitments, and visibility. |
| Review issue | Decision needed, related actions, evidence, information gaps, and suggested alternatives. |
| Adjudication run | Method configuration, frozen inputs, retrievals, outputs, validation, timing, and review edits. |
| Ruling / effect | Authority, decision, effective time, duration, status, and applied changes. |
| Claim / observation / knowledge record | Source, subject, claim audience, actor belief, independent truth status and provenance class, and time learned. |
| RFI / response | Question type, participants, status, evidence, affected issues, and state/knowledge implications. |
| Relationship | Typed endpoints, source/evidence, inferred or confirmed status, and temporal/visibility scope. |
| Event / evidence artifact | Immutable history entry or original material supporting a record. |

Use stable identifiers. Track simulated effective time and recording time separately, including when a fact becomes available to each audience. Preserve corrections as new versions/events. An intended action can be approved, active, interrupted, completed, or cancelled; an outcome must not be inferred simply because a submission exists.

Distinguish canonical world state from actor knowledge and adjudicator context. The god-view includes hidden canonical information and unresolved facts, but should not pretend unknown facts are settled. Adjudicator context can be a bounded selection of that view for a particular experiment.

## Operational records and review detail

Under [B-16](decisions.md#b-16--operational-addendum-incorporation--2026-09-15), extend
the modular wrapper rather than add a separate triage application. Reuse immutable
workspace package/action IDs and versions for direct preparation and narrow imports.
“Intended effect” is the existing Intent of Action; optional source attachments and
metadata do not create mandatory player tags or a structured action language.

- **Trigger evaluations:** wrapper-owned records link player statements and action,
  ruling, RFI, state and temporal dependencies to exact source versions. Preserve
  proposed status, evidence, uncertainty, cutoff, audience and decision history.
  Relevant changes mark affected reviews stale; reevaluation never erases prior
  evidence or independently reapplies effects. Operational applicability, feasibility,
  interpretation and effects are separate recorded decisions; research uses its policy.
- **Scenario state:** separate versioned variable definitions (category, type, unit,
  source, update authority and visibility) from baseline/subsequent value revisions.
  Revisions carry effective and recording times, uncertainty/dispute, rationale and
  ruling/effect links. Canonical values, beliefs and disclosures are distinct. Use
  existing atomic authority/version checks; no universal simulation is implied.
- **Observations:** store collected evidence with source, collection method, subject,
  time, confidence and review status. Review can establish a fact or authorize a
  player-facing disclosure through distinct decisions. Imported/automated material
  starts unverified. Broader capture adapters follow the same write boundary;
  Learning Demand integration remains unspecified.
- **Validation records:** the wrapper retains cases/results, known limitations,
  acceptance criteria, fallback, reviewer approval and the game context and exact
  method/model/prompt/retrieval configuration approved for operational use. Material
  behavioral changes require revalidation; research execution retains its own policy.
- **Instrumentation:** wrapper events retain workflow/review history and configuration
  identity. Counts and advisory flags need no new player fields. Capture active time
  separately from elapsed time; record re-entry/bypass through explicit reporting
  where activity is external. Interpret evidence using the unchanged evaluation plan.

Frameworks propose evaluations, relationships and retrieval results; they do not own
these authoritative histories. Introduce versioned contracts in the existing modular
application, without requiring independent services or a public API for every record.

## Storage proposal

Use an append-only event/decision history and periodic snapshots or materialized views for efficient current-state access. Preserve original submissions and model artifacts. The precise degree of event sourcing is an implementation decision, not a requirement to adopt a specific framework.

Evaluate a graph projection for relationships among actions, effects, actors, resources, places, and evidence. A relational representation of typed links is a valid baseline. A graph database is not yet selected. If projections are separate, establish one authoritative write path and rebuildable projections to avoid conflicting sources of truth.

Derived summaries and indexes must identify their source versions and be refreshed or invalidated after relevant changes. Retrieval should support entity, temporal, relationship, text, and potentially semantic queries; embeddings are optional and must be locally available if adopted.

## Turn and review workflow

Phase 0 default: simultaneous submission followed by joint review, with versioned amendments accepted by the adjudicator before ruling. Sequential resolution is a future configurable policy, not part of the initial fixture. See decision B-02.

1. Players draft actions and coordinate under team/sharing permissions.
2. Submission captures a stable version. Subsequent amendments are explicit.
3. Preparation identifies relevant history, possible interactions, and missing information.
4. Reviewers triage issues, resolve RFIs, refine suggestions, and record rulings.
5. Approved effects update canonical state under a consistent transaction/version boundary.
6. Approved observations and messages are released to the appropriate players.

Discussion does not create a commitment automatically; commitments do not create effects automatically. RFIs can be active throughout the lifecycle. Record whether an answer clarifies intent, communicates existing information, initiates collection, or establishes a missing scenario fact. Apply late answers under the game's explicit correction policy.

Background jobs should carry input state/submission versions. If inputs change, mark their results stale or re-run them rather than presenting them as current. Retried jobs and state commits must not duplicate applied effects. Concurrent human edits need conflict detection; character-level live editing is not assumed for the initial version.

## AI preparation contract

Inputs freeze game/replay/turn identifiers, submissions, scenario premise, prior
rulings and established facts, effects, evidence, RFI status, disclosure records,
temporal cutoff and versioned method configuration. Preserve player prose verbatim.

Outputs include a review packet, proposed god view and proposed per-actor fog-of-war
views, with issues, relationships, evidence, gaps, alternatives, proposed effects
and disclosures. Label each item independently by provenance (game record, world
knowledge, assumption) and truth status (established, claimed, disputed, unresolved).
A citable claim is not an established fact. Preserve author kind, method/framework
and run identity, proposal state and human changes. Store reviewable rationale and
actual output; do not require a model's private internal reasoning.

Methods may request more context through a permission- and time-scoped retrieval interface. Record what was requested, returned, and unavailable. Reconciliation must retain access to an all-action index and continuing effects rather than relying exclusively on lossy batch summaries.

The lookup contract resolves game-memory requests automatically under authorization;
world-specific questions are flagged for human verification. Limited approved game/scenario reference material may be included with
source versions, provenance, visibility and cutoff controls. Full, robust RAG is
beyond this application; external retrieval can use the resolver seam. Prompts, pass structure, batch
strategy, lookup budgets and model settings are versioned configuration so operational
method iteration does not require an application code update.

Treat imported text and player submissions as game data, not trusted instructions to the model or application. Validate structured outputs and authorize all proposed changes through the game core.

## Knowledge and access control

Apply authorization before retrieval and AI context construction, not only when rendering a final answer. Enforce it consistently on source documents, graph traversal, search, attachments, caches, generated summaries, and exported records.

The team access and submission-authority baseline remains. Cross-team coordination
shares specific records, not entire histories. Preserve actor beliefs and actual
disclosures so historical fog-of-war views can be reconstructed. Individual user
compartments remain outside the initial baseline.

The white cell plays unrepresented actors and retains god-view access. An optional
actor-only lens filters presentation using the current game/replay context, with a
clear active indicator and return to god view. It uses the same actor information
as fog-of-war views; it requires neither actor grants nor migration of team grants.
There is no separate lens time selector, truth/belief toggle or side-by-side requirement.
Actor additions and controller changes need a controlled path; current validation
requires every actor to have a team and rejects roster changes.

Keep internal evidence separate from audience-visible citations. Check disclosed
citations against audience rules. An explicit human decision can release an
observation without exposing its confidential cause. Checks on citations do not
certify prose: test leakage even when citations are public. The white-cell person's
god view does not authorize releasing everything they can see.

## Replay and AI participation

Preparation replay freezes historical actions and context while changing assistance methods. Adjudication replay reconsiders rulings with submissions fixed. Counterfactual gameplay changes actions, controllers, or represented actors and permits subsequent divergence.

Replays create independent wrapper-owned histories of rulings, facts, effects,
disclosures, review activity and artifacts, preserving the original game. Framework
projections derive from their own trajectory. Historical retrieval excludes later
knowledge and unrelated trajectories. Record the framework and ruling policy for
each run: automated research by default, a toggle for human review, or explicitly
selected reuse of applicable recorded rulings.

When a recorded move becomes incompatible, retain it as attempted by default and
adjudicate feasibility in that trajectory. Record flag/skip overrides and whether
original RFIs, disclosures and rulings remain applicable, are re-derived or withheld.
Phase 2 implements this minimum; Phase 4 adds human revision/controller regeneration.
Frozen-context tests hold one turn's inputs fixed; trajectory tests measure downstream
usefulness. Report the modes separately with divergence and reviewer controls.

Separate actors from controllers. Human, AI, and imported controllers use the same submission boundary and authorized actor view. Adding an AI-controlled actor is a scenario intervention as well as a controller choice and must be recorded for comparisons.

Persist actual model responses. A saved random seed may reproduce a probabilistic draw but does not guarantee identical model generation; exact artifact replay and a fresh model rerun are distinct operations.

## Deployment and operations

Proposed topology: browser clients → application service → durable storage and job queue; workers communicate with local inference and retrieval services. This describes logical roles, not a required number of hosts or containers.

Provide small-evaluation and full-game profiles using the same data model. Guided installation/admin flows should configure addresses, certificates, storage, authentication, model endpoint, and initial users/teams. Exportable validated configuration should support repeat installations without normal reliance on manual Compose or environment-file editing.

Phase 1G adds one-command development/evaluation setup on Ubuntu and native Windows
PowerShell, with WSL optional, documented prerequisites and generated secrets. It
does not qualify offline provisioning or full installer parity. Every dependency
must be pinned and packageable offline. Phase 3A bundles all surviving candidates,
dependencies and local model provisioning with integrity checks and repeatable
updates. Preserve games and artifacts through migrations and recovery. Analysis,
reporting and diagnostics run inside the operational environment; results cannot
be exported. Phase 5 qualifies the full deployment and 150-user/VDI workloads.

Measure interactive latency separately from inference throughput. Queue AI work with status, priority, retry, and cancellation; protect interactive operations during submission bursts. Identity provider, supported Ubuntu/browser versions, inference hardware, and performance/recovery targets remain open in [decisions.md](decisions.md).

## Future external export

External export is required eventually (OPS-10/B-16). Contents, scope, formats,
mechanism, authorization and delivery timing remain open. Current operational
analysis and reporting remain inside the environment. This acknowledges a future
capability without defining a payload, authorizing egress, or requiring M&S integration.
