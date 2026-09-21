# Living Memory

Living Memory is a planned DIME-FIL turn-based wargame platform and research harness for AI-assisted human adjudication. DIME-FIL covers diplomatic, informational, military, economic, financial, intelligence, and law-enforcement activities.

The initial build focuses on non-military actions. Each player submits an overall free-text intention for the turn and any number of actions with four free-text fields: **Title**, **Description**, **Intent of Action**, and **Anticipated reaction**. Military movements and combat are submitted and adjudicated separately through an M&S tool; integration with that tool is a separate task.

The primary research question is which AI preparation methods give human adjudicators the most useful starting point for review and refinement. The operational objective is to support actual games: player collaboration and submissions, RFIs, adjudication, world-state management, and feedback under fog of war.

The platform must support human and AI participants, imported moves, historical replay, and counterfactual branches. It is intended to operate offline with a locally hosted LLM, initially at single-digit user volume and eventually with up to 150 simultaneous users.

The accepted direction separates a durable platform wrapper from swappable
adjudication and memory frameworks. The wrapper preserves authoritative game and
review history and original run artifacts; framework projections are rebuildable.
Open-world scenarios use premises and accumulated adjudicator precedent, with player
claims distinct from established facts. White-cell users retain god view and can
apply an actor-only lens. Military context does not exclude a non-military action;
military components are handled separately without M&S integration here.

Mock scenarios test and narrow candidates; operational-environment comparisons
determine suitability. Research replay defaults to automated mode with a human-review
toggle and retains incompatible moves as attempted. Operational games retain human
approval of rulings and release.

The next session resolves the recorded usability issues and implements the revised
design in existing templates before 1D-2. The application will also generate
experimental histories through agent play: Phase 2 includes a complete small
multi-turn DATE World game before its full method/backend comparison. Scenario
specifics are deferred until nearer testing. Agent-played histories supplement
curated cases, not human evaluation; player interpretation confirmation remains a
later experiment rather than required structured entry.

## Project documents

| Document | Purpose |
| --- | --- |
| [requirements.md](requirements.md) | Scope, functional and operational requirements, and acceptance evidence. |
| [roadmap.md](roadmap.md) | Dependency-ordered delivery phases and completion gates. |
| [docs/architecture.md](docs/architecture.md) | Proposed boundaries, memory model, workflows, deployment, and replay semantics. |
| [docs/evaluation.md](docs/evaluation.md) | Research hypotheses, comparison methods, measurements, and test cases. |
| [docs/decisions.md](docs/decisions.md) | Established direction, provisional choices, and unresolved decisions. |
| [docs/design-guide.md](docs/design-guide.md) | Planning-session baseline for shared page, interaction and visual design rules. |
| [Design examples](docs/design-examples.md) and [navigation inventory](docs/navigation-inventory.md) | Initial structural trials and proposed placement; includes a shared visual reference. |
| [docs/revision.md](docs/revision.md) | Operational addendum incorporated under B-16; ADD-01–09 trace to requirements and roadmap gates. |
| [Phase 0 acceptance package](docs/phase0/README.md) | Non-military fixtures, submission contracts, acceptance cases, and human walkthrough. |

## Status and document conventions

This repository contains the Phase 1A foundation, Phase 1B/1C-core temporal memory,
Phase 1C-admin identity and administration with bounded corrections, and 1D-1 shared drafting, submission, and amendment decisions.
Coordination, RFIs, and imports remain in 1D-2; full 1D is not complete. See the
[1D-1 verification record](docs/phase1/verification-1d-1.md). Framework
decoupling, white-cell lenses, AI and replay are planned work. The selected stack is
Python 3.12, FastAPI, Pydantic, SQLAlchemy, Alembic, PostgreSQL 16, Jinja and local
HTMX. See [developer setup](docs/development.md) for current schema/backup
compatibility and the [historical 1C correction record](docs/phase1/corrections-1c.md)
for its bounded verification evidence.

Requirements consolidate the project owner's objectives. The revised roadmap direction
is accepted under [B-11–B-14](docs/decisions.md#b-11--wrapper-ownership-and-framework-contracts);
B-16 incorporates operational detail while preserving that sequence and the evaluation
plan. [B-17](docs/decisions.md#b-17--usability-delivery-and-agent-played-research-games--2026-09-21)
adds the immediate usability gate and agent-played research checkpoint. Player
structure stays minimal; limited game/scenario references are permitted,
full RAG stays outside this application, and future external export is required with
scope unresolved. These decisions do not imply implementation. Open technology
choices remain proposals.

`requirements.md` describes product requirements. Software dependencies are defined in `pyproject.toml` and locked in `uv.lock`.

Maintain requirement identifiers when revising scope. Implementation work should reference the relevant requirements and record consequential design choices in the decision log.
