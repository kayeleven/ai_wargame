# Architecture and data model

Status: conceptual architecture with Phase 1 stack and contracts accepted on 2026-09-10 under B-06–08. The [Phase 1 contracts](phase1/contracts.md) govern implementation; the [developer guide](development.md) describes the 1A runtime. Requirements are authoritative for intended capabilities.

## System boundaries

Use a shared game core with three interfaces: player workspace, adjudication workspace, and experiment/replay workspace. A browser client is the proposed access model for Windows VDI. The application server owns permissions and game transitions; workers handle AI and other long-running jobs.

Begin with a modular application rather than requiring many independently deployed services. Allow workers, the database, and local inference to run separately when capacity requires it. Keep model providers, storage/retrieval implementations, and import adapters behind explicit contracts.

The game core must operate when inference is unavailable. AI outputs are proposals. Operational authority comes from recorded human decisions; an experiment may explicitly select automated decisions.

The initial slice handles non-military DIME-FIL actions. Military movement/combat submission and adjudication remain in the separate M&S workflow; its integration is outside this build. The [Phase 0 contracts](phase0/contracts.md) define the initial submission and review baseline.

## Living memory

Living memory combines preserved source material, structured facts and relationships, temporal history, and derived retrieval views. A narrative summary is a convenience, not the sole record of truth.

| Record | Essential distinctions |
| --- | --- |
| Game / scenario version | Configuration, initial conditions, rules, and lifecycle policy. |
| Branch | Parent, divergence point, changes, and downstream replay policy. |
| User / team / actor / controller | Identity, collaboration membership, represented entity, and who supplies its actions. |
| Turn | Simulated interval, wall-clock deadlines, status, and state version. |
| Turn submission / action version | Overall free-text turn intention and variable-length actions with Title, Description, Intent of Action, and Anticipated reaction; immutable submitted package versions, stable action IDs, author/controller, and submission status. Derived resources, targets, and timing are separate source-linked interpretations. |
| Coordination record | Participants, shared purpose, linked actions, explicit commitments, and visibility. |
| Review issue | Decision needed, related actions, evidence, information gaps, and suggested alternatives. |
| Adjudication run | Method configuration, frozen inputs, retrievals, outputs, validation, timing, and review edits. |
| Ruling / effect | Authority, decision, effective time, duration, status, and applied changes. |
| Claim / observation / knowledge record | Source, subject, audience, confidence or dispute, and time learned. |
| RFI / response | Question type, participants, status, evidence, affected issues, and state/knowledge implications. |
| Relationship | Typed endpoints, source/evidence, inferred or confirmed status, and temporal/visibility scope. |
| Event / evidence artifact | Immutable history entry or original material supporting a record. |

Use stable identifiers. Track simulated effective time and recording time separately, including when a fact becomes available to each audience. Preserve corrections as new versions/events. An intended action can be approved, active, interrupted, completed, or cancelled; an outcome must not be inferred simply because a submission exists.

Distinguish canonical world state from actor knowledge and adjudicator context. The god-view includes hidden canonical information and unresolved facts, but should not pretend unknown facts are settled. Adjudicator context can be a bounded selection of that view for a particular experiment.

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

Inputs include game/branch/turn identifiers, submitted versions, the authorized state view at a specified point, rules, prior effects, evidence, RFI status, and method configuration.

Outputs include review issues, proposed relationships, evidence references, unresolved lookups, assumptions, alternatives or recommended outcomes, proposed state changes, and proposed player disclosures. Store the reviewable rationale and actual output; do not require access to a model's private internal reasoning.

Methods may request more context through a permission- and time-scoped retrieval interface. Record what was requested, returned, and unavailable. Reconciliation must retain access to an all-action index and continuing effects rather than relying exclusively on lossy batch summaries.

Treat imported text and player submissions as game data, not trusted instructions to the model or application. Validate structured outputs and authorize all proposed changes through the game core.

## Knowledge and access control

Apply authorization before retrieval and AI context construction, not only when rendering a final answer. Enforce it consistently on source documents, graph traversal, search, attachments, caches, generated summaries, and exported records.

The initial baseline shares knowledge across team members and designates submission authority. Individual information compartments remain a possible later policy, not part of the initial fixture (B-02). Cross-team coordination shares specific records, not entire team histories. Preserve what was actually disclosed so historical player views can be reconstructed after later revelations.

## Replay and AI participation

Preparation replay freezes historical actions and context while changing assistance methods. Adjudication replay reconsiders rulings with submissions fixed. Counterfactual gameplay changes actions, controllers, or represented actors and permits subsequent divergence.

Branches preserve their parent and divergence point. Historical retrieval excludes later knowledge and unrelated branches. Identify downstream invalidation: changing an early resource allocation can make a later action infeasible. Record whether later moves are retained where valid, revised by humans, or regenerated by controllers.

Separate actors from controllers. Human, AI, and imported controllers use the same submission boundary and authorized actor view. Adding an AI-controlled actor is a scenario intervention as well as a controller choice and must be recorded for comparisons.

Persist actual model responses. A saved random seed may reproduce a probabilistic draw but does not guarantee identical model generation; exact artifact replay and a fresh model rerun are distinct operations.

## Deployment and operations

Proposed topology: browser clients → application service → durable storage and job queue; workers communicate with local inference and retrieval services. This describes logical roles, not a required number of hosts or containers.

Provide small-evaluation and full-game profiles using the same data model. Guided installation/admin flows should configure addresses, certificates, storage, authentication, model endpoint, and initial users/teams. Exportable validated configuration should support repeat installations without normal reliance on manual Compose or environment-file editing.

Offline bundles must include required application/runtime dependencies and browser assets, plus documented local model provisioning. Plan dependency inventories, integrity verification, migrations, backup/restore, diagnostic export, and recovery. Diagnostics and exports must respect information sensitivity and permissions.

Measure interactive latency separately from inference throughput. Queue AI work with status, priority, retry, and cancellation; protect interactive operations during submission bursts. Identity provider, supported Ubuntu/browser versions, inference hardware, and performance/recovery targets remain open in [decisions.md](decisions.md).
