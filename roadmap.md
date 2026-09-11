# Roadmap

Status: Phase 0 complete; Phase 1A/1B/1C-core/1C-admin implemented with bounded Phase 1C corrections. The earlier Docker gate passed; correction evidence and explicit deferrals are maintained in [1C correction verification](docs/phase1/corrections-1c.md). Player workspace and adjudication remain 1D/1E work.

## Phase 0 — Define executable acceptance cases

The [Phase 0 package](docs/phase0/README.md) now specifies the non-military scenario, free-text turn/action contract, review policies, source fixtures, and acceptance oracle. “Executable” at this stage means a scripted walkthrough; automated acceptance tests follow in Phase 1. Phase 0 is complete as of 2026-09-09: the project owner accepted the AI substitute walkthrough under [B-05](docs/decisions.md#b-05--ai-substitute-walkthrough-accepted-for-phase-0). Military movements/combat and M&S integration are excluded from this build.

Turn the planning baseline into a small fixture scenario and review tasks. Include a three-turn-old commitment, cross-player resource conflict, delayed effect, coordinated action, RFI, hidden information, and imported move.

Decide an initial turn-resolution policy, action schema, team permissions, deployment assumptions, and model interface. Define reviewer tasks and initial usability/performance targets. Record decisions rather than implying that preliminary proposals are settled.

Exit gate: identify expected memory retrievals, relationships, visibility, and review decisions in the fixture walkthrough. Passed by the AI substitute and accepted by the project owner under B-05, superseding the original human-run requirement. Numerical outcome truth is not required for every action.

Coverage: GAME-01–02, MEM-01–05, EXP-03; resolves initial items in the decision log.

## Phase 1 — Playable human workflow and durable memory

Use host Python 3.12, FastAPI, Pydantic, synchronous SQLAlchemy/Psycopg,
Alembic, Docker-hosted PostgreSQL 16, Jinja, and local HTMX. Preserve the Phase 0
free-text turn intention and variable four-field action list.

| Milestone | Deliverable | Acceptance gate |
| --- | --- | --- |
| **1A — Application foundation** | Setup, shell, shared forms, clocks, migrations, staging seed, bounded resources, diagnostics and tests. | Fresh-checkout setup, migration/repeat seed, failure recovery, forms and browser checks. See [verification](docs/phase1/verification.md). |
| **1B — Thin retrieval slice and readable explorer** | PostgreSQL authorized read path, temporary full-timeline loader, read-only task views and components. | All nine audience/cutoff oracles from shared source records; typed read models and authorized direct/evidence navigation. |
| **1C-core — Temporal memory and authorization** | Temporal revisions, supersession, typed relationships, root-branch scoping, search/traversal and indexes. | Cross-team/game/branch isolation, disclosure-time, correction and reconstruction; unchanged 1B presentation tests. |
| **1C-admin — Identity and game administration** | Local identities, roles, teams, scenario configuration, external identity seam, backup/restore. | Two materially different scenarios; deactivation preserves authorship; restored state and access rules match. |
| **1D — Player workspace** | Shared drafts, comments, ownership, immutable submissions/amendments, consent, RFIs and move import. | Recoverable edit conflicts; submission authority; intact import/omissions; no private submission leakage through coordination. |
| **1E — Adjudication and feedback** | Manual issues/evidence/relationships, split/merge, RFI responses, rulings, effects and separate feedback release. | Stale reviews detected; atomic once-only effects; historical late-answer preservation; release boundaries. |
| **1F — Integrated game and recovery validation** | Multi-turn browser exercise, concurrency, restore drill, requirement mapping and local performance report. | Small group completes/restores game without DB edits; prior commitments discoverable; zero unauthorized disclosure. |

Deliver in order **1A → 1B → 1C-core → 1C-admin → 1D → 1E → 1F**.
[Architectural contracts](docs/phase1/contracts.md) fix the retrieval/presentation,
temporal, identity, concurrency and authority boundaries before subsequent planning.
1A seed only stages original artifacts; it does not create a playable game.
1B implements retrieval before establishing presentation components.

Phase 1 targets developer machines. Offline installation, organizational identity
integration, TLS, VDI qualification and full-scale capacity are follow-up deployment
obligations, not Phase 1 completion claims. Backup/restore tooling begins in
1C-admin and is exercised end to end in 1F.

The 1F report is **“Local eight-user sanity check.”** Report host, workload,
concurrency, durations, errors, pool waits and percentiles; assess the provisional
p95 two-second target only for that run. It provides **no 150-user capacity evidence**.
OPS-04 qualification requires a representative later deployment and deadline bursts.
Map applicable C01–C12 to application evidence; real model adapters remain Phase 2.

Coverage: GAME-01–02/04, PLAY-01–05, ADJ-02–04, MEM-01–05, RFI-01–04,
OPS-02–03/06–07/09 initially; OPS-01 offline provisioning is deferred qualification.

## Phase 2 — AI preparation and initial research loop

Add a local model adapter, background jobs, evidence-linked review packets, and captured human refinements. Implement single-pass and lookup-then-review methods first. Add AI participant control and an explicitly configured automated research mode.

Record full run inputs and outputs. Support preparation replay and an initial branch at a turn boundary. Run the same fixture through both methods with human review.

Exit gate: reviewers can compare the methods, trace and edit suggestions, and continue working during model failure. Mixed human/AI and AI-v-AI test games execute. A historical preparation run can be inspected without future-information leakage.

Coverage: GAME-03/05, ADJ-01–03, EXP-01–04 (initial methods), REP-01–02/04 (initial scope), OPS-05/08.

## Phase 3 — Relationship, retrieval, and batching experiments

Implement batch-then-reconcile and combined preparation. Compare batch boundaries and targeted lookups. Evaluate graph-backed relationships against a simpler storage/retrieval baseline using identical source records and cases.

Expand cross-turn effects, issue grouping, RFI dependencies, and workload metrics. Improve quick-reference interfaces based on reviewer behavior and corrections.

Exit gate: an evidence-backed report compares preparation usefulness, missed interactions, irrelevant context, reviewer effort, and operating cost. The storage choice is justified by observed needs rather than assumed graph advantages.

Coverage: MEM-02–06, EXP-01–04, ADJ-01–02, RFI-03.

## Phase 4 — Counterfactual replay and broader participation

Extend replay to alternate rulings, modified action sets, and added AI actors. Identify affected later actions and apply an explicit retain/revise/regenerate policy. Expand import adapters based on actual source games.

Exit gate: a historical game can branch, diverge, and continue coherently while preserving its original record. Reviewers can explain differences in actions, effects, knowledge, and controller participation.

Coverage: GAME-04–05, REP-01–04, MEM-05, EXP-02.

## Phase 5 — Full-game deployment readiness

Validate 150 simultaneous users under a representative mix of collaboration, submissions, RFIs, queries, review, and turn-feedback release. Measure application responsiveness separately from inference queue performance.

Complete the administrator experience for configuration, local identity integration as selected, diagnostics, certificates, offline upgrades, migration recovery, and deployment sizing. Test the target Windows VDI browser environment.

Exit gate: clean offline install/update/restore drills pass; concurrency and visibility tests pass; agreed capacity and recovery targets are met; an operator can run the system from the deployment guide.

Coverage: OPS-01–09 and full-scale PLAY-02–04.

## Delivery principles

- Keep offline operation, permissions, provenance, and installation in every increment; phase 5 validates scale rather than introducing these concerns.
- Prefer an end-to-end playable slice before broad domain modeling or interface embellishment.
- Maintain a requirement-to-verification record as implementation lands.
- Use pilot feedback to revise later phases and record scope changes explicitly.
- Do not interpret AI inference throughput as equivalent to interactive user capacity.
