# Decisions and open questions

Status: initial log, 2026-09-09. Established direction comes from the project discussion. Proposals below are not final technology selections.

## Established direction

| ID | Direction | Consequence |
| --- | --- | --- |
| D-01 | Research focuses on AI pre-adjudication usefulness to humans. | Human effort, omissions, and refinements are primary evaluation evidence. |
| D-02 | The product also supports actual wargame play. | Player collaboration, RFIs, adjudication, state updates, and feedback are core workflows. |
| D-03 | Games are configurable and support human, AI, and imported actions. | Separate scenario configuration, actor identity, and controller implementation. |
| D-04 | Living memory must serve adjudicator and fog-of-war views. | Preserve history, provenance, action status, relationships, and knowledge boundaries. |
| D-05 | Historical replay, modified action sets, and added AI actors are intended capabilities. | Preserve versioned inputs and branch history from the outset. |
| D-06 | The target includes air-gapped operation with local inference. | Required services and dependencies need offline operation/provisioning. |
| D-07 | Installation and initial configuration are first-class workflows. | Normal administration must not require in-depth Compose or environment-file editing. |
| D-08 | Scale ranges from single-digit evaluation users to 150 simultaneous users with multi-user teams. | Validate collaboration and application concurrency separately from inference capacity. |
| D-09 | Design should be system-agnostic; Ubuntu and Windows VDI are likely deployment components. | Keep platform assumptions explicit and interfaces portable. |

## Provisional design choices

| ID | Proposal | Validation or decision needed |
| --- | --- | --- |
| P-01 | Browser access from Windows VDI to an Ubuntu-hosted application. | Confirm VDI topology, supported browser, network, and authentication constraints. |
| P-02 | Modular application plus background workers and a model adapter. | Verify initial operational simplicity and scaling needs. |
| P-03 | Append-only history, snapshots/views, and preserved source artifacts. | Choose transaction boundaries and the extent of event sourcing. |
| P-04 | Evaluate a graph relationship layer against a simpler baseline. | Use retrieval and operational evidence before selecting a database. |
| P-05 | Simultaneous submissions and joint review as the initial turn policy. | Adopted for Phase 0 by B-02; broader lifecycle configuration remains future work. |
| P-06 | Shared drafts, comments, revision history, and conflict detection before character-level live editing. | Validate that this meets team collaboration needs in pilots. |
| P-07 | Human approval for operational rulings; explicit automated research mode. | Phase 0 authority and release baseline adopted by B-02; automated mode remains Phase 2 work. |

## Open decisions

| ID | Question | Needed by |
| --- | --- | --- |
| O-01 | Initial fixture/action baseline resolved by B-01–02; real-game refinements may supersede it. | Phase 0 baseline recorded |
| O-02 | Initial simultaneous review, amendment, late-RFI, and release policies resolved by B-02. | Validate in human walkthrough and Phase 1 |
| O-03 | Team-shared knowledge and named-record sharing adopted by B-02; individual compartments deferred. | Validate in Phase 1 |
| O-04 | What local authentication/identity service, certificates, and administrator access are available? | First deployment design |
| O-05 | Which implementation language, application framework, primary store, and job mechanism best fit maintainability and offline packaging? | Phase 1 |
| O-06 | What local model service, hardware, context limits, and structured-output capabilities are available? How are model artifacts provisioned offline? | Phase 2 |
| O-07 | Which external game formats should be imported first, and how will missing context be represented? | Initial import and later adapter expansion |
| O-08 | What reviewer protocol and practical success thresholds will determine whether preparation helps? | First comparison study |
| O-09 | How should downstream historical moves be retained, revised, or regenerated after divergence? | Phase 4 |
| O-10 | What representative workload, latency targets, inference queue targets, backup frequency, and recovery objectives define full-game readiness? | Set before phase 5 testing |
| O-11 | What export, retention, audit-access, and diagnostic-handling policies apply in the deployment environment? | Operational pilot |

