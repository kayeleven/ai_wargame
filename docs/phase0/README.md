# Phase 0 acceptance package

Status: **complete**, 2026-09-09. The project owner accepted the AI substitute walkthrough as sufficient for the Phase 0 exit gate under [B-05](../decisions.md#b-05--ai-substitute-walkthrough-accepted-for-phase-0). Fixtures and static examples exist; no application or automated acceptance runner exists.

## Start here

1. Read [contracts and policies](contracts.md).
2. Give the reviewer [the walkthrough](walkthrough.md) and the appropriate [fixture view](../../fixtures/phase0/views/). Keep the answer key out of the first attempt.
3. Compare the completed work against [acceptance cases](acceptance.md), then record observations in [findings](findings.md).

The fictional Harbor Relief scenario uses two civilian councils, Estuary and Upland. The four simulated turns last seven days each; wall-clock submission deadlines are separately recorded. Two members per team and one adjudicator illustrate collaboration and authority. Each team represents one submitting player in this fixture; user, team, actor, and player identity are not generally interchangeable.

Military movement, combat, M&S submissions, M&S adjudication, and military integration are excluded. Intelligence and law-enforcement actions here concern civilian trade information and invoices. No automatic domain classifier or military-content filter is specified.

## Artifacts and checkpoints

| Artifact | Purpose |
| --- | --- |
| [source.json](../../fixtures/phase0/source.json) | Full source timeline, including hidden information and later events; adjudicator/fixture-author material. |
| [views/](../../fixtures/phase0/views/) | Nine standalone snapshots: adjudicator, Estuary, and Upland at each of three cutoffs. |
| [imported-move.txt](../../fixtures/phase0/imported-move.txt) | Preserved synthetic external action. |
| [variant.json](../../fixtures/phase0/variant.json) | More funding and shorter simulated turns, applied only to the pre-ruling exercise. |
| [model-examples.json](../../fixtures/phase0/model-examples.json) | Static provider-neutral preparation and failure examples, not actual model results. |

`t3` is Turn 3 at 23:00 UTC; `review` is Turn 4 at 14:00, before the amendment and rulings; `release` is Turn 4 at 20:00, after the RFI answer and feedback release. Dates are fictional 2030 timestamps. Future-effective records known at a cutoff, such as a scheduled effect, are retrievable but must not be described as already active.

View files contain source records, not expected judgments. Private source links are omitted from player snapshots; the full timeline retains provenance. Never distribute the full repository, source timeline, answer key, or adjudicator snapshot as a player information package. The files demonstrate expected access boundaries; they do not implement authorization.

Later rulings are one illustrative continuation, not the unique correct solution to the initial review. Do not supply them as input to an earlier-turn preparation experiment. The funding amendment is accepted at 15:00; it changes the 12-credit demand to 10 before the recorded 16:00 allocation.

## Completion and handoff

C01–C13 were reported met in the [AI substitute walkthrough](findings.md), with no mandatory omissions or unauthorized disclosures. The project owner accepted this pass for Phase 0 completion. Preliminary human review was of limited use because difficulty reading JSON confounded interpretation errors with the intended review task. A further human run is not required to close Phase 0; human usability and effort still need evaluation through a readable interface in later phases. Recorded ambiguities remain handoff items.

The configuration variant tests that two original six-credit requests fit within fourteen credits and that simulated turn duration does not change wall-clock deadlines. It is partial evidence toward GAME-01, not proof that two materially different scenarios run in an application.

Phase 1 should translate these cases into application acceptance tests. No language, framework, database, queue, event-sourcing framework, or model provider is selected by the JSON format.
