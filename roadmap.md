# Roadmap

Direction accepted 2026-09-11 under [B-11–B-14](docs/decisions.md#b-11--wrapper-ownership-and-framework-contracts).
Planned capabilities below are not implementation claims.

Status: Phase 0 complete. Phase 1A, 1B, 1C-core and 1C-admin (with bounded
corrections) are implemented and verified under `docs/phase1/`. The 1D commit
delivers **persistence foundation and initial helpers only**: the models in
`src/living_memory/workspace.py` exist, `save_draft_action`, `submit_draft` and
`claim_request_key` have no application callers, `templates/play.html` and
`templates/adjudicate.html` are placeholders, and there is no 1D verification record
or dedicated workspace behavior test. Workflows, service-level authorization, state
transitions, concurrency behavior and verification are outstanding.

**Scope exclusion, unchanged:** military movement and combat are submitted and
adjudicated in the separate M&S tool, and integration with it remains outside this
build. This roadmap covers non-military DIME-FIL activity only.

The remaining work includes adapting existing boundaries as well as new workflows.
It incorporates the 2026-09-11 clarifications and roadmap reviews.

## Architecture premise for all remaining phases

Two parts, separated by explicit contracts.

**The wrapper (fixed platform).** Identity, teams, roles, actors, scenario
configuration, player workspace, move writing, coordination, RFIs, move import, the
adjudication review surface, the white-cell surface, release control, replay
orchestration and experiment records.

**Frameworks (swappable).** An adjudication/preparation method plus its memory and
retrieval implementation. A framework reads frozen input from the wrapper and returns
proposals to it.

### Ownership and durability of state

Authoritative history, preserved run artifacts, and disposable projections have distinct
durability obligations.

| State | Owner and durability | Rationale |
| --- | --- | --- |
| Submissions, drafts, amendments, coordination, RFIs, imports | Wrapper, authoritative | Canonical player input, verbatim regardless of later tagging |
| Human rulings, established facts, confirmed/rejected links, release decisions | Wrapper, authoritative | Portable reference labels that must outlive any framework |
| Applied effects and canonical world state | Wrapper, authoritative | Recovery and audit must not depend on a candidate backend |
| Actor beliefs and disclosure records | Wrapper, authoritative | Fog-of-war reconstruction is a platform guarantee |
| **Run artifacts: original framework proposals, issue grouping as first proposed, proposed links, raw model output, supplied context, validation failures, and exactly what each reviewer saw** | **Wrapper-held, immutable, preserved** | **Not regenerable. A model rerun does not reproduce them, and audit and effort comparison depend on the original** |
| **Human review history: triage, regrouping, edits, accept/reject decisions, effort** | **Wrapper, authoritative, preserved** | **The primary research measure; cannot be reconstructed** |
| Projections, indexes, caches, embeddings, current-state materializations | Framework, disposable and rebuildable | Reconstructable from wrapper history when a framework is swapped |

Rule: **authoritative history and run artifacts are preserved and wrapper-held; only
derived projections are disposable.** Swapping or rebuilding a framework must lose
nothing but recomputable indexes.

### Contracts

1. **Input contract.** Immutable submissions, scenario premise, prior human rulings and
   established facts, RFI status, disclosure records, temporal cutoff.
2. **Output contract.** A review packet, a proposed adjudicator god view, and a proposed
   fog-of-war view per actor. Each item carries two independent labels:
   - **Provenance class:** game record, world knowledge, or assumption.
   - **Truth status:** established, claimed, disputed, or unresolved.
   These are orthogonal. A citable game record may contain a player's lie: "game record"
   never implies "established fact."
3. **Lookup contract.** Game-memory needs resolve automatically under authorization;
   world-specific needs are flagged for the human in the loop. A reference/RAG corpus is
   out of scope but must be able to register as a resolver later.

One framework is active per game. Comparison happens by reprocessing saved moves.

## Open-world adjudication premise

Scenarios set a start date and premise; the world is the bound. No rulebook, no fixed
action space within the non-military scope, no numeric win condition.

Military components are handled separately outside this application. Non-military
components remain in scope even when they reference or depend on military activity.
This does not require automated routing or M&S integration.

- Every player statement is a claim, including claims about their own capability.
- Truth, belief and effect are separate. A false claim can still be effective.
- Adjudicator decisions and RFI answers accumulate into the precedent baseline and must
  surface when a later move contradicts them.
- Scenario premises outrank the model's world knowledge; world knowledge still applies
  wherever the scenario is silent. Both directions of failure are defects.
- A useful packet presents the gap, not a verdict.
- The white cell plays every unrepresented actor, holds god view, and needs an **actor
  lens** over that view (see 1E).

## Decision before code: the boundary contract

[B-11](docs/decisions.md#b-11--wrapper-ownership-and-framework-contracts) supersedes the
former admin-to-memory projection prerequisite in the [Phase 1 contracts](docs/phase1/contracts.md).
The governing decision is recorded before 1D-remainder: it establishes the ownership
table, the three contracts, and framework registration independent of game activation.
The code transition and rebuild verification complete in 1W after 1E.

## Phase 1 — Playable human workflow and durable memory

Implemented and unrevised: 1A, 1B, 1C-core, 1C-admin, and the 1D persistence foundation
described in the status note.

| Milestone | Deliverable | Acceptance gate |
| --- | --- | --- |
| **1D-remainder — Workspace workflow** | Service-level authorization, state transitions and concurrency behavior over the existing persistence, plus player-facing drafting, shared editing with ownership and comments, submission authority, explicit amendments, coordination consent, RFI submission and move import. | Recoverable edit conflicts with authorized base/current/submitted comparison; only the designated submitter submits; imports retain omissions verbatim; coordination consent exposes no private submission; dedicated workspace tests and a 1D verification record exist. |
| **1E — Review surface, white cell, release** | Wrapper-owned review surface: issues, evidence, relationship decisions, split/merge, RFI answers, rulings, effects, the white-cell actor lens, separately released feedback, framework-neutral human decision records, preserved run artifacts, reviewer-effort capture. | Stale reviews detected; atomic once-only effects; late answers preserved historically; lens fidelity and release boundaries hold (below); accepting framework-authored proposals needs no wrapper schema change. |
| **1W — Wrapper/framework boundary transition** | Adapt the coupled code so B-11's boundary is real. | The wrapper runs a game with no framework installed; framework projections can be dropped and rebuilt with no loss of authoritative history or run artifacts. |

### White-cell actor lens

The white-cell player **retains god view**. The lens is a presentation filter that helps
them role-play an actor, not a permission boundary.

- An optional lens selects an actor only: "show only what South Africa would know now."
  It uses the current game or replay context; no separate time selector, truth/belief
  toggle, or side-by-side lenses are required. It filters presentation, not access.
- Lens state is clearly indicated, and returning to the unfiltered god view is always
  available.
- Actor knowledge and belief still need tracking, because the lens has to be accurate.
  That tracking is wrapper-owned and already required by the fog-of-war views.
- **No actor-level grants and no grant migration are required.** Existing team-scoped
  grants plus `adjudicator` (`resolve_principal` in [identity.py](src/living_memory/identity.py)) stay
  as they are.

Acceptance gate: the lens accurately represents that actor's information in the current
game or replay context, drawn from the same records the fog-of-war view would use; released white-cell
responses respect disclosure decisions. The gate does **not** test that the white-cell
person is prevented from seeing other actors' information, because they are not.

### 1E review and release requirements

- **Provenance and truth status on every item,** kept independent.
- **Preserved run artifacts:** original proposals, raw output, supplied context,
  validation failures, and exactly what each reviewer saw, stored immutably.
- **Reviewer effort capture:** time on task, evidence navigation, edits by significance,
  accepted/rejected proposals, regrouping.
- **Claim-centred review model:** asserted, established, precedent, judgment-needed.
- **Belief tracking:** per-actor belief and claim-to-audience records, wrapper-owned.
- **Release boundary, three separate treatments:**
  1. **Internal evidence:** adjudicator-only material, never released, and not required
     to be disclosable for a derived effect to be released.
  2. **Audience-visible citations:** sources shown to that audience, which must pass an
     automated disclosure check. **Necessary but not sufficient:** a proposal can leak a
     secret in its prose while citing only public records, or cite nothing relevant.
  3. **Approved disclosures:** an adjudicator may deliberately release an observation or
     effect without its confidential causal evidence. An explicit recorded decision.
  Human approval remains the operational release authority. Add adversarial leak tests where cited
  sources are clean but the text is not.

### Scenario configuration changes

- `rules` is currently **mandatory** (`ScenarioConfiguration` in [administration.py](src/living_memory/administration.py)) and must become optional for open-world scenarios.
- Numeric resources are **already optional**; no change needed.
- There is **no scenario start-date or premise field** today. Add both, distinct from
  `public_rules`/`public_briefing`.
- **Actors must currently belong to a team** (`ScenarioConfiguration.validate_graph` in [administration.py](src/living_memory/administration.py)). Unrepresented actors must become valid, with a white-cell controller kind, since the white cell plays them.
- **Roster and controller revisions are rejected** (`revise_game` in [administration.py](src/living_memory/administration.py)). A controlled path is needed for adding actors mid-game and recording changes of control (GAME-05).

### 1W scope

- **Game activation must not create a framework dataset.**
  `activate_game` in [administration.py](src/living_memory/administration.py) calls
  `create_operational_dataset` directly. Move it behind framework registration so
  activation succeeds with no framework configured.
- **The authenticated memory route must go through the seam.**
  `authenticated_memory` in [web.py](src/living_memory/web.py) depends directly on `Dataset` and
  `MemoryReader`. Route queries through the retrieval interface, with the 1C store as one
  registered implementation.
- **Rebuild path:** projections rebuild atomically from wrapper history with a
  pending-rebuild state, reusing the 1C pattern. Run artifacts are never rebuilt; they
  are preserved.
- **Recovery independence:** backup and restore recover authoritative history and run
  artifacts with no framework present; projections rebuild afterwards.

Coverage: GAME-01–02/04, PLAY-01–05, ADJ-02–04, MEM-01–05, RFI-01–04, OPS-02–03/06–07/09 initially.

## Phase 1G — Setup and offline dependency discipline (new, small)

Runs alongside 1D/1E. [Requirements](requirements.md#boundaries-and-unresolved-specifications)
distinguish development-host support from full installer parity:

- **Developer and evaluation convenience, not installer parity.** Ubuntu remains the
  deployment target; Windows support here covers the development host.
- **Windows means native Windows PowerShell**, with WSL supported but not required.
  Document prerequisites: Python 3.12, `uv`, Docker or an existing PostgreSQL 16, and
  PostgreSQL client tools for backup/restore.
- Setup generates its own secrets; no hand-edited `.env` or Compose for normal use.
  Invalid configuration fails at startup with an actionable message.
- Every new dependency must be packageable offline and pinned as a condition of adoption,
  including the inference server, job runner and any candidate backend.

Exit gate: a clean checkout reaches a running instance with one documented command on
both hosts, and the dependency inventory names an offline source for every entry. No
offline-provisioning or installer-parity claim.

Coverage: OPS-02/03/06, development scope only.

## Phase 2 — Framework seam, first two methods, queued processing, replay

- **Local model adapter.** Configurable endpoint (OpenAI-compatible local servers),
  capability probing, structured-output validation, timeouts, recoverable failure. Record
  model identity and settings with every run.
- **Candidate model screening.** Premise adherence (a transplanted scenario whose
  premises contradict real-world facts) and content engagement (terror attacks, WMD
  claims, atrocities). A model that refuses or dilutes scenario content is unusable.
- **Queued processing, explicitly delivered** (OPS-05,
  [requirements](requirements.md#deployment-and-operational-requirements)): a job runner with status, priority,
  cancellation, retry and recorded failure; worker budgets separate from the interactive
  pool; inference never awaited inside an interactive transaction. Interactive work
  continues while inference is saturated or unavailable.
- **Method definitions as versioned data.** Prompts, pass structure, batch strategy,
  lookup budget and model settings are configuration, not code, because every code change
  in the operational environment costs an offline update cycle.
- **Two methods:** single pass, and lookup-then-review using the lookup contract.
- **Two memory backends behind one retrieval interface:** the 1C temporal store, and a
  thin second implementation exercising multi-step traversal, to prove the interface
  generalises.
- **View generation** under the output contract, including per-actor fog-of-war views and
  the white-cell lens.
- **Replay and reprocessing:**
  - **Isolated replay histories.** A replay never modifies the original game's history.
    It creates **its own wrapper-owned history**: replay rulings, established facts,
    release decisions, reviewer effort and run artifacts are authoritative and preserved
    within that replay, under the same ownership table. They are not framework state and
    not disposable. Original and replay histories remain independently inspectable.
  - **Two comparison modes, reported separately:**
    - **Frozen-context comparison:** methods run on identical inputs for one turn.
      Isolates method effects most cleanly, and matches
      the [evaluation plan](docs/evaluation.md#cases-and-controls)'s controlled-input assumptions.
    - **Trajectory comparison:** a framework carries its own state forward across the
      recorded move sequence. This measures end-to-end usefulness, including downstream
      consequences of earlier preparation, which frozen-context tests cannot show.
      Effort figures remain meaningful but need different interpretation and controls,
      because trajectories differ in world difficulty as well as method: normalize per
      turn and per volume, record trajectory divergence, and counterbalance reviewers.
      Use both modes; neither subsumes the other.
  - **Minimum incompatible-move policy.** When a recorded move depends on resources,
    knowledge, actors or effects absent from a trajectory, apply and record one of: retain
    as attempted (the claim stands, feasibility adjudicated in that trajectory), flag as
    infeasible, or skip with reason. Per-run default, recorded with the run. Regeneration
    stays in Phase 4. The default is **retain as attempted**; record any override.
  - **Applicability rules for recorded material.** State per run whether original RFI
    answers, disclosures and rulings remain applicable, are re-derived, or are withheld
    once a trajectory diverges. Unstated inheritance is a defect.
  - **Replay review session** in the 1E surface with effort captured, under a cutoff that
    excludes post-cutoff information.
  - **Ruling policy per run:** **automated research mode by default**, with a toggle
    for human review. Record the selected policy and any changes. Reuse of recorded
    rulings remains an explicit alternative where applicable. These policies are not
    interchangeable evidence; operational games retain human authority.
- **AI and white-cell assistance.** Framework-drafted responses for unrepresented actors
  and AI participant control (GAME-03/05), subject to human release in operational
  games; research replay follows its recorded ruling policy.
- **Experiment records.** Method and prompt versions, backend and rebuild version, model
  identity, supplied context, lookups requested/returned/unavailable, raw output,
  validation failures, human edits, timing, comparison mode, incompatible-move policy and
  applicability rules.

Exit gate: the same saved game runs end to end under both methods and both backends;
reviewers can trace, edit and reject any proposal; interactive work continues during model
failure and saturation; a replayed turn shows no post-cutoff leakage; replay histories are
provably isolated and preserved; no wrapper schema change was needed to add the second
backend or method.

Coverage: GAME-03/05, ADJ-01–03, EXP-01–02/04 (initial), REP-01–02/04 (initial), OPS-05/08.

## Phase 2M — Mock narrowing set (new)

Mock scenarios narrow candidates and act as regression tests. They establish behavior **on
the tested cases only** and do not prove unrestricted model behavior. Harbor Relief remains
a permissions and temporal oracle but does not represent real games: it is rule-bounded and
its central interaction is arithmetic.

Add an open-world, non-military mock scenario with: a premise that deliberately contradicts
real-world facts; overstated capability claims and false statements to other players; a
later move contradicting an earlier adjudicator decision; unrepresented actors whose
reactions must be adjudicated; an RFI establishing a missing world fact; and 100+ actions
across several turns for overwhelm and batch boundaries.

Pass/fail properties provable here: no fog-of-war leak (including prose leaks with clean
citations); no fact laundering from a player claim; prior commitment and precedent
recovery; premise adherence; lens fidelity; no double-applied effect; graceful
model-failure behavior; behavior at volume.

Gate outcomes:

- **Two or more survivors:** proceed to Phase 3 with all of them.
- **Exactly one survivor:** proceed, recording that the operational comparison validates
  one candidate rather than selecting among several, and consider adding a variant to
  restore a comparison.
- **No survivors:** fix or replace candidates and re-run; do not deploy to the operational
  environment to discover mock-detectable failures.

Candidates introduced later, including the Phase 3C variants, must pass these regression
gates before entering operational comparison.

Coverage: MEM-01–04, EXP-03 (partial), OPS-07.

## Phase 1F — Integrated game and recovery validation (moved, gate restored)

Moved after Phase 2M so it exercises the framework seam. Its original criteria stand in
full: a small group **completes and restores a game without database edits**, **prior
commitments are discoverable**, and there is **zero unauthorized disclosure**, alongside the
multi-turn browser exercise, concurrency checks, restore drill and requirement mapping of
applicable C01–C12 to application evidence. 1F validates integrated gameplay as well as
deployment.

Performance artifact: **"Local eight-user sanity check"** with host specifications,
workload, concurrency, durations, errors, pool waits and observed percentiles. The
provisional p95 two-second target is assessed only within that run. **No 150-user capacity
evidence.** OPS-04 requires a later representative deployment with deadline-burst workload.

## Phase 3 — Operational-environment deployment and comparison

**3A — Research deployment.** Offline bundle containing the wrapper, every surviving
candidate framework and backend, and all dependencies, with integrity verification; a
repeatable offline update path; migrations preserving accumulated games, run artifacts and
experiment records across updates; analysis, reporting and diagnostics that run inside the
environment, since results cannot be exported; backup, restore and recovery drills there.

**3B — Play tests and reprocessing.** One framework per play test, moves saved. Reprocess
each saved play test under the other candidates. Human replay review sessions measure
effort and corrections. Control for reviewer familiarity by rotating reviewers or method
order, and record which control was used. Report frozen-context and trajectory comparisons
separately, with trajectory divergence recorded alongside effort.

**3C — Remaining method variants.** Batch-then-reconcile and combined, with batch
boundaries compared by player, geography, domain, objective and linked group. Keep an
all-action index for reconciliation and measure links lost at batch boundaries. These
variants pass the 2M regression gates first.

Exit gate: a framework, including its method and storage/retrieval approach, is selected on
operational-environment evidence before the next real game. Report reviewer effort, missed
interactions and commitments, irrelevant flags, feedback quality, information discipline
and operating cost. Mock results narrow the field; they do not justify the selection.
Storage is chosen on observed need, not assumed graph advantages.

Coverage: MEM-02–06, EXP-01–04, ADJ-01–02, RFI-03, OPS-01/05–06/08.

## Phase 4 — Counterfactual replay and broader participation

Extend replay to alternate rulings, modified action sets and added AI actors. Apply an
explicit retain/revise/regenerate policy to affected later actions, extending Phase 2's
minimum incompatible-move policy with human revision and controller regeneration. Expand
import adapters based on the source games encountered in Phase 3.

Addition: every trajectory records which framework produced it, so two trajectories are
never compared as if they shared a history.

Exit gate: a saved game branches, diverges and continues coherently while preserving its
original record. Reviewers can explain differences in actions, effects, knowledge and
controller participation.

Coverage: GAME-04–05, REP-01–04, MEM-05, EXP-02.

## Phase 5 — Full-game deployment readiness

Unchanged. Guided installer, TLS, organizational identity integration, certificates,
offline upgrade tooling, migration recovery, deployment sizing, and the target Windows VDI
browser environment. Validate 150 simultaneous users under a representative mix of
collaboration, submissions, RFIs, queries, review and feedback release, measuring
application responsiveness separately from inference throughput.

Exit gate: clean offline install/update/restore drills pass; concurrency and visibility
tests pass; agreed capacity and recovery targets are met; an operator can run the system
from the deployment guide.

Coverage: OPS-01–09 and full-scale PLAY-02–04.

## Delivery order

B-11 decision → 1D-remainder → 1E → 1W → Phase 2 → 2M → 1F → 3A → 3B/3C → 4 → 5.
1G runs alongside 1D/1E. 2M authoring can begin during Phase 2.

## Delivery principles

- Military movement and combat stay in the separate M&S workflow. Open-world latitude
  applies within non-military DIME-FIL activity.
- Keep permissions, provenance and offline packageability in every increment. Installation
  is a continuing obligation, not a Phase 5 event.
- Authoritative history and run artifacts are preserved and wrapper-held; only derived
  projections are disposable. Adding a framework is a new module behind existing contracts,
  never a core rewrite.
- Boundary claims require adapted code, not only new modules. A contract the current code
  contradicts is a migration task with an owning milestone, and the governing decision is
  recorded before the milestones it affects.
- Replay adds its own preserved history and never modifies the original game's.
- Method variation belongs in versioned configuration and data wherever possible.
- Mock testing establishes behavior on tested cases and eliminates candidates. The
  operational environment selects the framework.
- Player input is canonical and verbatim. Framework-generated interpretations and
  derived storage are source-linked and framework-owned; original proposals and human
  triage, regrouping and other review history are preserved by the wrapper.
- Provenance is not truth status. A citable record may contain a lie.
- Lenses filter presentation; permissions control access. Do not conflate them.
- Automated checks screen; humans authorize operational release. Research replay
  follows its recorded ruling policy.
- Do not interpret inference throughput as interactive user capacity, or local pilot
  results as deployment qualification.

## Revision decisions and remaining questions

| ID | Decision or remaining question | Status / needed by |
| --- | --- | --- |
| N-01 | Automated research mode is the replay default, with a toggle for human review. | Resolved in B-13; Phase 2 |
| N-02 | Which candidate backends enter the offline bundle (typed relational, graph, semantic/vector, narrative baseline), and does each install acceptably in the operational environment? | Phase 2 / 3A |
| N-03 | Does the local model engage with required scenario content and hold to contradicted premises? | Phase 2 model selection |
| N-04 | Actor-only lens, using the current game or replay context. | Resolved in B-12; 1E |
| N-05 | Retain incompatible recorded moves as attempted by default. | Resolved in B-13; Phase 2 |
