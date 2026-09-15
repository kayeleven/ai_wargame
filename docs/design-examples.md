# Design examples — first structural trial

2026-09-15. Applies [guide revision 5](design-guide.md). These are rough layouts and
design-level scenario traces, not an unaided usability test or implemented screens.
Sample names/content are illustrative. Lifecycle policy remains governed by the
existing decisions until explicitly changed.

## Shared shell and reference

All examples use a quiet home/account header, a context line, flat destinations,
and a dominant work area. Supporting material is alongside the work on wide screens
and in the same task flow on narrow screens. No sticky navigation is assumed.

The [visual reference](design-reference.html) renders the three rough arrangements
and shared controls. It is a static design sample: links and writes do not contact
the application. It is not a second implementation of the app.

Shared starting tokens: system sans-serif, 16px body/1.5 line height; spacing
4/8/12/16/24/32px; 4px corner radius; quiet neutral surfaces and one blue accent.
Text, not colour alone, communicates state. Palette, typography, spacing, borders
and radii live in [design-reference.css](design-reference.css) as semantic tokens;
components contain no independent colour/shape choices. Dark theme support can
reuse these roles; no dark palette or production migration is claimed. Participants
and shared controls are accepted for now; revised player/review layouts need review.

| Element | Shared pattern demonstrated |
| --- | --- |
| Buttons | One filled primary command per task region; outlined secondary; explicit destructive label; grouped controls wrap. |
| Fields | Label above control, required/optional in label, help below, field error adjacent; preserve control type and values. |
| Notifications | Persistent task-local status with named subject; attention/error includes next action. Unknown outcome has Check status, not a fresh Submit. |
| Rows | Compact readable title/name, secondary metadata, clear row boundary and explicit labeled action. Selection controls belong to their named record. |
| Expanders | Visible label and chevron; the entire hit region has the same boundary. Never used to hide destination groups. |

## E1 — Player workspace

**Role/task:** Blue submitter revises an action after a rejected revision. An ordinary
member sees the same writing pattern but lacks submission authority.

**Primary subject:** selected action. **Primary command:** Save action while editing.
Overall intention appears above the action area as readable package-level content,
with an explicit Edit overall intention expander and its own Save/Cancel scope.
It is distinct from Intent of Action. The action editor remains the primary work
region. The right sidebar shows package state and writing guidance, with no chat
transcript/composer. Existing comments do not imply an agreed chat feature.
Submission confirmation is a package-level view for the existing submit operation;
it names its parent, All actions, and makes the whole package the primary subject.

```text
Home                                  Blue submitter · Account · Sign out
Harbor Relief / Blue / Turn 1 · Current turn
Workspace (current) | Memory
─────────────────────────────────────────────────────────────────────────
All actions · Revision rejected: explain inspection timing [Read reason]
Overall intention · Saved team draft [Edit overall intention]
Actions (90)             Inspection schedule                 Package context
Search actions          Saved draft differs from submission Draft/submission state
Sort: display title     [Edit action]                        Writing guidance
17 Inspection schedule  Description …
18 Supply liaison       Intent of Action …
19 Port briefing        Anticipated reaction …
                        [Previous action] [Next action]
                        [Check package before submitting]
```

**Navigation trace:** home → game/team workspace (1) → selected action (2).
Package submission confirmation is another task view (3 if entered from that action), not
a nested destination. It is also directly reachable from the workspace (2).
Item links restore authorized game/team/turn and selection; All actions restores
search, display sort and list position. Selecting another action counts as navigation
even when the list and selected subject share one screen.

**Data boundary:** Save action updates only its four fields and applicable action
metadata. Intention has its own save boundary. Neither operation submits. A package
commitment makes scope and recipient explicit; it reconciles dirty editors before
continuing. Existing late-submission and revision approval rules are not redesigned
by this example.

**Scenario trace:** read the overall intention, edit an action, then save intention
without losing that dirty action text; find action 17 among 90 using visible search;
edit a long
description; receive a teammate update; retain local text and show the conflict;
compare named versions and resolve explicitly. A rejected revision and its reason
remain visible even after a draft correction. Save confirmation does not claim the
revision is accepted. Navigating to action 18 while dirty triggers preservation or a
loss warning; returning retains list context.

