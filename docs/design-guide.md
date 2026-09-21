# Application design guide — session baseline (revision 5)

Status: design direction agreed in the 2026-09-15 session; example layouts and
visual reference remain proposals. No application implementation is claimed.
Revision 5 closes the planning session after consistency review. Participant and
shared-control patterns are accepted for now. Further review-workflow design is
deferred until a concrete need arises; it is not a planned feature or next task.
The retained comparison study illustrates presentation only.

Delivery update (2026-09-21, B-17): implementing this direction in existing templates
and resolving the usability findings is the next session's work, before 1D-2.
No template migration is claimed. Preserve proposed/accepted distinctions and settle
open lifecycle policies explicitly. The later Execution Context proposal is not
adopted; interpretation confirmation remains a separate future experiment.

Purpose: give existing and new pages consistent navigation, interaction and visual
rules. Keep the guide small enough to use during every UI change. Source:
[usability review](phase1/usability-review-2026-09-15.md).

## 0. How to use this guide

This guide defines **structure, responsibilities and constraints**. It deliberately
does not list specific pages, menu items or header contents; those are discovered
through example pages and recorded in the
[navigation inventory](navigation-inventory.md) (template in Appendix A).

Boundaries:

- **Requirements and the [decision log](decisions.md)** govern authority, lifecycle
  and domain behavior. This guide describes how state, authority and consequences
  are *shown*; it cannot silently change what they *are*.
- **The navigation inventory** records proposed and implemented placement separately,
  with the rationale for each item.
  Moving an item between regions updates the inventory, not this guide.
- **This guide** changes only when a principle, region responsibility, constraint
  or shared pattern changes.

Terms: *must* marks a constraint a design has to meet; *should* marks a default
that may be departed from with a recorded reason.

## 1. Guiding principles

1. **One coherent task at a time.** The work area has one primary subject and one
   primary action per task region. Related objects may serve that task; task-local
   navigation and consulted material remain visibly subordinate. This does not
   prescribe a sequential one-record-at-a-time flow or a multi-panel dashboard.
2. **Make the next action apparent.** A user can identify where they are, what they
   can do and what needs attention without instructions or a supplied URL.
3. **Shallow and visible.** Permitted work is reachable in a few predictable steps
   and never depends on hidden, deeply nested or undiscoverable controls.
4. **Protect authored work.** Saving one section, navigating, receiving an update or
   encountering an error must not silently discard other edits.
5. **Make state and consequences visible.** Distinguish unsaved text, saved draft,
   submitted content, proposed revision and effective content where people work.
6. **Keep content primary.** Use readable prose and compact summaries. Put metadata,
   technical identifiers and historical detail in supporting positions.
7. **Same task, same pattern.** Navigation, save/cancel, feedback, comparison and
   recovery behave the same across roles and pages.
8. **Design for the working volume.** Check layouts with long text, many actions and
   large rosters; a two-record example is insufficient.

## 2. Application shell

### 2.1 Regions by responsibility

Every signed-in page uses the same shell. Regions are defined by the question they
answer, not by their contents or visual form. Whether a region renders as a
sidebar, top bar, rail or tab strip is an implementation choice recorded in the
inventory.

| Region | Answers | Holds | Must not hold |
| --- | --- | --- | --- |
| **Persistent shell** | "Who am I and how do I get home?" | Home link, identity, account and sign-out; anything that applies regardless of context. | Game- or task-specific items. |
| **Context region** | "Where am I, and in what state?" | Information that scopes everything beneath it and changes rarely during a task, with a switcher only when a real choice exists. | Task destinations or actions on content. |
| **Destination region** | "What can I work on here?" | The places a user moves between within the current context, with the active one marked and attention indicators in text. | Actions that change data; nested menus. |
| **Work area** | "What am I doing right now?" | One coherent task: its primary subject, state, actions and subordinate task-local navigation. | Unrelated tasks or competing primary subjects. |
| **Supporting region** (optional) | "What helps me do this?" | Material the user consults: discussion, guidance, history or evidence. Required material is available beside the work without navigating away. | The primary subject or its commitment controls. |

