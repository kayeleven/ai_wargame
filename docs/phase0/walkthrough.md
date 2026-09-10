# Human reviewer walkthrough

Status: completed by an AI substitute on 2026-09-09 and accepted by the project owner for Phase 0 completion under [B-05](../decisions.md#b-05--ai-substitute-walkthrough-accepted-for-phase-0). The protocol below is retained for future reviews. Preliminary human review was confounded by JSON readability; it does not establish a usable human baseline.

Use a reviewer familiar with adjudication but not the fixture's expected answers. A facilitator supplies only the specified snapshots, this script, and the contracts. Do not open the answer key, full source timeline, model examples, or later snapshots before instructed. Role switches test boundaries, not independent blinded user behavior; prior knowledge from the god-view must never be copied into a player answer without a player-visible source.

For each task record active review minutes, evidence-search minutes (a subset of review time), record IDs consulted, proposed decision or clarification, confidence/uncertainty, and any assistance needed. Pause timing for interruptions. The facilitator can record clarification requests but should not explain the answer during the first attempt.

1. Open `t3-adjudicator.json`. Explain which commitments and effects could matter next turn, their current status, and which outcomes have not happened.
2. Open `review-adjudicator.json`. Summarize each player's overall intention. Group interacting actions, cite evidence, identify missing information, and propose defensible decisions. Mark irrelevant actions separately. Inspect the external move and its provenance. Do not assume anticipated reactions occurred.
3. Open `review-estuary.json` and `review-upland.json` separately. For each player, answer: What have we submitted? What have we jointly committed to? What do we know about permits? Cite only that snapshot. Note whether each shared link can safely expose its source.
4. Open `release-adjudicator.json`. Explain changes since initial review: submission versions, funding, the RFI, and effect status. Identify which earlier preparation is stale and which historical rulings remain intact.
5. Open the two player release snapshots separately. Draft a short feedback message for each council from its authorized evidence. Distinguish approved effects, unresolved questions, and anticipated reactions.
6. Read `variant.json` and reconsider the original review funding issue and turn timing under its overrides. Do not use the base continuation for this variant.
7. After submitting the first-attempt answers, inspect `model-examples.json`. Explain what a human can do for each failure example and why no proposed effect applies automatically.
8. Facilitator and reviewer compare results to C01–C13 in the answer key. Record missed facts/links, unsupported flags, significant corrections, unauthorized disclosures, incorrectly withheld information, and ambiguities in the materials. Preserve first-attempt answers before corrections.

Pass requires every mandatory fact/interaction and access boundary in the answer key to be identified without author explanations, and zero unauthorized disclosures. Multiple defensible rulings are allowed. Missing mandatory evidence or needing an author explanation requires revision and a repeat of affected tasks, preferably with a fresh reviewer. A single walkthrough establishes fixture clarity only, not general usability or AI efficacy.

Collect effort and correction counts as a baseline; no percentage improvement is required yet. Phase 2 comparisons will freeze tasks and inputs, counterbalance order, and separately evaluate model variability. Do not portray this walkthrough as a comparative study.
