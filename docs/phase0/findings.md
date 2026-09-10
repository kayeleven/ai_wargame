# Walkthrough findings and readiness

Status: Phase 0 **complete**. The project owner accepted the AI substitute walkthrough on 2026-09-09; see [B-05](../decisions.md#b-05--ai-substitute-walkthrough-accepted-for-phase-0).
An AI-assisted walkthrough of the full 8-task script was completed 2026-09-09; see "AI-assisted walkthrough" below.

## Preparation findings

- Player-authored actions use the supplied four free-text fields, with overall intention stored once per turn submission. Resource and timing interpretations are review material.
- The fixture's late disclosure requires both recording and audience-availability cutoffs; effective time alone cannot reconstruct knowledge.
- A current-state view must resolve supersession: retaining a scheduled guarantee without its cancellation would produce an invalid activation.
- Cross-team coordination cannot expose private linked submissions. Player snapshot source links are filtered accordingly.
- The configuration variant stops before the illustrative rulings because copying the base remaining-fund effect would be inconsistent with the changed initial balance.

These are authoring/inspection findings, not observations of human performance.

## Static inspection — 2026-09-09

One-off consistency checks passed for 31 unique source records and nine role/time snapshots. Checks covered JSON parsing, exact submission field names, reference resolution, disclosure/recording cutoffs, exclusion of private references from player snapshots, verbatim import mapping, funding totals, cancellation/activation supersession, authorized evidence in the static model example, and local Markdown links. `git diff --check` passed. No validator was added to the repository.

These checks establish artifact consistency only; they do not verify application authorization, concurrency, model behavior, usability, or performance.

## AI-assisted walkthrough — 2026-09-09

An AI reviewer executed Tasks 1–8 of the walkthrough script in a single session, in the adjudicator role, receiving snapshots one at a time and without facilitator explanation. First-attempt answers were preserved before the answer key was opened.


### Scope limits specific to this run

- One reviewer, one pass, no counterbalancing, no order variation, no model-variability measurement.
- Blinding was a property of the session, not of an independent reviewer's memory. Tasks 1–6 were genuinely cold — no prior fixture exposure in context — but this is a weaker guarantee than a human who has never seen the key.
- Timings are the reviewer's estimates of equivalent analyst effort, not stopwatch readings. They are **not comparable to human timings** and must not be used as a human baseline.
- Per C13 and the coverage limits: nothing here tests a real model adapter, executes concurrent writes, or speaks to 150-user capacity, replay branching, M&S integration, or comparative AI usefulness. Not to be portrayed as a comparative study.

### Results

| Field | Value |
| --- | --- |
| Date / reviewer | 2026-09-09 / AI reviewer, adjudicator role, no facilitator explanation |
| Tasks executed | 1–8, in order, snapshots supplied one at a time |
| First-attempt answers | Preserved in session transcript, unedited before key release |
| Active review / search minutes | 250 est. / 87 est. (35% search) |
| Mandatory omissions | 0 |
| Unsupported flags | 2 (both cautionary, neither affected a packet) |
| Significant corrections | 0 |
| Facilitator assistance requests | 0 |
| Clarification requests filed | 5 |
| Unauthorized disclosures | 0 |
| Incorrectly withheld facts | 0 (one over-caution noted, permissible under C05) |
| Case results C01–C13 | All met |
| Required revisions / reruns | None |
| Outcome against script criteria | Pass — fixture clarity only |

Per-task effort:

| Task | Active (min) | Search (min) | Records |
| --- | --- | --- | --- |
| 1 — T3 forward-bearing state | 22 | 8 | 17 |
| 2 — Turn 4 review | 48 | 16 | 22 |
| 3a — Estuary snapshot | 26 | 11 | 15 |
| 3b — Upland snapshot | 24 | 10 | 15 |
| 4 — Release delta | 34 | 13 | 30 |
| 5a — Estuary feedback | 28 | 9 | 21 |
| 5b — Upland feedback | 26 | 8 | 17 |
| 6 — Variant | 19 | 5 | 9 |
| 7 — Model examples | 23 | 7 | 10 |
| **Total** | **250** | **87** | — |

Task 2 was the single heaviest task at roughly a fifth of total effort, and Task 4 carried the highest record count. If Phase 2 needs to shorten the protocol, those two are where the cost sits.

### Access-boundary performance

All checks satisfied, zero unauthorized disclosures. The Estuary review answer excluded `upland-t4-v1`, `import-invoices`, `review-invoices`, `observation-permits`. The Upland review answer excluded `estuary-t4-v1`, `rfi-permits`, `review-invoices`, `observation-permits`. The Upland release answer additionally excluded the RFI answer, Estuary's revisions, and Estuary's feedback. Task 1 used no Turn 4 record.

The reviewer independently derived the key's traversal rule — that public rulings and commitments do not license reaching their private source submissions — by inspecting which `source_refs` chains had been deliberately emptied in each player snapshot, before the key was opened.

### Ambiguities found, in priority order

1. **`commitment-1` visibility asymmetry — resolve before Phase 2.** Upland sees Estuary's funding intent; Estuary sees no equivalent. Combined with the six-credit clinic approval in `feedback-upland`, this creates an inference channel toward Estuary's reduced allocation. The key's access checks do not address it. Unclear whether it is designed information advantage or incidental. This affects what "no unauthorized disclosure" means operationally and should be settled explicitly in the access checks.
2. **No announcement ruling exists** in `release-adjudicator.json`, and neither released feedback mentions the announcement. Consistent with C05, which says a joint announcement is not yet an approved outcome — but a reviewer cannot distinguish "deliberately left pending" from "snapshot cut before the ruling." Decide and state in the facilitator notes.
3. **`variant.json` states its own answer.** `expected_differences` gives the funding result outright, so C12 tests application rather than derivation. Fine for fixture clarity; a limitation if Phase 2 wants to measure whether a reviewer *finds* the non-competition result. Consider removing.
4. **`commitment-1` is stale at the release cutoff** — still reads "six credits", `status: active`, after `ruling-fund` allocates four. C09 does not require closing or annotating it.
5. **Filenames not supplied.** `variant.json` cites `base_fixture: "source.json"`; `model-examples.json` cites `authorized_context_artifact: "views/review-adjudicator.json"`, a path prefix used nowhere else. Neither blocked this reviewer; a reviewer working strictly from named artifacts would stop.
6. **`rfi-permits` typing is a deliberate snare.** Typed `retrieval_of_known_information`, which pulls toward answering it as a lookup when the only responsive material is confidential. Recommend keeping it and documenting it as a known snare in facilitator notes rather than treating it as a defect.

### Divergences from the fixture's recorded path

Two, both within the latitude the key allows for defensible rulings. Recorded because they indicate where the fixture admits genuine judgment:

- **Funding.** The reviewer proposed 6/4 favouring clinics at the review checkpoint; the recorded path reached 4/6 via Estuary's voluntary amendment. Both fit C03.
- **RFI.** The reviewer proposed answering without disclosing the inspection; the recorded path disclosed under express authorization via `rfi-permits-answer`. Both fit C06–C07.

### Coverage gap against the static model example

`model-examples.json` surfaces two issues (fund contention, invoice specificity). The human-equivalent review surfaced those plus the RFI access boundary, the announcement gate, and the `e-festival` irrelevance marking. The access boundary is the highest-consequence of the three omissions. The example does not claim exhaustiveness, so this is an observation about proposal coverage, not a defect.

## Preliminary human review and completion decision — 2026-09-09

The project owner reported that preliminary human review was of limited use: JSON presentation was difficult to digest, conflating mistakes in reading the data with the intended assessment of retrieval, relationships, visibility, and review decisions. No usable human effort or performance baseline is established by that review.

The owner used an AI as a human substitute and explicitly accepted its pass as sufficient to mark Phase 0 complete. The recorded run reports all C01–C13 met, zero mandatory omissions, and zero unauthorized disclosures. No additional human walkthrough is required for this exit gate. This acceptance does not establish human usability or comparative AI usefulness; later human evaluation should use a readable presentation.

## Handoff dependencies

Fixture and contract decisions resolve the initial O-01–03 baseline; real-game refinements remain possible. O-07 has a synthetic import mapping only; select an actual source format before a production adapter. O-08 has a first reviewer protocol; comparative benefit thresholds require baseline observations. O-10 has a provisional eight-user latency target only; workload mix and recovery/queue targets remain open. O-04–06 and O-11 require deployment evidence at their recorded milestones. O-09 remains a later replay decision.

Additionally, arising from the AI-assisted walkthrough: ambiguity 1 (the `commitment-1` inference channel) should be resolved in the access checks, and ambiguity 2 (the missing announcement ruling) decided and documented, as follow-up work before a future human evaluation. These handoff items do not block the accepted Phase 0 completion.