An illustration of *one possible* arrangement (not a commitment):

```
┌───────────────────────────────────────────────────────────┐
│ Persistent shell                  Context region          │
├─────────────┬───────────────────────────────┬─────────────┤
│ Destination │ Work area                     │ Supporting  │
│ region      │ Title · state                 │ region      │
│             │ One task, one primary action  │ (optional)  │
└─────────────┴───────────────────────────────┴─────────────┘
```

### 2.2 Placement tests

When it is unclear where an item belongs, apply these in order:

1. **Does it apply everywhere, regardless of context?** → Persistent shell.
2. **Does changing it change what everything else on the page means?** → Context.
3. **Is it a distinct place for a task within this context?** → Destination.
   Selecting records within the same task is task-local navigation in the work area,
   not a separate destination.
4. **Is it acted on or read as the point of the visit?** → Work area.
5. **Is it consulted to inform work on the primary subject?** → Supporting. If the
   decision depends on it, make it available alongside the work without navigating
   away. On narrow screens, place it in the same task flow with a clear return to
   the decision. Required evidence must never become an optional discovery.

An item that passes more than one test is usually two things (for example, an
indicator of current state is context, while the page for managing that state is
a destination). Split it rather than compromising on a region. Record the test
result in the inventory.

### 2.3 Navigation constraints

There are two tiers. Firm constraints express the app's goals and have no per-page
exceptions. Numeric trial defaults are tested through examples.

| Firm constraints | Trial defaults |
| --- | --- |
| No submenus, flyouts or collapsible destination groups; non-interactive group headings are allowed. | At most 3 navigation steps from home. |
| No permitted action reachable only through hidden or icon-only controls. | At most 1 drill-down level below a destination. |
| Current context and location identifiable at a glance. | At most 7 destinations per role and context. |
| Drill-downs name their parent (for example, “All actions”). | Five starting page patterns in Section 3. |
| Dialogs do not navigate or open further dialogs; no nested tabs. | |

A **navigation step** changes location or context. Opening a menu, switcher or
expander is not a step; choosing a different location/context is. Count substantive
changes, not clicks or URL segments. Context and location need not stay fixed while
scrolling, but must be immediately identifiable on entry or when navigation is used.

Record a trial-default exception in the inventory with the example that justifies
it. Review exceptions together at each design review; if they recur or accumulate,
revise the shared default rather than leaving a growing list of local exceptions.
Changing a firm constraint requires an explicit guide-level design decision.

Additional shared rules:

- **Focus:** one coherent task, one primary subject and one primary action per task
  region. A selected comparison is primary; its action list is task-local navigation;
  its evidence is supporting material. These are not competing destinations.
- **Stable location:** an item has the same region responsibility for every role
  that has it. Responsive layouts may change geometry, not responsibility. Placement
  changes update the inventory rather than being invented page by page.
- **Direct links:** task and item views have stable links that restore their
  game/team/turn and task context under current authorization. Links do not grant
  access. Browser Back and named parent links retain useful list/search context.
- **Dialogs:** reserve them for confirmation, loss-of-work warnings and short focused
  inputs. They have no internal navigation and do not open another dialog.
- **Tabs:** at most one set of views of the same subject inside the work area; no
  nested tabs or tabs containing destination lists.

### 2.4 Visibility and authority

- **Unauthorized:** absent. Destinations and actions a role may not use are not shown.
  Administrative authority does not imply access to private player or adjudicator
  content.
- **Temporarily unavailable:** visible, disabled and explained, including how or when
  it becomes available ("Available when submissions open").
- **Permitted:** visible and labeled. Permitted actions must not depend solely on
  hover, right-click, keyboard shortcuts, icon-only controls or overflow menus. An
  overflow menu may duplicate a rare secondary action only when it also has a
  visible labeled path. Rarity does not create an exception.
- **Attention:** items needing a response show a text indicator in the destination
  region and a persistent message in the work area; colour supplements, never replaces.
- **Labels:** destination labels name places; button labels name actions. Two labels
  must not appear to lead to different places while opening the same page.

## 3. Page types

