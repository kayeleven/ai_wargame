# Living Memory

Living Memory is a planned DIME-FIL turn-based wargame platform and research harness for AI-assisted human adjudication. DIME-FIL covers diplomatic, informational, military, economic, financial, intelligence, and law-enforcement activities.

The initial build focuses on non-military actions. Each player submits an overall free-text intention for the turn and any number of actions with four free-text fields: **Title**, **Description**, **Intent of Action**, and **Anticipated reaction**. Military movements and combat are submitted and adjudicated separately through an M&S tool; integration with that tool is a separate task.

The primary research question is which AI preparation methods give human adjudicators the most useful starting point for review and refinement. The operational objective is to support actual games: player collaboration and submissions, RFIs, adjudication, world-state management, and feedback under fog of war.

The platform must support human and AI participants, imported moves, historical replay, and counterfactual branches. It is intended to operate offline with a locally hosted LLM, initially at single-digit user volume and eventually with up to 150 simultaneous users.

## Project documents

| Document | Purpose |
| --- | --- |
| [requirements.md](requirements.md) | Scope, functional and operational requirements, and acceptance evidence. |
| [roadmap.md](roadmap.md) | Dependency-ordered delivery phases and completion gates. |
| [docs/architecture.md](docs/architecture.md) | Proposed boundaries, memory model, workflows, deployment, and replay semantics. |
| [docs/evaluation.md](docs/evaluation.md) | Research hypotheses, comparison methods, measurements, and test cases. |
| [docs/decisions.md](docs/decisions.md) | Established direction, provisional choices, and unresolved decisions. |
| [Phase 0 acceptance package](docs/phase0/README.md) | Non-military fixtures, submission contracts, acceptance cases, and human walkthrough. |

## Status and document conventions

This repository currently contains planning documents and static Phase 0 acceptance fixtures, not an implemented application. The human walkthrough and Phase 0 exit gate remain pending. There is no selected implementation stack, installer, or dependency manifest yet.

Requirements consolidate the project owner's stated objectives. Architecture and roadmap details are proposals unless identified as established direction. Open decisions are not silently treated as approved choices.

`requirements.md` describes product requirements. If Python is selected, a future `requirements.txt` may list software dependencies; it will serve a different purpose.

Maintain requirement identifiers when revising scope. Implementation work should reference the relevant requirements and record consequential design choices in the decision log.