**Design outcome:** no new page pattern needed. Task-local action navigation can sit
beside the editor. A comparison needed for conflict recovery becomes the primary
subject temporarily, rather than appearing as a competing dashboard panel.

## E2 — Retained comparison study; further review design deferred

**Task explored:** understand substantial changes to an action in its package context.
**Primary subject:** the complete action, compared field by field. This study is
retained only as an illustration of presentation. Further review-workflow design is
deferred until a concrete need arises; no reviewer role, routing, approval command
or new feature is planned here. Existing adjudicator amendment behavior remains
unchanged. This deferral does not block the other design guidance.

```text
Home / Signed-in user
Harbor Relief / Blue / Turn 1 · Change comparison study
─────────────────────────────────────────────────────────────────────────
Action selection       Inspection schedule                 Review context
17 Inspection          What changed?                       Overall intention
  Description edited   Description: multiple edits         Related source text
  Reaction cleared     Anticipated reaction: cleared
18 Port briefing       Title: unchanged, readable
19 Supply liaison      DESCRIPTION · CHANGED
                       Base full text | Proposed full text
                       INTENT OF ACTION · UNCHANGED
                       Complete text
                       ANTICIPATED REACTION · CLEARED
                       Base full text | Explicit empty state
```

**Reading scenarios represented in the reference:**

- Multiple small edits across three substantial paragraphs: complete versions are
  presented field by field, without a screen full of interleaved strikeouts.
- Whole-field removal: the base text remains visible and proposed content explicitly
  says the field was cleared. This is a comparison case, not permission to submit an
  invalid action. Empty-field validity depends on the eventual workflow stage.
- Unchanged Title and Intent of Action remain visible because they inform the change.
- A prominent change summary links to the affected field headings. Word-level
  highlighting is supplemental and illustrated for only one paragraph.
- Package overall intention and related source material are consulted alongside the
  work. At narrow widths the versions and support stack with retained headings.

**Navigation/authority limits:** action selection is task-local; direct links must
restore the authorized package and comparison context. Entry destination, reviewer
roles, queue structure, parent links and end-to-end step counts cannot yet be settled.
The earlier adjudicator queue and package decision were premature and are withdrawn
from this design trial. No exception is justified or waived by that withdrawal.

**Limits of the retained study:** it shows multiple paragraph edits and whole-field
removal. Complete section replacement, added/removed actions and long unchanged
context were not exercised. These are limits on the example, not scheduled work.
Revisit comparison needs only when a concrete application task calls for them.

## E3 — Participant placement

**Role/task:** administrator places 50 existing accounts into game teams. Account
creation is a separate explicit task, with a return to the placement context.
**Primary subject:** roster when browsing; selected participant set during placement.
**Primary command:** Assign selected participants when the selected set is ready.

```text
Home                                     Administrator · Account · Sign out
Harbor Relief / Setup · Participants
Game setup | Participants (current)
─────────────────────────────────────────────────────────────────────────
Participants · 50 total · 38 assigned · 12 unassigned
Search people [            ]  Assignment [Unassigned]
[Create accounts]             [Select all 12 matching people]
Name                    Assignment            Selection
Avery Chen              Unassigned            [selected]
Jordan Ellis            Unassigned            [selected]
…
Place 2 selected participants
Team [Blue]  Authority [Member]
[Assign 2 participants] [Clear selection]
```

**Navigation trace:** home → game setup (1) → participants (2) → person (3) when
individual detail is needed. Bulk selection does not navigate; it changes the
subject of the roster's task. Individual detail names its parent, All participants.

**Data boundary:** selection, filter and preview do not assign anyone. Commitment
names the selected set, game, team and authority. The implementation must define
atomic versus partial completion before delivery; either result identifies which
records changed, which did not, and why. Do not imply a bulk submitter designation
that bypasses the one-submitter rule. Unknown outcomes retain operation identity and
reconcile per the implemented transaction semantics.