These are starting patterns, not an exhaustive classification. Density follows
the task, which implements the agreed **mixed by task** direction: working and review pages are compact and
content-focused; setup guides users through prerequisites, choices and outcomes.

| Type | Purpose | Work area shape | Density |
| --- | --- | --- | --- |
| **Overview** | Orient and route to attention items | Status summary; each attention item links directly to its work | Compact |
| **Workspace** | Author and maintain content | Compact task navigation and a primary subject in view/edit mode | Compact |
| **Review** | Inspect content and evidence; decide when the scoped workflow calls for it | Primary review subject with supporting context; compare versions when relevant | Compact, wide |
| **Roster** | Find and manage records | Searchable, filterable compact list; selected set or individual detail | Compact |
| **Setup** | Configure with prerequisites | Visible prerequisites, progress and outcomes; revisit completed sections and skip inapplicable steps | Guided |

List-and-item behavior (Workspace, Review, Roster):

- The list is searchable when it can exceed roughly one screen. Search and filters
  are visible, not hidden behind a toggle.
- Opening an item replaces the list in the work area, or on wide screens appears in
  an adjacent pane *within* the work area. It never becomes a second destination
  region.
- An open item offers previous/next and a named back link, so users can move through
  many items without returning to the list. Returning restores list position,
  search and filters.

A genuinely new page shape is added here with its purpose and shape after an
example demonstrates the need. Related bulk operations may treat the selected set
as the primary subject. Do not force a poor fit or leave one-off shapes unrecorded.

## 4. Editing and collaboration

- Existing items open in readable view mode; **Edit** opens a clearly bounded editor.
  Save and Cancel sit together and name their scope. New items open as a labeled
  creation form with an explicit create command.
- Initial proposal: explicit saving with visible unsaved/saved state. Autosave is a
  separate design choice and must not be inferred from an update notification.
- Saving never implies a later lifecycle step (such as submission) and never
  silently saves or discards other editors. Cancel discards only its editor's
  changes, with a warning when changes exist.
- Navigation, reload, partial updates and ordinary form submissions must protect
  dirty input by retaining it recoverably or warning before loss. Do not assume
  browser unload warnings cover every path.
- Incoming changes from others never overwrite unsaved local text. Show a clear
  update or conflict indication, preserve attempted input and offer explicit recovery.
- Conflicts explain who changed what, using named versions and a readable comparison,
  brought into view with clear resolution actions.
- Discussion and its composer stay together, in the work area or supporting region
  per the placement tests. Comment text is primary; author and readable time secondary.
- Ordinary working pages omit passive revision lists; authorized audit and recovery
  views preserve history.
- Summaries expand independently. Changing display order is distinct from changing
  saved order; controls must say which they affect.

## 5. Feedback, forms and consequential actions

| Situation | Shared pattern |
| --- | --- |
| Successful save/create | Brief accessible confirmation naming what changed, near the task; preserve focus and position. A transient toast may supplement persistent state, never replace it. |
| Invalid input | Summary plus specific field errors; retain non-secret values, labels and control types; explain how to correct. |
| Commitment (send, submit, release) | Before: state recipient, content affected and resulting state. After: show the authoritative result. |
| Rejection or required response | Persistent message beside the affected item, with reason and next action; indicator in the destination region. |
| Confirmed failure or conflict | Visible explanation, preserved input and a safe retry or recovery path; never imply success before confirmation. |
| Unknown write outcome | Say that confirmation was lost and the operation may have completed; preserve input and reconcile its status before a fresh attempt. Do not present it as confirmed failure. |
| Empty list | Explain what belongs here and offer the authorized next action. |
| Unavailable action | Give the reason and path to availability; never show empty selectors with apparently usable submit buttons. |
| Error page | Keep the shell and orientation; offer a safe route back to authorized work. |

Consequential writes need backend support to determine whether an operation landed,
for example a client-generated request key and an authorized result lookup or
idempotent retry. Reuse the operation identity during reconciliation; a new key
could duplicate a completed operation. Existing workspace request-key support must
be checked per operation; this rule does not imply all administration writes have it.

