# Navigation inventory — initial design trial

2026-09-15. Governed by [design guide revision 5](design-guide.md).
“Trialed” below means a structural scenario trace in [the examples](design-examples.md),
not an unaided usability pass. Entries distinguish proposed/trialed placements from those accepted for now. Existing
capabilities are noted separately from implementation of the proposed UI.

| Item | Context / scope | Region | Placement rationale | Roles | Page pattern | Design status | Implementation status | Trial-default exception / evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Home, identity, account/sign-out | Application | Persistent shell | Applies regardless of game/task | All signed-in roles | Shared | Trialed | Partial: home link exists; shared account/navigation treatment outstanding | None; E1–E3 |
| Game, team/role, turn and state | Authorized current context | Context | Scopes the work; switch only when there is a choice | All | Shared | Trialed | Partial: context exists in current pages; unified presentation outstanding | None; E1–E3 |
| Workspace | Game/team/turn | Destination | Place for team authoring/submission | Player | Workspace | Trialed | Partial: workflow exists; proposed shell/layout outstanding | None; E1 |
| Memory | Authorized game view | Destination | Separate exploration task | Player, adjudicator | Pattern to be tested separately | Proposed | Partial: memory routes exist; new placement not implemented; explorer blocker recorded | Outside current examples; not evidence of pattern fit |
| Action selection / All actions / previous-next | Team package | Work area: task-local navigation | Selects primary action without changing task | Player | Workspace | Trialed | Not implemented as proposed | None; E1 |
| Package submission confirmation | Team package | Work area: task view | Acts on package as a whole, reached by labeled command/link | Designated submitter | Workspace / Review | Trialed | Partial: submission exists; confirmation arrangement outstanding | None; E1 |
| Package context and guidance | Selected team task | Supporting | Consult state and writing guidance; no chat assumption | Player | Workspace | Proposed after feedback | Not implemented as proposed | E1; replaces chat-like sidebar |
| Overall intention | Team/turn package | Work area: package-level content | Separate readable content and editor/save scope from selected action | Player | Workspace | Proposed after feedback | Partial: intention exists; proposed placement outstanding | E1 |
| Team comments | Team task; placement unresolved | To be determined | Existing comments do not establish a chat interface | Authorized teammates | To be trialed | Proposed / deferred | Comments exist; sidebar design withdrawn | Needs its own placement trial |
| Game setup | Selected game | Destination | Configuration task with prerequisites | Administrator | Setup | Trialed | Partial: configuration exists; guided setup outstanding | None; E3 |
| Participants | Selected game | Destination | Game-centric placement task | Administrator | Roster | Settled for now | Partial: membership commands exist; unified roster/bulk placement outstanding | None; E3 |
| Selected participant set / person detail | Current roster/filter and game | Work area | Acts on one selected set or person | Administrator | Roster | Settled for now | Not implemented as proposed | None; E3 |
| Create accounts | Administration; return context retained | Work area: task entry | Starts a related creation task; does not mutate through a destination control | Administrator | Setup | Proposed | Partial: single-account creation exists; bulk/return flow outstanding | Unmeasured: requires its own trace before implementation |

## Counts and exception register

E1/E3 show two destinations per illustrated role/context; E2 has no assigned entry
or destination count; further review-workflow planning is deferred until needed.
E2 is retained as a presentation study, not an active inventory or feature proposal. This is not a complete menu
inventory and excludes future coordination, RFIs, release, white-cell and other
tasks pending their own placement tests. Memory and account creation are named entry
points here, but their internals are not validated by these three examples.

No trial-default exceptions recorded in E1/E3; E2 is unassessed. For each future exception record:
default, actual value/shape, role/context, linked example, justification and review
outcome. Repeated exceptions trigger a shared-default review. Firm constraints have
no per-page exception path.

Placement revision after user feedback: E1's chat-like supporting region is replaced
with package context/guidance; team comments remain unplaced. E2's adjudicator queue
and package-decision assumptions are withdrawn; its reading layout is role-neutral.
Participants and shared controls are accepted for now, without implementation claims.
The speculative review entries have been removed from the active inventory.
Subsequent moves
record old region, new region and reason. “Settled” requires acceptance of the design;
“implemented” requires evidence from the application, independently of design status.