**Scenario trace:** filter 12 unassigned people from 50; select two; choose Blue;
verify those names in the placement summary; assign; confirm the two results and
update counts without losing the filter. A filtered selected row must not become an
invisible assignment: keep the full selected set inspectable and label selection
scope (this page versus all matching people). Stale eligibility is explained beside
the affected person. Clearing selection is distinct from removing membership.

**Design outcome:** Roster handles routine placement; guided Setup handles missing
prerequisites. No new pattern needed. Bulk action controls are in the work area,
not the destination region. Large rosters need pagination or bounded rendering in
implementation; neither browser performance nor bulk administration exists by virtue
of this example.

## Shared state coverage required before implementation acceptance

The original E2 decision-state trace was withdrawn; further review design is
deferred until there is a concrete need. Generic confirmed/failed/unknown outcome rules remain in the guide; they do
not justify adding approval operations to this example.

| State | E1 workspace | E3 roster |
| --- | --- | --- |
| Empty | Create first action; expose overall intention | No people / no matches distinguished |
| Dirty | Mark each editor; protect all exits and independent saves | Retain placement selections without implying assignment |
| Saving | Retain text; identify which save is pending | Identify pending selected set |
| Confirmed success | Name saved scope; submission unchanged | Named results and updated assignments |
| Invalid / failure | Field errors with input retained | Named invalid selection/authority; valid input retained |
| Conflict | Base/current/attempted comparison | Refresh eligibility and confirm affected selections |
| Unknown outcome | Reconcile same save operation | Reconcile same assignment operation/set |
| Read-only | Explain turn/access restriction | Explain lifecycle restriction |
| Denied | Safe shell/authorized home; no private content | Same |

## Structural check results and limits

| Check | E1 | E2 | E3 |
| --- | --- | --- | --- |
| Steps on representative route | 2; 3 including submission confirmation | Not assessed; deferred | 2; 3 for person detail |
| Parent/child depth below destination | 1 | Unmeasured | 1 |
| Destinations shown in scoped example | 2 | Not assigned | 2 |
| Firm constraints | Satisfied in specified layout | Reading layout only; workflow deferred | Satisfied in specified layout |
| Trial-default exceptions | None | Not assessed | None |

Counts cover only the illustrated roles/tasks, not the eventual complete menu.
Opening an expander/menu does not count; selecting context or an item does. Task-local
navigation is not automatically free: its selection counts even without a page reload.
No nesting is concealed by renaming a destination list.

These traces identify expected recovery and scale behavior. They do not prove
90-action search, 50-person placement, keyboard usability, server reconciliation,
accessibility or performance in a working application. The static visual reference
uses a few representative rows and cannot close those acceptance checks.

## Decisions emerging from this trial

- Keep task-local item navigation subordinate within the work area; it is distinct
  from flat application destinations.
- Further review-workflow planning is deferred until a concrete need arises;
  retained comparison material creates no new scope or authority.
- Treat a bulk selection as one subject and always expose its full membership.
- Required evidence belongs alongside the task and remains reachable in the same
  flow at narrow widths; it must not require leaving the decision.
- No numeric exceptions or new page shapes are justified by E1/E3 so far. E2 cannot
  establish navigation compliance until its workflow is scoped.

Participants and shared controls are accepted for now. Action navigation and the
view/edit approach are accepted; overall intention and region separation have been
added in response to feedback. The comparison study is retained as reference only.
The planning session is closed; no review-scoping discussion is queued.

### Reference rendering check

The first reference rendering check (before the latest revision): Chromium loaded
the static reference without page errors. At 1280, 768, 390 and
320px viewport widths, the document had no horizontal overflow. A native expander
opened successfully, and the desktop review layout was visually inspected. These
bounded checks establish rendering only; no application tests were run for these
documentation/design changes.

After feedback, the revised reference was checked again at 1280, 768, 390 and 320px:
no document horizontal overflow or browser page errors. The overall-intention
expander opens and editing its local textarea leaves the action textarea intact
(this is not a server-save test). Player/review screenshots were visually inspected.
Component colour and radius declarations were checked for shared-token use; local
document links resolve. No production application styles were changed.
