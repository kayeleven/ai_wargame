# Requirements

Status: initial planning baseline, consolidated 2026-09-09. This document specifies intended capabilities, not current implementation. Acceptance evidence describes what must be demonstrated; detailed performance thresholds remain to be established.

## Purpose and scope

The platform has two related purposes:

1. Evaluate AI pre-adjudication methods that reduce human workload, forgotten context, missed action interactions, and effort producing player feedback.
2. Run actual configurable DIME-FIL wargames through integrated player and adjudicator interfaces.

Initial adjudication accuracy is secondary to usefulness as a starting point for human review. Accuracy, coherence, and information handling still constrain whether assistance is useful. Automated AI-v-AI experiments are supported, but operational games retain human authority over rulings and state publication.

## Initial action scope and submission baseline

The initial build covers non-military DIME-FIL actions. Military movements and combat are submitted separately to an M&S tool and adjudicated there. Military submission, adjudication, and M&S integration are a separate task.

Each player submits one overall free-text intention for the turn and a variable-length collection of actions. Each action has four free-text fields: **Title**, **Description**, **Intent of Action**, and **Anticipated reaction**. There is no fixed game-level action limit; the Phase 0 baseline permits an intention-only submission. Preserve the original text. Structured resources, targets, timing, and classifications may be separately interpreted for review but are not mandatory player-authored fields. Anticipated reactions are expectations, not observations. See the [Phase 0 contract](docs/phase0/contracts.md).

## Game configuration and participation

| ID | Requirement | Acceptance evidence |
| --- | --- | --- |
| GAME-01 | Configure scenario, initial state, rules, actors, teams, objectives, resources, and relationships for each game. | Two materially different scenarios can be configured without application code changes. |
| GAME-02 | Configure player count, turn count, simulated turn duration, submission deadlines, and turn-resolution policy. Simulated duration and wall-clock deadlines are separate. | Games with different timing and participation settings execute their configured lifecycle. |
| GAME-03 | Support AI-v-AI, human-v-AI, human-controlled play, and mixed control, including multiple users per team. | The same scenario runs with different controller assignments. |
| GAME-04 | Import or substitute moves from other wargames, preserving original content, provenance, mapping, and missing context. | An imported move enters the same preparation and review workflow as a native submission. |
| GAME-05 | Add AI controllers for countries, regions, or other actors not otherwise represented, and permit recorded changes in control. | An added actor acts through its configured capabilities, objectives, and information view. |

## Player workspace and collaboration

| ID | Requirement | Acceptance evidence |
| --- | --- | --- |
| PLAY-01 | Create, revise, review, and submit versioned turn packages containing overall intention and actions in the baseline free-text structure. Preserve timing, targets, resources, and supporting material where supplied; keep derived interpretations separate. | Reviewers can recover the exact submitted version despite later draft changes. |
| PLAY-02 | Provide integrated intra-team collaboration: shared drafts, discussion, comments, ownership, revision history, and submission authority. | Multiple teammates collaborate without silent overwrites or unauthorized submission. |
| PLAY-03 | Support permitted coordination of effects within and across teams, including linked actions and explicit commitments. | Participants can inspect a shared coordination record without gaining access to unrelated private material. |
| PLAY-04 | Let players query their current and historical view of the game, submit RFIs, and receive meaningful turn feedback. | Answers and feedback reference information available to that player; unauthorized facts are excluded. |
| PLAY-05 | Distinguish drafting, discussion, commitment, submission, and adjudicated outcome. | A discussion or draft does not independently change canonical world state. |

## Adjudication and living memory

| ID | Requirement | Acceptance evidence |
| --- | --- | --- |
| ADJ-01 | Prepare review issues from submissions, including grouped interacting actions, evidence, uncertainties, and suggested consequences. | A human can navigate from an issue to source submissions and supporting history. |
| ADJ-02 | Support human triage, edits, relationship confirmation/rejection, issue splitting/merging, decisions, and state updates. | Human changes and their authorship are preserved alongside AI suggestions. |
| ADJ-03 | Make human-approved rulings authoritative in operational games. Permit an explicitly configured automated mode for research runs. | Unapproved AI proposals do not become authoritative operational state. |
| ADJ-04 | Prepare player feedback from approved effects and authorized observations, with review and release controls. | Different players receive appropriate accounts of the same turn and adjudicators can trace each account. |
| MEM-01 | Maintain living memory distinguishing intents, commitments, rulings, effects, observations, claims, assumptions, and unresolved facts. | Retrieval does not present a proposal, rumor, or assumption as an established outcome. |
| MEM-02 | Track active, delayed, continuing, interrupted, completed, and cancelled actions/effects across turns. | A commitment from three turns earlier is retrieved when relevant, with its current status. |
| MEM-03 | Link actions across players and time, including prerequisites, enabling effects, competition, opposition, shared targets, and resource contention. | A seeded cross-player interaction is surfaced with supporting evidence and confidence/status of the link. |
| MEM-04 | Provide an adjudicator god-view and permission-aware player fog-of-war views, including quick reference and source-grounded queries. | Equivalent queries produce the appropriate distinct views, including in search, summaries, and graph traversal. |
| MEM-05 | Preserve provenance, versions, simulated effective time, recording time, and visibility. Corrections retain history. | Prior state and what was known at a decision point can be reconstructed. |
| MEM-06 | Enable comparison of storage and retrieval methods through stable interfaces. Evaluate graph-based relationship storage without assuming it is the final choice. | Comparable retrieval cases can be run against alternative implementations or projections. |

