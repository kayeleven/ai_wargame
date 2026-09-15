# Living Memory — Adjudication Workflow and Context Integration Addendum

**Status:** Incorporated planning detail under [B-16](decisions.md#b-16--operational-addendum-incorporation--2026-09-15); not implementation evidence

**Date:** 14 September 2026; reconciled 15 September 2026

**Purpose:** Define targeted improvements to Living Memory that reduce adjudication friction, improve context quality, preserve human authority, and support an integrated, auditable wargaming workflow.

---

## 1. Intent

Living Memory will serve as the durable operational backbone for turn submission, temporal game state, adjudication review, Requests for Information (RFI), feedback release, replay, and evaluation of AI-assisted preparation methods.

The platform will preserve the following design principles:

1. **Human authority remains decisive in operational games.** AI may identify, summarize, retrieve, compare, and propose; it does not independently determine feasibility, adjudicate outcomes, apply effects, or release player feedback there. Research follows its recorded ruling policy.
2. **Authoritative records remain durable.** Player input, adjudicator decisions, effects, disclosures, review actions, and original AI run artifacts remain preserved independently of any retrieval or model implementation.
3. **Context must be inspectable.** Every proposed issue, relationship, trigger determination, or suggested consequence must identify the records, sources, assumptions, and temporal cutoff used.
4. **Workflow integration is a product requirement.** Users should not need to retype turn-card content into a separate AI or triage tool.
5. **Automation must reduce—not redistribute—human workload.** Features that create redundant links, excessive recommendations, delays, or opaque output do not meet the intended outcome.

This addendum supplements, but does not replace, existing requirement identifiers,
scope boundaries, and architectural decisions. [Requirements](../requirements.md)
and the [roadmap](../roadmap.md#operational-addendum-allocation-and-gates) incorporate
ADD-01–09; their phase order governs delivery. The [evaluation plan](evaluation.md)
remains unchanged and governs measurement and comparison.

Human approval requirements here apply to operational games and release. Research
replay retains B-13's automated default, human-review toggle and recorded policy in
an isolated history; research automation cannot authorize operational effects or release.

---

## 2. Priority Outcomes

Development should prioritize the following operational outcomes:

1. Native, structured, LLM-readable player turn submissions.
2. AI-assisted identification and evaluation of conditional actions, branches, sequels, prerequisites, and trigger conditions.
3. More complete, source-traceable context across turns, teams, actors, and scenario state.
4. Human-centered adjudication review that surfaces uncertainty and preserves adjudicator judgment.
5. Scenario-defined structured state variables, including economic and other non-military indicators where required.
6. Pre-game validation of workflows, prompts, retrieval behavior, and human trust criteria.
7. Measurable reduction in transcription, context assembly, duplicate recommendations, and review time.

---

## 3. New and Revised Requirements

### ADD-01 — Structured Turn-Card Ingest

Living Memory shall provide a native, versioned turn-card format that is directly usable by adjudication and AI-preparation workflows without manual transcription.

Each turn package shall preserve:

- player/team and actor identity;
- turn and scenario context;
- overall intent;
- action title;
- action description;
- Intent of Action (synonymous with intended effect);
- anticipated reaction;
- timing or trigger conditions when supplied;
- targets, resources, dependencies, and supporting material when supplied;
- source attachments and source metadata;
- drafting, revision, submission, and amendment history.

Player entry retains overall intention and the four free-text action fields. No
additional mandatory tags, modifiers, targets, resources or timing fields are
introduced. Optional supplied context is preserved; extraction remains separate.

The canonical original player text shall remain immutable after submission. Derived tags, interpretations, classifications, summaries, and extracted entities shall remain separate from the original submission.

**Acceptance evidence:**

- A submitted turn package is available to authorized adjudicators and AI-preparation workflows without re-entry into another application.
- Reviewers can recover the exact submitted version, including attached supporting material and later amendments.
- Derived interpretations do not overwrite player-authored text.

---

### ADD-02 — Conditional Logic and Trigger Evaluation

Living Memory shall support explicit conditional-action and trigger evaluation.

A conditional trigger may represent, at minimum:

- an “On Action” condition;
- a branch or sequel;
- a prerequisite;
- a dependency on another action, ruling, RFI response, effect, or state variable;
- a temporal condition;
- a condition that is unresolved because information is unavailable or disputed.

Each trigger evaluation shall record:

- the trigger statement;
- linked authoritative and non-authoritative source records;
- applicable temporal cutoff;
- applicable actor visibility or disclosure constraints;
- machine-proposed status: satisfied, not satisfied, uncertain, or not applicable;
- rationale and cited supporting records;
- adjudicator confirmation, modification, or rejection;
- resulting effect, if any.

In operational games, AI may recommend a trigger status but shall not apply the trigger or initiate downstream effects without human approval. Research follows its recorded ruling policy.

Dependency references identify exact source versions. Amendments, RFI answers and
state changes require reassessment of affected evaluations, preserving prior results
and preventing duplicate effect application.

**Acceptance evidence:**

- A reviewer can navigate from a proposed trigger determination to relevant turn cards, prior rulings, RFIs, state records, and source material.
- A conditional action is not treated as active merely because it exists in a player submission.
- Uncertain or incomplete conditions are visibly identified rather than silently assumed true.

---

### ADD-03 — Contextual Retrieval and Review Packets

Living Memory shall provide a framework-neutral retrieval contract capable of supporting keyword, structured, semantic, graph, and future resolver implementations.

For an adjudication request, the retrieval contract shall support authorized retrieval of:

- relevant current and historical submissions;
- prior rulings and established facts;
- unresolved and answered RFIs;
- actor beliefs and approved disclosures;
- linked actions, commitments, effects, and conditional triggers;
- structured scenario-state variables;
- limited approved game/scenario reference material, with source versions and authorization.

Full, robust RAG is beyond this application. Preserve an external resolver seam;
this requirement does not introduce general reference-corpus ingestion.

Every AI-generated review packet shall include:

- source records supplied to the method;
- retrieval rationale or query basis;
- source type and provenance;
- temporal cutoff;
- authorization and visibility constraints applied;
- unsupported assumptions;
- unresolved information needs;
- raw model output and validation status.

**Acceptance evidence:**

- Reviewers can distinguish game record, reference material, and machine-generated assumption.
- Retrieval does not expose unauthorized player, team, or actor information.
- Re-running or replacing a retrieval implementation does not alter preserved historical records or original run artifacts.

---

### ADD-04 — Structured Scenario State

Living Memory shall support scenario-defined structured state variables without requiring a universal domain simulation.

A scenario administrator or authorized white-cell user may define state categories, variables, units, baselines, sources, update authority, visibility, and effective dates. Initial use cases may include:

- economic and financial indicators;
- national or actor-level resources;
- political, informational, or social indicators;
- readiness, resilience, or will-to-act indicators;
- other scenario-specific measures required for adjudication.

Structured state records shall support:

- baseline and subsequent values;
- effective time and recording time;
- source citation or provenance;
- confidence, uncertainty, and dispute status;
- actor visibility and disclosure rules;
- linkage to relevant submissions, rulings, and effects.

Variable definitions and value revisions are separate wrapper-owned records;
canonical values remain distinct from actor beliefs and disclosures. Updates use
authority, concurrency and once-only effect controls.

Structured state is supplemental to free-text adjudication. It shall not force all scenarios into a common simulation model.

**Acceptance evidence:**

- A scenario can define and maintain selected structured variables without code changes.
- Reviewers can identify the baseline, current value, source, update rationale, and effective time of a variable.
- State updates are versioned, attributable, and recoverable.

---

### ADD-05 — Human Feasibility and Intent Safeguards

The adjudication workflow shall explicitly separate:

1. what a player submitted;
2. what the player appears to intend;
3. what is factually or procedurally feasible;
4. what is triggered or applicable;
5. what effects the adjudicator approves.

AI may flag apparent ambiguity, infeasibility, inconsistency, missing context, or competing interpretations. AI shall not treat all submitted actions as feasible, triggered, or adjudicable.

In operational games, the review surface shall require a human decision or applicable human-approved policy for:

- feasibility determinations;
- interpretation of player intent when ambiguous;
- adjudication of conditional actions;
- confirmation of material cross-player links;
- application of effects;
- release of feedback or observations.

**Acceptance evidence:**

- An AI-proposed adjudication cannot become authoritative in an operational game without recorded human approval; research follows its recorded ruling policy.
- Reviewers can record that an action is infeasible, deferred, conditional, incomplete, or requires clarification.
- The system preserves the distinction between player intent, adjudicator interpretation, and final ruling.

---

### ADD-06 — Move Volume and Scope Support

Living Memory shall provide configurable turn-level metrics and advisory guardrails to help facilitators manage excessive action volume and action scope.

The platform may support:

- action counts by player, team, actor, domain, or turn;
- configurable advisory thresholds;
- flags for actions lacking sufficient operational relevance or required context;
- identification of potentially duplicative actions;
- queueing or grouping support for high-volume adjudication.

Counts use existing package metadata; domain or other classifications, when needed,
are supplied optionally or derived separately rather than required from players.

These features are advisory. They shall not automatically reject or modify player submissions unless a scenario-specific policy explicitly requires it.

**Acceptance evidence:**

- Facilitators can view move volume and selected scope indicators before adjudication.
- Advisory flags are clearly distinguished from adjudicator decisions.
- The system does not silently suppress submitted actions.

---

### ADD-07 — Pre-Game Validation and Trust Gate

Before a live game uses AI-assisted adjudication, the responsible team shall conduct and record a pre-game validation exercise.

The validation package shall include representative turn cards and test cases covering:

- normal player submissions;
- cross-player interactions;
- conditional actions and branch/sequel logic;
- incomplete or contradictory information;
- sensitive visibility boundaries;
- structured state updates;
- RFI dependencies;
- expected retrieval sources;
- anticipated failure modes;
- latency and recovery behavior.

The validation record shall document:

- method and model configuration;
- prompts and retrieval configuration;
- known limitations;
- reviewer acceptance criteria;
- fallback workflow if AI processing is unavailable or unsuitable;
- human approval to use the method for the specified game context.

**Acceptance evidence:**

- A live-game method has a retained validation record before activation.
- Known failure modes and fallback procedures are available to adjudicators.
- Approval identifies the game context and exact method/model/prompt/retrieval configuration. Defined material behavioral changes invalidate that approval and trigger revalidation; a changed configuration cannot silently inherit approval.

---

### ADD-08 — Adoption, Friction, and Quality Instrumentation

Living Memory shall measure whether integrated workflow and AI assistance improve adjudication outcomes.

At minimum, the platform shall capture:

- turn-card transcription or re-entry events;
- AI-processing latency and failures;
- time from submission to completed adjudication;
- reviewer time spent per issue or action;
- number of AI-proposed links, accepted links, rejected links, and merged duplicates;
- trigger recommendations and confirmation outcomes;
- missing-context and RFI rates;
- reviewer edits to AI-produced content;
- user bypass of the integrated workflow;
- feedback-release timing;
- method, model, and retrieval configuration.

Metrics shall support comparison across methods, turns, scenarios, and validation
exercises under the existing evaluation plan, without substituting automated metrics
for human assessment. Separate active reviewer time from elapsed/queue time. External
re-entry and bypass require explicit reporting or observation; missing interactions
require independently assessed cases, not merely acceptance logs.

**Acceptance evidence:**

- Project personnel can identify whether AI support reduces or increases adjudication workload.
- Redundant recommendation rates and missed-interaction rates are measurable.
- Metrics preserve links to the applicable method version and review history.

---

### ADD-09 — Knowledge Capture and Observation Records

Living Memory shall support structured capture of observations and significant activities during game execution and adjudication.

An observation record shall support:

- title and narrative;
- source and collection method;
- associated actors, teams, actions, turn, and time;
- visibility and disclosure controls;
- confidence and assessment status;
- links to adjudication issues, state changes and RFIs; Learning Demand integration remains unspecified and is not an initial delivery gate;
- reviewer and approval history.

Collected source evidence, established facts and approved player-facing observations
remain distinct. Manual review/release belongs to 1E; broader capture adapters follow
in Phase 3/4 as use cases establish need.

The platform may accept observation records from manual entry, imported structured data, or approved transcription/capture workflows. Automated capture outputs shall remain unverified until reviewed.

**Acceptance evidence:**

- Authorized users can create, review, link, and release observation records.
- Observation records can be retrieved in adjudication and analysis workflows according to authorization.
- Automated or imported observations are distinguishable from human-confirmed records.

---

## 4. Architectural Direction

### 4.1 Wrapper Responsibilities

The durable Living Memory wrapper shall remain authoritative for:

- users, roles, teams, actors, and scenario configuration;
- player turn cards, drafts, submissions, coordination, imports, and amendments;
- RFIs and answers;
- adjudicator decisions, approved effects, and canonical state;
- actor beliefs, disclosures, and release decisions;
- review actions and human approval history;
- original AI run artifacts and what reviewers saw;
- experiment records, replay records, and measurement data.

### 4.2 Framework Responsibilities

Swappable frameworks may provide:

- retrieval and memory projections;
- AI preparation methods;
- rule or conditional-logic evaluation support;
- issue grouping and relationship proposals;
- structured-output validation;
- analysis projections and reports.

Frameworks shall not become the sole holder of authoritative game history, adjudication decisions, or original review artifacts.

### 4.3 Integration Responsibilities

Living Memory shall define stable, versioned contracts within the modular application
as the owning milestones are delivered; separate services or public APIs are not
required for every record. These contracts cover:

- structured turn-card ingest;
- scenario-state import and update;
- retrieval requests and results;
- RFI lifecycle events;
- observation and significant-activity records;
- adjudication review packets;
- approved rulings and effects;
- analysis and reporting consumers;
- external M&S or specialized workflow tools, where integration is later authorized.

---

## 5. Scope Boundaries

This addendum does not require:

- a universal import format for all wargames;
- a complete economic, political, or military simulation;
- autonomous AI adjudication or automatic AI-proposed effects in operational games; research follows its recorded policy;
- full, robust RAG or unrestricted reference-corpus ingestion; limited relevant game/scenario inclusion is permitted;
- replacement of specialized M&S tools;
- direct integration with external systems before interface contracts and governance are defined.

Military movement and combat remain outside the initial Living Memory adjudication scope. Non-military actions may retain links to military context where necessary for adjudication, provided authorization, visibility, and release controls are preserved.

---

## 6. Delivery themes and roadmap allocation

A/B/C below are thematic groupings, not a replacement delivery sequence. The accepted
order remains 1D-2 → 1E → 1W → Phase 2 → 2M → 1F → 3A → 3B/3C → 4 → 5,
with 1G alongside 1D/1E. See the roadmap's operational allocation for explicit gates.
Native 1D-1 entry is already delivered; its completed verification is unchanged.

### Increment A — Workflow and Data Foundation

1. Apply the accepted wrapper/framework contracts now; complete code separation in 1W after 1E.
2. Deliver native structured turn-card entry and a narrow import contract.
3. Add scenario-defined structured state records.
4. Complete RFI workflow and controlled context injection.
5. Add baseline workflow and friction instrumentation.

### Increment B — Human-Centered Adjudication Support

1. Build the review packet contract.
2. Implement conditional trigger representation and review workflow.
3. Add source-linked retrieval results and uncertainty presentation.
4. Add human feasibility, intent, and approval gates.
5. Conduct representative pre-game validation exercises.

### Increment C — Retrieval, Analysis, and Knowledge Capture

1. Introduce and compare retrieval implementations behind the stable contract.
2. Expand observation/significant-activity capture beyond the reviewed records and release workflow established in 1E.
3. Provide authorized internal analysis/reporting interfaces. External export is required eventually, but scope, contents, mechanism, authorization and delivery phase remain unresolved; current operational results remain internal.
4. Expand replay and counterfactual analysis using preserved run and review artifacts.
5. Use measured operational evidence to select or refine AI and retrieval methods.

---

Future external export is acknowledged by OPS-10, without committing to an export
format, payload, transport or external integration. It does not authorize current
data egress and has no implementation gate until its scope is agreed.

## 7. Definition of Success

This addendum will be considered successfully implemented when an authorized team can:

1. Create and submit turn cards without later transcription into an AI workflow.
2. Review an AI-prepared adjudication packet with visible sources, uncertainty, and temporal context.
3. Evaluate conditional actions against relevant current and historical records.
4. Record and preserve human feasibility, intent, adjudication, and release decisions.
5. Maintain selected structured scenario-state variables with provenance and visibility controls.
6. Continue core player and adjudicator workflow when AI processing is delayed, unavailable, or rejected.
7. Demonstrate through retained measurements that the integrated workflow reduces friction or provides sufficient decision-quality benefit to justify continued use.