- Use human-readable names, never required internal IDs. Dependent selectors offer
  only valid choices and clear invalid selections when their parent changes.
- Label required and optional fields consistently. Explain audience and effect where
  not obvious, especially who can see the information.
- One visually primary action per task region; secondary actions are quieter.
  Destructive actions name the affected item and consequences. Reserve confirmations
  for consequential actions or loss of work.
- Comparisons name changed fields prominently, retain the entire action context and
  show complete base/proposed text by field. Unchanged fields remain readily readable.
  Mark a cleared field explicitly and retain its base text. Multiple paragraph edits,
  full replacements and removed content must remain understandable without word-level
  highlights; highlights are supplementary. Narrow layouts retain version labels.
- A comparison pattern does not define an approval workflow. Further design of
  review roles, routing and decisions is deferred until a concrete need arises.
  This session creates no new review feature, role, permission or implementation
  prerequisite. Existing submission/amendment behavior is unchanged.
- Overall intention is package-level authored content with its own visible location
  and save boundary. Keep it available while editing actions; never conflate it with
  the action's Intent of Action. Saving it preserves dirty action editors.
- Supporting regions do not imply chat or live collaboration. Include only scoped
  aids. Existing team comments do not establish a chat interface or its placement.
- Distinct lifecycle operations remain visually and verbally distinct. Completing
  one must not suggest that a different, later operation has occurred. Which
  operations exist is a domain decision, not a guide decision.

## 6. Minimal visual baseline

Proposed starting values; refine through representative screens rather than branding.

- System sans-serif throughout, approximately 16px body text, 1.5 line height.
  Preserve authored paragraphs; monospace only for actual code or technical data.
- Neutral page background, plain content surfaces, dark text and one restrained accent
  for links and primary actions. Status always includes text.
- Navigation and supporting regions use distinct quiet surfaces and visible borders;
  the primary work surface remains dominant. Active location is clearly marked.
  Distinction survives reflow and does not depend on colour alone.
- Colours, typography, spacing, borders, radii and state appearances use semantic
  tokens in one shared source. Component styles consume those tokens without local
  palette/shape literals or inline overrides. A future dark theme overrides the
  token values, not each component. Layout breakpoints remain centralized separately.
  The reference uses [design-reference.css](design-reference.css). Adopt the same
  single-source structure in production when implementing these patterns; this does
  not claim the current application has been migrated or that a dark theme exists.
- Consistent heading hierarchy; spacing scale of 4, 8, 12, 16, 24 and 32px. Group by
  task with spacing and subtle boundaries, modest corner rounding.
- Prose uses a bounded line length; workspaces and comparisons may use more width.
  Do not force every page into one narrow column.
- Compact rows for lists; expandable summaries for long items. Comfortable control
  targets and wrapping rather than shrinking text to fit more records.
- Links look interactive; expanders have indicators and visible hit areas. Hover,
  focus, selected, disabled and expanded states have consistent treatments.
- On narrow screens, navigation regions may collapse behind a single clearly labeled
  control, with current context and location identifiable at a glance. Opening that
  control does not consume a navigation step; choosing a destination does.
- Keyboard access, visible focus, semantic labels and announced feedback throughout.
  Check zoom and narrow layouts; no horizontal scrolling for ordinary prose or forms.
- Establish a small shared visual reference for buttons, fields, notifications,
  rows and expanders from the three examples. Once reviewed, it supplies the shared
  implementation baseline rather than each page inventing its own variants.
- Locally available assets and shared styles/components only. New dependencies must
  meet the project's offline packaging rules.

## 7. Method for designing a page

Before implementation, write a short page specification:

1. **Role and task:** who uses it, what they accomplish, how they arrive.
2. **Page type:** which type from Section 3; if none fits, why.
3. **Placement:** apply the Section 2.2 tests to the page and its major elements;
   add or update inventory rows.
4. **Context and authority:** scoping context, visible content, permitted,
   unavailable and unauthorized actions.
5. **Layout:** work area regions, primary action, supporting detail and exit route.
6. **Constraint check:** firm constraints, then trial-default measurements of steps
   from home, drill-down depth and destinations per role/context. Record justified
   exceptions with their example.