## RFI workflow

| ID | Requirement | Acceptance evidence |
| --- | --- | --- |
| RFI-01 | Record requester, question, recipient, status, visibility, linked actions/issues, response, evidence, and relevant times. | An RFI remains traceable from submission through answer and affected decisions. |
| RFI-02 | Distinguish intent clarification, retrieval of known information, requests for intelligence collection, and establishment of unspecified scenario facts. | Responses explicitly identify whether they affect knowledge, assumptions, or canonical state. |
| RFI-03 | Incorporate answered RFIs into relevant preparation and authorized memory views. Surface unanswered dependencies. | A dependent issue shows the answer or an unresolved information need. |
| RFI-04 | Apply an explicit policy for late answers and corrections: prospective use, review, or branching. | A late response does not silently rewrite a historical ruling. |

## Experiments and replay

| ID | Requirement | Acceptance evidence |
| --- | --- | --- |
| EXP-01 | Compare single-pass, lookup-then-review, batch-then-reconcile, and combined preparation methods. | Methods accept equivalent cases and return reviewable outputs under a common contract. |
| EXP-02 | Preserve experiment configuration, model identity/settings, prompts, supplied context, retrievals, raw outputs, validation failures, human edits, timing, and resource use where measurable. | A result can be inspected and attributed to its inputs and method. |
| EXP-03 | Measure human effort, omissions, irrelevant flags, corrections, feedback quality, coherence, and information discipline. | A comparison report includes human-review outcomes, not only model plausibility scores. |
| EXP-04 | Distinguish modeled outcome uncertainty from variability between AI responses. | Repeated runs and sampled world outcomes are separately identifiable. |
| REP-01 | Branch old games at a recorded point, modifying one or several actions or adding participants without altering the original. | Original and branch histories remain independently inspectable. |
| REP-02 | Support preparation replay, adjudication replay, and counterfactual gameplay as distinct modes. | A replay identifies what was held fixed and what could change. |
| REP-03 | Identify downstream invalidation and explicitly handle later historical actions after divergence. | Infeasible later actions are flagged, revised, or regenerated under a recorded policy. |
| REP-04 | Prevent future information or another branch's records from contaminating historical preparation. | Replay retrieval tests exclude facts unavailable at the selected point. |

## Deployment and operational requirements

| ID | Requirement | Acceptance evidence |
| --- | --- | --- |
| OPS-01 | Operate on an air-gapped installation using a locally hosted LLM, with no required external services. | Core workflows succeed with external network access disabled. |
| OPS-02 | Make installation and initial configuration guided workflows rather than requiring in-depth Compose or environment-file editing. | An administrator installs and configures using documented installer/admin flows. |
| OPS-03 | Keep application boundaries system-agnostic. Target Ubuntu server first; browser access from Windows VDI is the current deployment assumption. | Supported Ubuntu deployment and target VDI browser workflows are verified; platform-specific requirements are documented. |
| OPS-04 | Support single-digit-user evaluation and up to 150 simultaneous users for full games. | A representative 150-user workload, including submission bursts and team collaboration, meets agreed performance thresholds. |
| OPS-05 | Separate interactive work from queued AI processing; expose job status, cancellation, and recoverable errors. | Users can submit, collaborate, and adjudicate while inference is saturated or unavailable. |
| OPS-06 | Provide offline installation/update artifacts, dependency inventory, integrity verification, migration, backup, restore, and recovery procedures. | Clean offline installation, upgrade, and restoration are exercised using documented artifacts. |
| OPS-07 | Enforce permissions for teams, roles, shared coordination, attachments, queries, graph links, AI context, and released feedback. | Negative access tests cover direct access and indirect leakage through retrieval and generation. |
| OPS-08 | Support configurable local model endpoints with capability checks and output validation. | Unsupported capabilities and invalid responses produce actionable, recoverable failures. |
| OPS-09 | Keep state updates, submissions, and background processing safe under concurrency, retries, and service restarts. | Tests show no duplicate applied effects, silent lost edits, or partially committed rulings. |

## Boundaries and unresolved specifications

The initial scope does not require a comprehensive domain simulation, a universal import format for all wargames, simultaneous character-level document editing, or multi-platform installer parity. These are possible extensions, not established requirements.

The final stack, database choice, identity integration, model/hardware sizing, numerical performance targets, recovery objectives, and detailed collaboration policy remain open. See [decisions](docs/decisions.md). Delivery order is in [roadmap.md](roadmap.md).
