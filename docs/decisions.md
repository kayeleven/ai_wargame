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
| P-05 | Simultaneous submissions and joint review as the initial turn policy. | Confirm against the first actual scenario; retain configurable lifecycle boundaries. |
| P-06 | Shared drafts, comments, revision history, and conflict detection before character-level live editing. | Validate that this meets team collaboration needs in pilots. |
| P-07 | Human approval for operational rulings; explicit automated research mode. | Specify permissions, approval granularity, and feedback release policy. |

## Open decisions

| ID | Question | Needed by |
| --- | --- | --- |
| O-01 | What fixture scenario, action structure, and adjudicator roles should anchor the first build? | Phase 0 |
| O-02 | Which turn-resolution, amendment, late-RFI, and release policies are required initially? | Phase 0–1 |
| O-03 | Do team members share all knowledge, or can individual roles have restricted information? How is cross-team sharing authorized? | Phase 1 |
| O-04 | What local authentication/identity service, certificates, and administrator access are available? | First deployment design |
| O-05 | Which implementation language, application framework, primary store, and job mechanism best fit maintainability and offline packaging? | Phase 1 |
| O-06 | What local model service, hardware, context limits, and structured-output capabilities are available? How are model artifacts provisioned offline? | Phase 2 |
| O-07 | Which external game formats should be imported first, and how will missing context be represented? | Initial import and later adapter expansion |
| O-08 | What reviewer protocol and practical success thresholds will determine whether preparation helps? | First comparison study |
| O-09 | How should downstream historical moves be retained, revised, or regenerated after divergence? | Phase 4 |
| O-10 | What representative workload, latency targets, inference queue targets, backup frequency, and recovery objectives define full-game readiness? | Set before phase 5 testing |
| O-11 | What export, retention, audit-access, and diagnostic-handling policies apply in the deployment environment? | Operational pilot |

These questions do not block all progress. Resolve each before implementing behavior that depends on it; keep independent work moving.

## Maintaining the log

For a consequential decision, record the date, status, problem, chosen approach, alternatives, evidence, and consequences. Link affected requirements and verification. Mark superseded decisions rather than deleting the history. Track optional niceties separately until their value and scope are established.