7. **State table:** empty, editing/dirty, saving, confirmed success/failure, unknown outcome, invalid, conflict,
   read-only and denied as applicable, with the next action for each.
8. **Data boundaries:** what each save changes, what commitment freezes, what others
   see, and how concurrent changes and unsaved text are handled.
9. **Walkthrough:** realistic data and a short unaided task demonstrating success,
   recovery, keyboard use and narrow-screen use.

Reuse an existing pattern first. Add a shared pattern here only when no existing one
serves the task. Record consequential domain choices in the decision log. Adopt
patterns incrementally as pages are corrected or extended; avoid a separate
all-pages visual rewrite.

## 8. Planning session record

### 8.1 Examples

The session produced a player workspace, a comparison presentation study and a
participant roster, with a shared visual reference. The examples distinguish shown
states from written scenario traces. Full 90-action and 50-person workflows, conflict
recovery and unaided use remain unverified. The comparison study is retained as
reference material; no further review-workflow planning is scheduled.

### 8.2 Questions for future changes

Apply these when a concrete UI task needs design; they are not an immediate backlog:

- Which items are true context, and which do users switch between often enough to be
  destinations?
- How many destinations does each role need per context? Does it stay within the limit?
- Does any real workflow break the depth budget? If so, is the budget or the
  structure wrong?
- Is discussion used beside the work (supporting) or as its own place (destination)?
- Do the five page types cover the examples without strain?
- Do the proposed numeric limits produce useful pass/fail signals?

### 8.3 Separate domain questions

Carry these separately and resolve them before dependent implementation: revision
approval versus immediate effect; deadline and lock behavior; pushed saved updates
versus simultaneous editing; display sorting versus saved ordering; and controlled
account reactivation and team changes. The usability review records these as
unresolved. This guide selects none of their policies.

### 8.4 Session outputs

- Agreed principles, region responsibilities, firm constraints and trial defaults.
- Confirmed or revised page types and shared interaction patterns.
- Player/participant examples, a retained comparison study and a small shared visual reference.
- Initial navigation inventory entries with placement rationale.
- A short decision list.

Outside this session: further review-workflow design, detailed branding, animation,
exhaustive component catalogues, final navigation contents and live-editing technology.
Review design resumes only when an actual task establishes the need.

## Appendix A. Navigation inventory template

Kept in [navigation-inventory.md](navigation-inventory.md), separate from this guide.
Initial examples and design checks: [design-examples.md](design-examples.md).

| Item | Context / scope | Region | Placement rationale | Roles | Page pattern | Design status | Implementation status | Trial-default exception / evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| *(example)* | Selected game/team/turn | Work area: task-local navigation | Selects an action within the task | Player | Workspace | proposed | not implemented | None; link to example |

Design status: **proposed** (from a specification), **trialed** (exercised in an
example or walkthrough), **settled** (accepted for current use). **Deferred** records deliberately paused
work with its trigger for reconsideration; it is not an implementation commitment. Record
what kind of trial occurred; a document or mockup trial is not a live usability pass.
Implementation status is independent: **not implemented**, **partial** (describe
what exists), or **implemented** (link evidence). Placement changes record the
previous region and the reason. Example counts are partial inventories, not proof
that every future destination fits the default.

## Appendix B. Page review checklist

- [ ] Uses a starting pattern or records a justified new shape
- [ ] Every element placed by region responsibility; inventory updated
- [ ] Trial steps/depth measured; exceptions linked to examples; drill-down names parent
- [ ] Trial destination count measured for each role/context; no nested destination menus
- [ ] One coherent task, primary subject and primary action per task region; aids subordinate
- [ ] Context and current location identifiable at a glance
- [ ] No permitted action depends only on hidden or icon-only controls
- [ ] Unavailable items explained; unauthorized items absent
- [ ] Dirty input protected on every exit path; conflicts preserve input
- [ ] State table covered, including empty, invalid, conflict, denied and unknown outcome
- [ ] Status carries text; keyboard, focus, zoom and narrow screen checked
- [ ] No domain policy decided in the UI that is not in requirements or the decision log
