# Evaluation plan

Status: proposed research protocol, 2026-09-09.

## Research objective

Determine which AI pre-adjudication methods give humans the best starting point for adjudication: less searching and reading, fewer forgotten commitments and missed interactions, clearer decisions, and better player feedback. A persuasive model explanation or initial agreement with a past ruling is not sufficient evidence of usefulness.

Secondary questions concern storage and retrieval, temporal/action linking, state-view generation, RFI integration, and the effects of adding AI participants.

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

The [acceptance package](phase0/README.md) supplies the initial non-military case, role/time snapshots, source-linked expected results, and [reviewer protocol](phase0/walkthrough.md). Human execution is pending. Record effort and substantive corrections before setting comparative improvement thresholds; the static model examples are not research results. Free-text turn intentions and anticipated reactions must remain distinguishable from adjudicated outcomes.

## Cases and controls

Start with constructed fixtures containing known relevant facts and links. Include a three-turn-old commitment, resource conflict between two players, delayed effect, cancellation, coordinated action, contradictory claim, unanswered RFI, late answer, hidden observation, and irrelevant distractor actions. Add larger volumes to expose overwhelm.

Use real or imported game records later, retaining original assumptions, omissions, and provenance. Historical rulings are reference judgments, not unquestionable ground truth. Human annotations should allow multiple defensible outcomes and record disagreements.

For each comparison, freeze the case's source records, temporal cutoff, permissions, and human task. Record model version, settings, prompts, context, retrieval policy, token/resource budget where available, raw responses, structured output, errors, and elapsed time. Compare both controlled budgets and operational end-to-end costs when practical.

Use repetitions to measure model variability. Counterbalance method order or assign equivalent cases to reduce reviewer learning effects. Blind method labels where feasible. Do not evaluate an earlier turn using later facts, reference rulings inadvertently supplied to the model, or knowledge unavailable to the selected viewer.

## Measures

| Dimension | Proposed evidence |
| --- | --- |
| Human effort | Active review time, evidence-search time, navigation burden, and perceived workload. |
| Memory recovery | Relevant prior commitments recovered, missed, or given incorrect status. |
| Interaction discovery | Supported links found, missed interactions, and false/irrelevant links flagged. |
| Review packet usefulness | Material edits, missing evidence, unresolved assumptions, and issue regrouping required. |
| Decision quality | Human assessment of defensibility, rule compliance, temporal coherence, and resource consistency. |
| Feedback quality | Corrections, missing meaningful effects, unsupported claims, and usefulness to players. |
| Information discipline | Unauthorized disclosures and incorrectly withheld permitted information. |
| Practical operation | End-to-end time, queue wait, model calls, resource use, and failure/recovery rate. |

Count edit burden by significance, not just character count. Faster review is not a success if important omissions increase. Acceptance without edits can reflect automation bias; independently audit a sample of reviewed results.

Where probability estimates and adequate reference outcomes exist, calibration can be examined as a secondary measure. Keep model disagreement separate from the modeled randomness of world outcomes.

## Storage and retrieval experiments

Use identical source records, temporal boundaries, permissions, and query tasks when comparing implementations. Measure supported-link retrieval, missing/irrelevant context, latency, update consistency, rebuild effort, and operational complexity. Separate the benefit of relationship modeling from the benefit of a particular database.

Test memory updates after corrections, delayed effects, RFI answers, and branch divergence. Summaries and projections must not silently retain superseded facts as current or expose future knowledge.

## Operational validation

Construct a 150-user workload with multiple users per team, shared drafts, discussions, RFIs, player queries, adjudicator review, submission bursts, and feedback release. Agree workload proportions and latency thresholds before declaring capacity supported.

Test inference saturation independently from application load. Include service restarts, duplicate job delivery, stale AI outputs, simultaneous edits, disconnected clients, offline installation, upgrade, and restore. Verify workflows from the target VDI browser environment.

## Experiment record and report

Each report should identify the question, case set, method versions, controlled variables, reviewer protocol, measured outcomes, uncertainty, failure examples, and limitations. Preserve enough artifacts to inspect a result even when a model cannot reproduce it exactly.

Choose the next implementation based on observed human benefit and operating constraints; do not assume the most elaborate pipeline wins. Early pilot findings should guide product refinement, not be presented as general conclusions from an inadequate sample.
