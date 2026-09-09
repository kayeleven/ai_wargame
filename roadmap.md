# Roadmap

Status: proposed delivery sequence, 2026-09-09. Phases are ordered by dependencies rather than calendar estimates. No phase is complete yet.

## Phase 0 — Define executable acceptance cases

Turn the planning baseline into a small fixture scenario and review tasks. Include a three-turn-old commitment, cross-player resource conflict, delayed effect, coordinated action, RFI, hidden information, and imported move.

Decide an initial turn-resolution policy, action schema, team permissions, deployment assumptions, and model interface. Define reviewer tasks and initial usability/performance targets. Record decisions rather than implying that preliminary proposals are settled.

Exit gate: a human can walk through the fixture and identify expected memory retrievals, relationships, visibility, and review decisions. Numerical outcome truth is not required for every action.

Coverage: GAME-01–02, MEM-01–05, EXP-03; resolves initial items in the decision log.

## Phase 1 — Playable human workflow and durable memory

Build a browser-based vertical slice: configure a small game; create users and teams; collaborate on versioned drafts; submit actions; coordinate a linked effect; ask and answer RFIs; review issues; record rulings; apply approved effects; release player feedback.

Provide structured history and source references, adjudicator and player views, basic memory queries, safe concurrent editing, and a first guided offline installation. Exercise backup and restore immediately. Include a simple import path for the fixture's external move.

Exit gate: a small group completes a multi-turn game without manual database edits or routine configuration-file surgery. Hidden facts stay out of player views, prior commitments remain discoverable, and the game survives restoration.

Coverage: GAME-01–02/04, PLAY-01–05, ADJ-02–04, MEM-01–05, RFI-01–04, OPS-01–03/06–07/09.

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
