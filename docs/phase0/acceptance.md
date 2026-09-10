# Acceptance cases and requirement coverage

Status for C01–C13: **met in the recorded AI substitute walkthrough; accepted for Phase 0 completion on 2026-09-09** (see [findings](findings.md) and [B-05](../decisions.md#b-05--ai-substitute-walkthrough-accepted-for-phase-0)). Application verification remains future work. This is the answer key. Keep it outside preparation input and the reviewer's first attempt.

All cases use game `harbor-relief`, branch `main`. `review`, `t3`, and `release` refer to the exact cutoffs in the view files. Record IDs below are evidence, not an exhaustive input list. Outcome judgments can vary; mandatory evidence and information boundaries cannot.

| Case / requirements | Viewer and task | Mandatory evidence and expected result |
| --- | --- | --- |
| C01 — GAME-01–02, PLAY-01/05 | Adjudicator, review: inspect turn intentions and action structure. | `scenario-v1`, `estuary-t4-v1`, `upland-t4-v1`: intentions contextualize each player's actions; the four authored fields remain free text. `upland-t1-v1` has a valid intention-only submission. No invented structured requirements or automatic effects. |
| C02 — MEM-01–02/05 | Adjudicator, review: recover the three-turn-old bridge commitment. | `commitment-1`, `estuary-t1-v1`, `estuary-t4-v1`: active commitment to seek six credits, not an already-approved allocation. Relationship: prior commitment supports `e-bridge`. |
| C03 — MEM-03, ADJ-01–03 | Adjudicator, review: assess funding interaction. | `scenario-v1`, `estuary-t4-v1`, `upland-t4-v1`: six plus six exceeds ten. Flag resource contention with both action sources. Reduced allocations, deferral, or an amendment are defensible; allocating twelve without changing authorized resources is not. Player expectations of support do not establish consent. |
| C04 — MEM-01–02/05 | Adjudicator, t3 then review: determine continuing effect status. | At t3, `effect-customs-scheduled` is delayed. At review, `effect-customs-active` supersedes it and customs hours are extended. `effect-guarantee-cancelled` supersedes `effect-guarantee-scheduled`; no guarantee activates in Turn 4. No double application. |
| C05 — PLAY-03, MEM-03–04, OPS-07 | All audiences, review: inspect coordination. | `coordination-1` authorizes shared coordination. Adjudicator can link `e-announce` and `u-announce`; each player sees its own action and the shared record, not the other submission. Publication requires both approvals; a joint announcement is not an approved outcome yet. |
| C06 — RFI-01–03, MEM-01/04 | Adjudicator and Estuary, review: decide what the permit RFI establishes. | `rfi-permits` is unanswered. `claim-open` is unverified; `observation-permits` is visible only to adjudicator at this point and contradicts the universal claim without establishing the full extent. Estuary gets an unresolved information need, not the hidden report. |
| C07 — RFI-04, MEM-05, REP-04 | Adjudicator and Estuary, release; compare review: handle the late answer. | `ruling-permits` at 16:00 precedes `rfi-permits-answer` at 18:00. The answer discloses existing information; the deferred ruling remains intact. The observation becomes available to Estuary at 18:00 despite being recorded in Turn 3. Neither answer nor later ruling may enter review-cutoff inputs. |
| C08 — GAME-04, PLAY-01, MEM-05 | Adjudicator and Upland, review: inspect imported action. | `import-invoices`, `upland-t4-v1`, original artifact: all four fields map verbatim to `u-inspect`; staff quantity, firms, and date remain missing. Do not invent allocations or timing from “available” or “soon.” `review-invoices` is an adjudicator-only unresolved interpretation. |
| C09 — PLAY-01–02, MEM-05, OPS-09 | Adjudicator, review then release: compare submitted versions. | `estuary-t4-v1` requests six; `estuary-t4-v2` requests four with the same action ID. `amendment-accepted` establishes acceptance at 15:00; the original stays recoverable. The old funding issue is stale, not a current twelve-credit demand. `ruling-fund` and `effect-fund` record four plus six, leaving zero. |
| C10 — ADJ-04, MEM-04, OPS-07 | Estuary and Upland, release: produce feedback. | `feedback-estuary` and `feedback-upland` are separate releases. Estuary may now use its permit answer/report. Upland must not receive that answer, observation, Estuary's private submission, or hidden provenance. Each council can learn its approved allocation without seeing the other's private drafts. No announcement success may be invented. |
| C11 — EXP-03, MEM-03 | Adjudicator, review: triage relevance and uncertainty. | `e-festival` uses volunteers and explicitly no joint funding: do not group it into the funding conflict without evidence. Identify uncertainty in `u-inspect`; distinguish anticipated public/business reactions from actual observations. Record missed mandatory links and unsupported flags separately. |
| C12 — GAME-01–02 | Adjudicator, review with variant: reassess configuration. | `variant.json`: fourteen credits cover the original twelve-credit demand; no insufficient-funds flag. Three simulated days per turn do not change the recorded wall-clock deadlines. Do not replay the base continuation as if it were variant truth. |
| C13 — ADJ-01/03, OPS-05/08 | Adjudicator, review: inspect static model examples. | `model-examples.json`: success cites authorized evidence and proposes rather than applies; unavailability and invalid evidence permit manual review; amendment makes old output stale. This specifies failure behavior, not verified adapter behavior. |

## Access checks

At review, Estuary must not see `upland-t4-v1`, `import-invoices`, `review-invoices`, or `observation-permits`. Upland must not see `estuary-t4-v1`, `rfi-permits`, `review-invoices`, or `observation-permits`. At release, Upland still must not see the observation, its RFI answer, Estuary's revisions, or Estuary's feedback. Shared public historical rulings and commitments do not authorize traversal to their private source submissions.

At t3, no Turn 4 record is visible, including the customs activation, even though its schedule is known. At review, no amendment, fund ruling, RFI answer, or feedback is visible. Apply the same boundaries to future searches, summaries, source previews, links, attachments, exports, and AI context.

## Coverage limits

This package specifies roadmap Phase 0 coverage (GAME-01–02, MEM-01–05, EXP-03), plus concrete Phase 1/2 acceptance seeds listed above. C01/C12 are partial GAME-01 evidence; C09 does not execute concurrent writes; C13 does not test a real model. Full requirements remain unverified until exercised in implementation. No Phase 0 case claims 150-user capacity, replay branching, M&S integration, or comparative AI usefulness.

## Fixture version 2 — Phase 1B revision

Version 1 retains its accepted Phase 0 completion under B-05. Version 2 revises
release expectations; the earlier AI walkthrough is not evidence for these changes.
The nine version 2 snapshots are independently maintained application test oracles.

- Estuary's pledge is explicitly shared; Upland's funding request remains private.
  A council may reason from facts disclosed to it. Such deductions never authorize
  retrieving a private submission, ruling, RFI, or evidence source.
- `commitment-1-updated` records the four-credit approved bridge allocation at
  16:00 and supersedes the original six-credit request. The adjudicator sees it
  immediately; both councils receive this expressly shared update at 19:00.
  Only the adjudicator may follow its `ruling-fund` reference. C09/C10 require
  this update at release, preservation of the earlier pledge, and no earlier leak.
- Announcement approval is deliberately pending at the release checkpoint.
  Neither consent nor submitted announcement actions establish publication.
  C05/C10 continue to prohibit invented announcement success.
- The variant remains an initial-review-only exercise; model examples remain
  static examples, excluded from the explorer. No new AI or human efficacy claim
  follows from this fixture revision.