These questions do not block all progress. Resolve each before implementing behavior that depends on it; keep independent work moving.

## Phase 0 baseline decisions — 2026-09-09

### B-01 — Non-military scope and authentic submission content

Status: accepted baseline. Problem: the broad architecture could be read as requiring structured player inputs or military adjudication. Chosen approach: an overall free-text turn intention and any number of actions with Title, Description, Intent of Action, and Anticipated reaction; separate system metadata and source-linked interpretations. Content is versioned so the baseline can evolve. Military movement/combat and M&S integration are separate work.

Alternatives: mandatory structured resource/target fields; a unified military/non-military submission workflow. Evidence: project owner supplied the actual action format and explicitly limited this build to non-military actions. Consequence: preserve prose, treat anticipated reactions as expectations, and resolve missing context through review. Requirements: PLAY-01/05, GAME-04, MEM-01/05. Verification: C01, C08, C11 in the [acceptance cases](phase0/acceptance.md).

### B-02 — Small synthetic game and human authority

Status: accepted initial implementation baseline. Problem: behavior must be concrete before implementation. Chosen approach: two civilian teams and four turns, simultaneous submissions, team-shared knowledge, a designated submitter, explicit consent to named cross-team coordination, and one adjudicator approving rulings and separately releasing feedback. Freeze submitted packages; accept explicit amendments only before ruling and reassess affected review work. Late RFI answers apply prospectively; corrections preserve history.

Alternatives: a supplied historical game, sequential turns, individual information compartments, or split approval roles. Evidence: owner selected a synthetic fixture and these simpler role/turn defaults, then authorized the revised plan. Consequence: the fixture can be walked through without a running application; other policies remain extensions. Zero-action submissions are an initial default, not a claim about all real games. Requirements: GAME-01–02, PLAY-01–05, ADJ-02–04, RFI-04, MEM-04–05. Verification: C01–C10, C12.

### B-03 — Acceptance artifacts before executable tooling

Status: accepted delivery baseline. Problem: executable acceptance needs clear expected behavior without prematurely choosing a stack. Chosen approach: Markdown contracts, JSON sources and role/time snapshots, a separate answer key, and a human reviewer script; no validator or application implementation in Phase 0. Use a provider-neutral static model example with recoverable failure cases.

Alternatives: runnable fixture tooling now, provider-specific integration, or benchmark-first development. Evidence: owner selected fixtures and walkthrough and authorized implementation of that plan. Consequence: cases are specified, not verified; the exit gate waits for a human run. Synthetic import provenance exercises mapping without selecting a real external format. Requirements: GAME-04, MEM-01–05, EXP-03, OPS-05/08. Verification: C01–C13 and [walkthrough findings](phase0/findings.md).

### B-04 — Provisional deployment and pilot targets

Status: provisional operational assumptions. Problem: an initial target is needed without available deployment evidence. Chosen approach: offline Ubuntu hosting, Windows VDI browser clients, eight concurrent pilot users, and p95 ordinary interactive request/response latency at or below two seconds, measured separately from inference. Require all seeded mandatory facts/interactions and zero unauthorized disclosures in the human walkthrough; collect effort before selecting comparative AI improvement thresholds.

Alternatives: early 150-user qualification or invented AI speedup thresholds. Evidence: project scale/offline requirements and the authorized Phase 0 plan; no performance measurements exist. Consequence: confirm identity/platform constraints under O-04, stack under O-05, model/hardware under O-06, and final workload/recovery targets under O-10. Requirements: EXP-03, OPS-01/03–05/07–08. Verification: human protocol now; measured performance in later phases.

## Maintaining the log

For a consequential decision, record the date, status, problem, chosen approach, alternatives, evidence, and consequences. Link affected requirements and verification. Mark superseded decisions rather than deleting the history. Track optional niceties separately until their value and scope are established.
