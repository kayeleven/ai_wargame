# Navigation inventory — initial design trial

Created 2026-09-15 and reconciled with the implemented 1U-2 milestone branch on
2026-09-25. Governed by [design guide revision 5](design-guide.md).
“Trialed” below means a structural scenario trace in [the examples](design-examples.md),
not an unaided usability pass. Entries distinguish proposed/trialed placements from those accepted for now. Existing
capabilities are noted separately from implementation of the proposed UI.

| Item | Context / scope | Region | Placement rationale | Roles | Page pattern | Design status | Implementation status | Trial-default exception / evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Home, identity, account/sign-out | Application | Persistent shell | Applies regardless of game/task | All signed-in roles | Shared | Trialed | Implemented in 1U-1; account is read-only pending later account management | None; E1–E3 |
| Game, team/role, turn and state | Authorized current context | Context | Scopes the work; switch only when there is a choice | All | Shared | Trialed | Implemented for home and workspace/review; administration retains its task-specific context | None; E1–E3 |
| Workspace | Game/team/turn | Destination | Place for team authoring/submission | Player | Workspace | Trialed | Implemented entry, named saved regions, explicit conflict recovery and protected editor/command retries in 1U-1; 1U-2 adds the effective/pending/rejected/draft lifecycle, deliberate revision entry and always-visible Discussion and Draft history. Action-volume layout and automatic teammate refresh remain 1U-3 | None; E1 |
| Amendment review | Authorized game/team/turn | Destination | Existing accept/reject task with immutable comparison | Adjudicator | Review | B-18 scoped; combined PR 4 walkthrough complete; milestone acceptance pending | Dedicated page with pending/history links, immutable complete comparisons, changed-action/field anchors, persistent reasons and retained decision recovery implemented in 1U-2 | Keyboard/narrow and owner walkthrough evidence in [1U-2 verification](phase1/verification-1u-2.md); no new review authority |
| Rejected revision | Authorized team/turn | Workspace notice and submitted version | Inspect the rejected content and persistent reason | Player | Workspace | Combined PR 4 walkthrough complete; milestone acceptance pending | Full lifecycle presentation and deliberate correction entry implemented in 1U-2. A newer effective version supersedes the current rejection notice/state while the rejected amendment and reason remain in history | No adjudicator access granted; [1U-2 verification](phase1/verification-1u-2.md#pr-4a-owner-review-corrections--2026-09-25) |
| Memory | Authorized game view | Destination | Separate exploration task | Player, adjudicator | Pattern to be tested separately | Proposed | Deferred: operational data has no application projection writers; fixture explorer repaired in 1U-1 | Outside current examples; data-backed authenticated entry required before placement |
| Action selection / All actions / previous-next | Team package | Work area: task-local navigation | Selects primary action without changing task | Player | Workspace | Trialed | Not implemented as proposed; action-volume layout remains 1U-3 | None; E1 |
| Package submission confirmation | Team package | Work area: task view | Acts on package as a whole, reached by labeled command/link | Designated submitter | Workspace / Review | Trialed; combined PR 4 walkthrough complete; milestone acceptance pending | Implemented in 1U-2: exact immutable live-action package review, complete effective-version comparison, explicit initial/renewed confirmation and explanation of changed expectations | Ordinary/enhanced, keyboard and 375px evidence in [1U-2 verification](phase1/verification-1u-2.md#pr-4b--exact-package-review-and-renewed-confirmation-explanation); no automatic preconfirmation |
| Package context and guidance | Selected team task | Supporting | Consult state and writing guidance; no chat assumption | Player | Workspace | Proposed after feedback | Not implemented as proposed | E1; replaces chat-like sidebar |
| Overall intention | Team/turn package | Work area: package-level content | Separate readable content and editor/save scope from selected action | Player | Workspace | Proposed after feedback | Existing intention read/edit and independent save scope are implemented; the proposed action-volume layout remains 1U-3 | E1 |
| Team comments | Team task; placement unresolved | To be determined | Existing comments do not establish a chat interface | Authorized teammates | To be trialed | Proposed / deferred | Discussion and Draft history remain visible on current, historical and completed workspace overviews; the sidebar design is withdrawn and final comment/composer placement remains 1U-3 | Needs its own placement trial |
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

The combined PR 4 owner walkthrough is complete, including both B-18 revision paths,
exact package confirmation, renewed confirmation and the player lifecycle. Automated
coverage also verifies the inclusive deadline boundary and visibly late first
submissions. The integrated 1U-2 milestone status is **Awaiting owner acceptance**;
the walkthrough does not accept unimplemented 1U-3 layouts, automatic refresh or any
other proposed placement. See the [verification record](phase1/verification-1u-2.md#pr-4-combined-owner-manual-review-4a--4b).
