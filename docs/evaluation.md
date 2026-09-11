# Evaluation plan

Status: research direction revised 2026-09-11 under B-13/B-14. Protocol details and
numerical success thresholds remain to be established; no new evaluation results
are claimed by this update.

## Research objective

Determine which AI pre-adjudication methods give humans the best starting point for adjudication: less searching and reading, fewer forgotten commitments and missed interactions, clearer decisions, and better player feedback. A persuasive model explanation or initial agreement with a past ruling is not sufficient evidence of usefulness.

Secondary questions concern storage and retrieval, temporal/action linking, state-view generation, RFI integration, and the effects of adding AI participants.

Compare frameworks through their review packets, god views and per-actor fog-of-war
views. Mock scenarios establish behavior on tested cases and narrow candidates;
selection requires operational-environment evidence from real game complexity.
Use one framework per live game and reprocess saved moves with alternatives.

## Hypotheses and methods

| ID | Hypothesis / comparison |
| --- | --- |
| H1 | A lookup-planning pass followed by evidence-enriched review is more useful than a single pass over submissions and a standard memory package. |
| H2 | Batch review followed by cross-batch reconciliation reduces overload and omissions compared with single-pass review. |
| H3 | Combining targeted lookups and reconciled batching improves usefulness enough to justify added latency and complexity. |
| H4 | Structured living memory improves recovery of prior commitments compared with narrative-summary retrieval alone. |
| H5 | Explicit relationships improve interaction discovery; separately, graph storage may improve retrieval performance or maintainability relative to simpler storage. |
| H6 | Evidence-linked draft feedback reduces human revision effort while preserving player-specific knowledge boundaries. |

These are hypotheses, not established findings.

Initial preparation methods:

- Single pass: current submissions and a standard authorized memory package.
- Lookup then review: generate explicit information needs, retrieve evidence, then prepare issues.
- Batch then reconcile: prepare issues per batch, then examine interactions across batches.
- Combined: targeted retrieval for batch reviews followed by reconciliation.

Compare batching by player, geography, domain, objective, and linked action group as distinct variants. Keep an all-action index available for reconciliation and measure links lost at batch boundaries. Later experiments may compare probability-based proposals, independent adjudicators with reconciliation, and rule/AI hybrids, but human review support remains the primary objective.

## Phase 0 baseline

The [acceptance package](phase0/README.md) supplies the initial non-military case, role/time snapshots, source-linked expected results, and [reviewer protocol](phase0/walkthrough.md). The project owner accepted an AI substitute walkthrough for Phase 0 completion under [B-05](decisions.md#b-05--ai-substitute-walkthrough-accepted-for-phase-0). Preliminary human review was confounded by difficulty reading JSON and supplies no usable human baseline. Later human evaluation should use a readable presentation and record actual effort and substantive corrections before setting comparative improvement thresholds; AI-estimated timings and static model examples are not human research results. Free-text turn intentions and anticipated reactions must remain distinguishable from adjudicated outcomes.

## Cases and controls

Start with constructed fixtures containing known relevant facts and links. Include a three-turn-old commitment, resource conflict between two players, delayed effect, cancellation, coordinated action, contradictory claim, unanswered RFI, late answer, hidden observation, and irrelevant distractor actions. Add larger volumes to expose overwhelm.

Use real or imported game records later, retaining original assumptions, omissions, and provenance. Historical rulings are reference judgments, not unquestionable ground truth. Human annotations should allow multiple defensible outcomes and record disagreements.

For frozen-context comparisons, freeze the case's source records, temporal cutoff,
permissions and human task. For trajectory comparisons, frameworks carry forward
state through recorded moves in isolated wrapper-owned replay histories. Record
divergence, effort per turn/volume and reviewer controls; normalization alone does
not remove differences in world difficulty. Report the modes separately: controlled
method effects and downstream usefulness answer related but different questions.
Record model version/settings, versioned method definitions, prompts, context,
retrieval policy, measurable budgets, original outputs, errors and elapsed time.

Use repetitions to measure model variability. Counterbalance method order or assign equivalent cases to reduce reviewer learning effects. Blind method labels where feasible. Do not evaluate an earlier turn using later facts, reference rulings inadvertently supplied to the model, or knowledge unavailable to the selected viewer.

Research replay defaults to automated mode with a human-review toggle (N-01).
Retain incompatible moves as attempted by default (N-05), adjudicating feasibility
in the replay. Record policy changes/overrides and applicability of original RFIs,
disclosures and rulings. Recorded-ruling reuse is an explicit alternative. Automated
acceptance is not human review and supplies no human-effort measurement; use replay
review sessions for that evidence. Operational games retain human approval.

Phase 2M adds an open-world non-military mock with contradicted world premises,
false capability claims, precedent contradictions, unrepresented actors, an RFI
establishing a fact and 100+ actions over several turns. Check premise adherence,
claim/fact distinctions, commitments/precedent, actor-lens fidelity, prose leakage
with clean citations, duplicate effects and failure behavior. The lens selects an
actor only in the current game/replay context and never restricts white-cell god view.
Screen local models for premise adherence and engagement with required scenario content.

Two or more surviving candidates proceed to operational comparison; one proceeds
to validation without a comparative-selection claim; none means repair/replacement
and retesting. Later candidates, including Phase 3C variants, pass these gates before
operational comparison. Harbor Relief and Orchid Accord retain their historical
permissions/temporal-oracle role; their accepted evidence is not open-world validation.

## Measures

| Dimension | Proposed evidence |
| --- | --- |
| Human effort | Active review time, evidence-search time, navigation burden, and perceived workload. |
| Memory recovery | Relevant prior commitments recovered, missed, or given incorrect status. |
| Interaction discovery | Supported links found, missed interactions, and false/irrelevant links flagged. |
| Review packet usefulness | Material edits, missing evidence, unresolved assumptions, and issue regrouping required. |
| Decision quality | Human assessment of defensibility, premise and precedent adherence, claim/belief distinctions, temporal coherence, and resource consistency where applicable. |
| Feedback quality | Corrections, missing meaningful effects, unsupported claims, and usefulness to players. |
| Information discipline | Unauthorized disclosures and incorrectly withheld permitted information. |
| Practical operation | End-to-end time, queue wait, model calls, resource use, and failure/recovery rate. |

Count edit burden by significance, not just character count. Faster review is not a success if important omissions increase. Acceptance without edits can reflect automation bias; independently audit a sample of reviewed results.

Capture time on task, evidence navigation, substantive edits, triage/regrouping and
accept/reject decisions in the 1E surface. Preserve original proposals and exactly
what reviewers saw alongside their changes; regenerated output cannot replace this
evidence. Historical human rulings are reference labels, not infallible truth.

Where probability estimates and adequate reference outcomes exist, calibration can be examined as a secondary measure. Keep model disagreement separate from the modeled randomness of world outcomes.

## Storage and retrieval experiments

Use identical source records, temporal boundaries, permissions and query tasks for
controlled backend comparisons; label trajectory-based comparisons separately.
Measure supported-link retrieval, missing/irrelevant context, latency, update
consistency, rebuild effort and operational complexity. Separate relationship-model
benefits from database benefits. Phase 2 exercises two methods and two backends;
operational Phase 3 evidence determines the selected approach, not mock scores.

Test memory updates after corrections, delayed effects, RFI answers, and branch divergence. Summaries and projections must not silently retain superseded facts as current or expose future knowledge.

## Operational validation

Phase 1F follows 2M and retains its integrated game/restore gate without database
edits, discoverable commitments and zero unauthorized disclosure. Its “Local
eight-user sanity check” is not 150-user capacity evidence. Phase 3A exercises
offline research install/update/recovery before operational comparisons; all
analysis, reporting and diagnostics stay inside that environment because results
cannot be exported. The workload below is the separate Phase 5 qualification.

Construct a 150-user workload with multiple users per team, shared drafts, discussions, RFIs, player queries, adjudicator review, submission bursts, and feedback release. Agree workload proportions and latency thresholds before declaring capacity supported.

Test inference saturation independently from application load. Include service restarts, duplicate job delivery, stale AI outputs, simultaneous edits, disconnected clients, offline installation, upgrade, and restore. Verify workflows from the target VDI browser environment.

## Experiment record and report

Each report should identify the question, case set, method versions, controlled variables, reviewer protocol, measured outcomes, uncertainty, failure examples, and limitations. Preserve enough artifacts to inspect a result even when a model cannot reproduce it exactly.

Include framework/backend and rebuild versions, comparison mode, ruling policy,
incompatible-move policy, applicability rules and reviewer-order controls. Preserve
all run artifacts and review history in the wrapper, including each replay's own
history. Framework replacement must not erase evidence or alter the original game.

Choose the next implementation based on observed human benefit and operating constraints; do not assume the most elaborate pipeline wins. Early pilot findings should guide product refinement, not be presented as general conclusions from an inadequate sample.
