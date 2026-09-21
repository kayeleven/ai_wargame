# Guided application verification — 2026-09-15

## Delivery status update — 2026-09-21

The subsequent design session is complete; applying the revised design to existing
application templates and resolving these findings remain outstanding. The owner
has designated this work as the next session, before 1D-2. Use the workstreams and
acceptance checks below together with the [design guide](../design-guide.md),
[examples](../design-examples.md), and [navigation inventory](../navigation-inventory.md).
See the [roadmap](../../roadmap.md#immediate-next-work--usability-remediation-and-template-implementation)
and [B-17](../decisions.md#b-17--usability-delivery-and-agent-played-research-games--2026-09-21).
The original findings and observed results below remain historical evidence;
this update claims no fixes or new verification. The coworker's Execution Context
alternative is not the implementation baseline. Open lifecycle policies below are
not resolved by the design samples.

## Consolidated assessment and delivery plan

Walkthrough closed after the memory explorer blocked the final step. This document
is the consolidated findings artifact: workstreams below, original user
comments by step, screenshots, and traceable findings/acceptance checks. The user's
instruction during that review was to record issues for future fixes, not implement
them during the walkthrough; the delivery status above records the subsequent plan.
Priorities are recommendations; policy questions remain explicit.

### Assessment

The exercised draft, persistence, concurrency, submission-authority and amendment
transitions worked with guidance. The application is not ready for an unaided
player/adjudicator pilot: missing role navigation and logout, silent loss of unsaved
text, weak state/decision feedback, and poor review comparisons are significant
obstacles. Responsive stacking worked. Passing workflow steps do not establish
overall usability, full-game readiness, capacity, or security qualification.

### Recommended workstreams, in order

| Order | Workstream | Included findings | Reviewable outcome |
| --- | --- | --- | --- |
| 1 | Protect input and restore access to basic tasks | UX-37, UX-01/02/26/27/47/48, BUG-01 | No silent loss of unsaved work; shared signed-in header/account/logout; role-aware game/workspace entry; recoverable error pages; fixture explorer works after game activation. |
| 2 | Design and deliver submit/review/revise as one workflow | UX-38/43–46/49–51; status patterns UX-09/15/16/24/32 | Agree lifecycle policy, then deliver readable package states, explicit revision mode, changed-action summaries and old/new comparisons, prominent decisions/reasons, and consistent outcome messages. Validate both rejection and acceptance paths. |
| 3 | Make the team workspace usable at realistic volume | UX-28–31/33–36/39–42 | Readable view/edit modes, collapsible actions, clear sorting versus saved ordering, colocated discussion, protected incoming teammate updates; move passive history out of the normal player workspace. |
| 4 | Consolidate account and participant administration | UX-03–08/10/11/17–23 | Compact searchable/sortable/paginated rosters, bulk local-account creation and placement, readable attribution, explicit deactivation/reactivation and user management, clear field-specific recovery. |
| 5 | Replace technical game setup with guided configuration | UX-12–14/25 | Backend-generated identifiers, explained required/optional fields and audiences, game/team selectors and guided scenario setup; remove confusing duplicate navigation. JSON remains temporarily acceptable. |
| 6 | Repeat focused acceptance and complete deferred checks | All relevant gates below | Fresh unaided player/admin/adjudicator walkthrough, automated regressions for data protection and authorization, realistic 50-user placement and 90-action usability checks, then previously blocked memory review. |

These workstreams consolidate 51 UX findings; UX-51 is the overarching redesign,
not an additional isolated feature. Repeated feedback on notifications and
navigation should be implemented through shared patterns. Keep authoritative
history and effective-version integrity while changing their presentation.

### Decisions required during design

- **Revision policy:** does an open-turn revision become effective immediately or
  still await adjudicator acceptance? The user requested Submit revision wording
  and clear status; immediate effect was not explicitly settled.
- **Deadline/lock policy:** user expects no submission after locking/deadline;
  existing behavior deliberately permits late submissions in the active turn.
  Reconcile contracts and roadmap, then enforce the chosen policy consistently.
- **Collaboration:** user wants pushed changes, ideally simultaneous/live editing.
  Choose an approach that preserves unsaved work and handles conflicts/reconnects;
  do not select technology solely from the request for live updates.
- **Administration:** LDAP is an intended future integration; local bulk creation,
  credential management and reactivation are still required. Specify restored
  access behavior and the controlled Add team lifecycle.
- **Action sorting:** distinguish local display sorting from changing the submitted
  action order. The user requested sortable actions, without specifying semantics.

### Verification outcomes and limits

**Observed working:** account creation persisted across refresh/logout/login;
game creation, assignments and activation reached active turn 1; saved draft
revision persisted; concurrent edits were detected and combined recovery worked;
ordinary member lacked Submit; designated submitter submitted; post-submission
draft edits left the official package unchanged; rejection was visible and a later
accepted revision became effective version 3; narrow layouts stacked correctly.

**Observed failures or blockers:** unaided role/workspace navigation, player logout,
silent unsaved-input loss, raw/dead-end error pages, difficult conflict/revision
review, missing outcome feedback, and fixture explorer failure after activation.

**Not fully verified:** action reorder/removal and historical recovery, submitter
replacement, explicit original-version retention after final acceptance, validation
recovery beyond reported cases, keyboard focus/order, exact 200% zoom behavior,
cross-team URL isolation (skipped at user preference), memory search/navigation
(blocked), live updates, large rosters/action volumes, multi-turn gameplay, backup
restore, offline setup, performance or capacity. A Red adjudicator request returned
Not found; that alone is not a complete authorization test. Refer to historical
automated verification separately; it was not rerun as part of this walkthrough.

### Changes made during review

At the user's direction the disposable development database was rebuilt without
a backup, current fixtures loaded, and the application restarted. A missing
administration-model import in cli.py was corrected to unblock fixture loading;
both loads, Ruff and mypy passed. That pre-existing setup repair remains. The later
attempted explorer filter was reverted; no explorer or UX redesign is implemented.

## Purpose and recording method

Walk through the delivered application with the project owner. Preserve their
feedback per step, then consolidate findings into a prioritized implementation
plan in this document. User observations and assistant findings remain distinct.
No step passes merely because automated tests previously passed.

For each step record: outcome (pass / issue / blocked / skipped), original user
comments, reproduction details, expected and actual behavior, and impact.
Screenshots may be supplied in the conversation. Never record passwords or secrets.

## Walkthrough queue

1. Landing page and first impressions — feedback recorded; initial database blocker resolved.
2. Sign-in and workspace discovery — login/admin access verified; usability issues recorded.
3. Test-game setup, roles and membership — completed through activation; game active on turn 1; usability findings recorded.
4. Player workspace discovery (4a) failed unaided; assisted access succeeded. Intention/comment saved (4b), action created (4c), saved revision survived refresh (4d). Unsaved description lost without warning when intention was saved and page refreshed.
   Two-session conflict detected (5a), but message was offscreen and recovery unclear. Conflict recovery passed (5b). Submission authority passed (6a); version 2 rejected (7a), corrected version 3 accepted and effective (7b). Red adjudicator access returned Not found; targeted cross-team URL check skipped (8a). Next: keyboard/readability (8b).
5. Unsaved-input behavior and validation recovery.
6. Shared editing, conflicts, comments and history.
7. Submission authority and immutable submitted versions.
8. Amendment rejection and acceptance.
9. Cross-team access and submitter replacement.
10. Keyboard, zoom, narrow-window and long-content usability.
11. Fixture memory exploration, if loaded and available.
12. Consolidation and prioritized planning backlog.

Adjust the order as needed for available accounts and game data. Missing features
are scope gaps, not failed checks of delivered behavior.

## Step 1 — Landing page

Instructions: open http://127.0.0.1:8000/; inspect the page before signing in.
Assess whether purpose, next action and navigation are clear. Note misleading copy,
missing information, layout/readability concerns and anything unexpected.

User outcome: landing page accessible; database-backed checks blocked by readiness.

User comments:

> Is the database and app running on the labvm01 machine? That machine is headless,
> but I have set up port forwarding via my ssh.
>
> The link you provided is to localhost:62139 - it loads on my machine without
> forwarding enabled, but the database is unavailable.

Connection context: user has an SSH alias `labvm01-web` forwarding local port
18000 to VM loopback port 8000 through a jump host. No credentials recorded.

Assistant verification: host identifies as labvm01; Uvicorn listens on loopback
8000 and PostgreSQL is running. Readiness returns schema mismatch. The browser's
62139 URL differs from the user's explicitly configured SSH forwarding port.
Additional user feedback:

> 18000 works.
> Sign in & Administration links navigate to a log in page. (the same regardless of link clicked)
> Explore memory gives a database error
>
> Try the form demonstration shows a template form, api documentation takes me to the standard docs page.

Assessment: SSH-forwarded access confirmed. Sign in and Administration both lead
to login while signed out; this observation is not yet classified as a requested
change. Memory exploration is blocked by database readiness. Demo and API docs
navigation work as observed. No user preference about visual design recorded yet.

## Step 2 — Sign-in and administration

User outcome: login and administration access succeed; issues with feedback,
navigation state, sign-out placement and action discoverability.

Original user comments:

> Logged in as administrator. After login the page stayed on what I assume is the 'home page' or the landing page with the link to sign in and administrator still showing. There was no indication that I had logged in successfully.
> Clicking 'Administrator' did take me to the administrator page. Clicking 'Sign in' did nothing - no prompt, no redirect)
>
> I included a screenshot of the admin page. The sign out button is in an awkward location - I would expect it to be smaller and in the header on the right, or nested under a menu of user/system tasks.
> The links (create local user, create configured game, etc.) are not clear that they are actions or links - they appear as unfinished areas of the page.
> Related - the cursor changes to 'Text select' icon when hovering over the labels vice 'Link select'.

Screenshot: [Administration after login](evidence/usability-2026-09-15-admin.png).

Assistant source inspection: successful login redirects to `/`; authenticated
GET `/login` also redirects to `/`, explaining the apparent no-op. The landing
page always displays Sign in. The administrative action labels are native
`details`/`summary` expanders. The screenshot supports the placement and visual
hierarchy findings; the cursor behavior is user-reported.

## Step 3a — Create first test player

User outcome: pass. Creation persists through refresh and logout/login. User also
tested deactivation and attempted recreation; no reactivation control found.

Original user comments:

> 3a - pass
> Form opens - there is no indication of where I need to click to expand the form. It works as expected by clicking on the text, but it also expands when I click far to the right of the text. There is likely a non-indicated region.
>
> The user was maintained with refresh and logout/login.
> The 'deactivate ' buttons are oversized. With 2 users (admin and the test user) the list is rapidly growing in vertical size. With 100s of users the list will be untennable and the options that the admin needs (create user configure, etc) will be at the bottom of the list and need scrolling to see without any indication that there is anything aside from more user names below the page.
> Deactivate is an unclear action - does that delete the user, make their account inactive, ? Clicking deactivate marks the user as 'deactivated' but there is no action to 'reactivate' the user.
> Trying to recreate that user was precluded "This identifier or assignment already exists".

Assistant source verification: deactivation retains the user record, marks the
account inactive, revokes sessions and reconciles affected team state. Username
uniqueness still applies. No reactivation service/route/control was found. The
administration template places account-creation and game-configuration expanders
after the full user list. Large-user-list concerns are user projections from two
users, not a completed large-volume test. The exact deactivated username was not
explicitly stated; likely the newly created test user.

Next instructions: create distinct active walkthrough accounts blue_submitter,
blue_member, red_player and adjudicator; do not assign permissions yet. Retain the
deactivated account as evidence rather than changing its state behind the UI.

## Step 3b — Repeated account creation

User outcome: pass. Remaining test-account creation reported successful.

Original user comments:

> Passes.
> -the goal is eventual tie in to LDAP. But for username/password accounts there should be a bulk create/import ability.
> The list expands when the user is created (some visual feedback) but there should be a toast saying the account was created (or failed).
> The User list is not sorted (it keeps oldest on top) this is fine for a handful of users, but is not helpful for when there are hundreds of accounts to sort through.
> There is no mechanism that I can see to allow for managing the users (reset password, update name, etc.)

Assistant clarification: local password reset exists as an operator CLI command,
but the administration UI offers no password-reset or name-editing controls.
LDAP is the user's intended future integration, not an implemented capability or
a reason to omit local-account management. Bulk account import is distinct from
the roadmap's game-move import workflow.

## Step 3c — Draft game creation

User outcome: game record appeared under Games; success feedback was unclear.
Creation reported successful by observation, not an explicit user pass rating.

Original user comments:

> Sable identifier should be created in the backend - not a user defined value.
> The content that should go into each field is unclear. Title is self evident. Is the description just a text display of what the game is? Does it carry any weight into the game later?
> Are public rules for the players or for the AI? Are they required or not? (similar for every field there is no indication on what is needed vs optional)
> The structured configuration (JSON) is okay for now - it cannot be the long term solution.
>
> There was no indication that the game was created or if it failed. (I did eventually see the new record in 'Games'. )

Assistant clarification: current game creation requires identifier, title and a
valid structured configuration. Public description, public rules and briefing
default to empty strings. They are stored and exposed by the game's public-info
endpoint, not currently used to execute effects or drive AI (AI is not implemented).
The separate JSON `rules` list is currently mandatory; the roadmap plans to make
it optional for open-world scenarios. The UI must explain this distinction and
future premise/rule usage rather than imply all text has the same authority.

User accepts JSON temporarily, not as the eventual facilitator experience.
Next: assign adjudicator role and blue/red team memberships; inspect the resulting
game grants before activation.

## Step 3d — Assign participants

User outcome: game-role assignment worked, without clear confirmation. Membership
completion remains unconfirmed; invalid game/team inputs were deliberately tested.

Original user comments:

> adding the user to game role worked - but there was no indication. The form closed and the page refreshed (I think) it was an abrupt jump to the top of the page.
> Assigning team membership is poor UX. 'Game identifier' requires me to type in the identifier, it should be a dropdown of available games.
> Same with team identifier - a list of existing teams or 'add new'.
> There is no indication of who has been assigned to the game and who has not. An admin adding 50 people to a game has to track who they've done and who they haven't and needs to coordinate this across two actions (add user, and then assign user).
> Typing in a bad game identifier causes an error page ({"detail": "Not found"}) instead of a clear error/message.
> Trying to add a user to an invalid team gives a 'review you input' form, but the user_id shown is not the user_id I selected, it appears to be a hashed key of the user. The form also doesn't make it known what was wrong. (message says Unknown configured team or authority)

Assistant source verification: the user selector displays a username but submits
the user's internal UUID. Generic error rendering replaces named controls with
textareas containing raw posted values, exposing that UUID instead of the username.
This explains the apparent identifier change; no evidence yet of a different user
being assigned. A missing game raises LookupError, handled as a JSON 404 rather
than a recoverable form error. Membership validation combines bad team and bad
authority into one message. Successful commands redirect to /admin, consistent
with the reported closed form and jump to page top.

Existing assignments can be inspected on the game's details page, but are not
shown at the point of assignment. User's 50-person workload concern is a design
assessment, not a completed bulk-assignment test. Adding new teams is a requested
workflow; current roster/controller revision limitations must be respected in its
future implementation.

Next: inspect the game details and record which expected memberships/role are
present; add only missing memberships through the existing form before activation.

### Step 3d follow-up — Saved membership review

Original user comments:

> The membership list is hard to navigate. The different user blocks are not demarked so actions are unclear if they are for the above user or the below user. There is no logical grouping or order (or if there is it is unclear with the limited users in the game).
> The 'replacement teammate' is empty for Red (there is no other red members) but it is confusing that the dropdown even shows.
> Adjudicator is also showing the UUID vs the display user_id. (under 'granted by')

Screenshot: [Memberships and game roles](evidence/usability-2026-09-15-memberships.png).

Visible evidence: blue and red both Ready; blue_submitter is blue/submitter,
blue_member is blue/member, **red_submitter** is red/submitter, and adjudicator has
the adjudicator role. Use red_submitter in subsequent instructions (the earlier
suggested red_player name does not match the account shown in the screenshot).
The grant attribution is the granting administrator's internal UUID, not a changed
identity for the adjudicator. Red has an empty replacement selector and an enabled
Replace submitter button. User blocks lack clear visual separation.

Next: activate the configured game and verify active status / turn 1, then begin
player-workspace checks. Memberships need no further changes for this setup.

## Step 3e — Activate game

User outcome: activation succeeded; game shows active and turn 1. Outcome feedback
and duplicated navigation remain unclear.

Original user comments:

> There was no indication the 'activate after prerequisite check' did anything. The form collapsed - I can see that the game shows active now.
> The game does show it is on turn 1.
> The 'Configuration history and grants' link takes me to the same game page as if I selected it under 'games'. it is unclear if this is supposed to show me something different or why it exists here.

Assistant source verification: both links point to the same `/admin/games/{id}`
page, without an anchor or alternate view. Successful activation redirects to the
main administration page; the activation button disappears because the game is
no longer draft. No separate outcome notification is provided.

Next: sign out as administrator, sign in as blue_submitter, assess workspace
discovery, then use `/play?game_id=ux-review` as an explicit assisted fallback.
Do not count navigation by supplied URL as successful unaided discovery.

## Step 4a — Player workspace discovery

User outcome: logout/login successful; unaided discovery blocked, direct-link
access successful. Access denial for the administration page was clear but lacked
navigation. User tried selecting turn 2 with Open workspace.

Original user comments:

> Log out/log in was successful.
> The same page (landing page) was visible as when I logged in as the administrator. There is no link to a user page, the game page, or any indication of what to do once signed in.
> Clicking on 'administrator' gives a clear error (but the error page has no navigation).
> I had to use your link to get to the player page.
> The 'team' is a dropdown - for most players this is confusing, they are on one team. For game admins it could make sense (view as this team) but as shown it is unclear why this is a selectable field.
> Open workspace was confusing at first - what does it do? I figured it out when I changed the turn to 2 and tried it.
>
> The workspace is unimpressive - okay for the beta view, but lacking cohesion and navigability.
> There is a 'discussion' section but no way to start a conversation.

Screenshot: [Player administration access denial](evidence/usability-2026-09-15-player-access-denied.png).

Assistant source verification: only the active current turn is editable; future
turn 2 is read-only while turn 1 is current. Package comment / Add package comment
and action-comment forms exist in the editable draft area, separate from the
Discussion output section. They are hidden on noncurrent turns. The user's exact
selected turn when inspecting Discussion is not confirmed, so the missing-control
observation may involve placement/discoverability, read-only state, or both.
Open workspace applies the chosen team/turn through a GET navigation. Team choices
are permission-filtered; an administrator role alone does not confer private-team
viewing rights. A future convenient admin view must preserve that distinction.

Next: explicitly return to turn 1, save overall intention, add a package comment,
and reload to verify persistence. Do not submit the package yet.

## Step 4b — Save intention and package comment

User outcome: intention and package comment saved; confirmation absent. Screenshot
shows both intention and comment with two history revisions. Refresh persistence
was not explicitly reported and will be checked with the next action.

Original user comments:

> Save intention did save, but again there is no indication to the user - a toast is appropriate.
> Same comment for saving the package comment. The font/display in 'discussion' is backwards - the User info is larger/more prominent than the actual comment.
> Expanding the 'Revision 2' doesn't show anything meaningful. That revision was adding the package comment. what shows is just a repeat of the already entered 'Overall intention' data.

Screenshot: [Discussion and draft history](evidence/usability-2026-09-15-discussion-history.png).

Assistant source verification: adding a comment increments the draft revision and
stores a package snapshot, but comments are separate records and absent from that
snapshot. History renders the snapshot without an operation description or diff,
so a comment-only revision repeats unchanged intention/action content. This is a
history-presentation gap, not evidence that the comment was lost. Discussion uses
a normal paragraph for metadata and a preformatted block for the actual comment,
consistent with the screenshot's reversed emphasis.

Identity context: screenshot attributes both revisions and the comment to **Blue
Teammate**, whereas earlier instructions suggested blue_submitter. This may reflect
the signed-in account or its configured display name; do not infer an authorization
bug. Both blue team members may draft. Confirm the active account/display name
before submission-authority checks.

Next: add one complete action, reload, verify intention/action/comment persistence,
and note whether the displayed author is the expected account.

## Step 4c — Create an action

User outcome: action creation occurred, inferred from the existing-action Save
control; ambiguous action label and disorienting screen update. Refresh persistence
and expected author identity remain unconfirmed.

Original user comments:

> Add action was unclear if that was a 'save what I wrote' or add in a second place for me to add 2 actions. Adding the action caused a confusing screen update. The info I typed seemed to disappear (It jumped up to a new area above what I was looking at). The new button for the existing action is clearly a 'save'.
> Save & Remove are vertically aligned - they should probably be on the same row with a visual indication of the positive (save) and negative (remove).

Assistant context: the New action form creates a saved action that is then rendered
above the empty New action form. This explains relocation but does not establish
the exact scroll/focus behavior seen by the user. Existing actions have separate
Save action and Remove action forms. Record this as a layout/interaction request;
do not implement it during the review.

Next: edit the saved action and reload to verify persistence, then use a clearly
disposable unsaved marker in one form while saving a different form to assess
whether unrelated unsaved edits survive. No removal or submission yet.

## Step 4d — Saved edits and unrelated unsaved input

User outcome: saved revision logged and persisted after refresh. Unsaved
description did not survive saving intention and refreshing; no warning or status
was shown. Exact point of loss (save-triggered page update versus manual refresh)
was not separately established.

Original user comments:

> No indication that revision has saved. The revision was logged & saved/persisted post refresh. Saving the intention with an unsaved change in description did not save the description (it was lost on the refresh) there was no displayed warning or indication.

Assessment: persistence passes for the saved revision; unsaved-input protection
fails for the observed sequence. Saving intention need not implicitly commit the
description, but unrelated edits must not disappear silently. This is distinct
from a concurrent saved-edit conflict and needs separate acceptance coverage.
The recurring missing-save-confirmation observation extends UX-32.

Next: use two independent browser sessions to edit the same saved draft version,
save one, then attempt the other's stale save and inspect recovery before resolving.

## Step 5a — Two-user stale edit

User outcome: second save produced a conflict message, but viewport moved to the
bottom and the user had to scroll back up to find it. Meaning and next action
were unclear. Attempted-text preservation was not explicitly confirmed.

Original user comments:

> The second user's screen scrolled to the bottom after selecting 'save intention'. Scrolling back up, the edit conflict dialog was shown. The edit conflict dialog does not easily identify what the problem is, or what the user should do. The app needs to be responsive to multi-user work. It should push changes as they occur (or ideally, allow simultaneous/live edit). The draft history portion can go away. It is useful for admin verification or potentailly for rollback but is unneeded for the average player - especially since it doesn't enable any interaction (like rollback). Actopms should be minimizable and sortable. If the team drafts 90 actions for a turn having every form block always shown will become unuseable. Related, there should be a view and an edit mode so that accidental changes are minimized.

Interpretation for planning: user requests automatic teammate updates, with
simultaneous/live editing as the preferred experience. Transport/merge approach
is not selected. Remove draft history from the normal player-facing layout;
retain authoritative history for audit/recovery. Rollback is a possible use case,
not an implemented capability. Requested action collapse/sorting and view/edit
modes must support high action volume; 90-action usability has not been tested.

Next: resolve the conflict deliberately using a combined intention, then reload
the first session to verify the chosen result. Keep real-time updates as a recorded
gap rather than implying the current app pushes saved edits.

## Step 5b — Conflict resolution

User outcome: pass.

Original user comments:

> Pass. text was preserved, combined edit was available to the other user on refresh.

Evidence: attempted text survived conflict handling; user saved a combined edit,
and the other session displayed it after refresh. Automatic/live update remains
unimplemented and is not implied by this pass. UX-38 remains open for discovery
and clarity despite successful recovery with guided instructions.

Next: verify ordinary member has no submission control, then designated submitter
submits the existing package and both users inspect the effective version. Do not
propose an amendment until initial submission is confirmed.

## Step 6a — Initial submission and authority

User outcome: blue_member lacked Submit; blue_submitter successfully submitted.
Submission confirmation absent. Visibility of the same submission in the other
session was not explicitly confirmed.

Original user comments:

> blue_member did not have 'submit' the submission worked on the blue_submitter, there was no indication the submission occured. The view of 'submitted packages' is not valuable. The actual submission (the forms/actions) should show that they have been submitted so that players have clear indication where they are working that the turn was submitted; related, there should be a clear indication that they are revising a submitted package if they choose to make a change.

Interpretation: status belongs at the point of writing, not only in a separate
Submitted packages section. Mark the turn/package and its actions as submitted;
make subsequent editing an explicit revision mode with clear pending/unsubmitted
changes and effective-version status. Preserve original submitted snapshots even
if their current presentation is replaced. Do not imply each action is separately
submitted: the current submission unit is the complete turn package.

Next: change one saved action in blue_submitter's draft after submission, verify
effective submission version 1 still has the original text, then propose the draft
as an amendment and inspect pending status before an adjudicator decision.

## Step 6b — Draft revision and amendment proposal

User outcome: edited draft saved; effective submitted package stayed unchanged;
proposal succeeded and version 2 is pending.

Original user comments:

> Edit made, saved, submitted package did not update. Propose amendment is an odd phrasing. Who is the amendment being proposed to? If the player can make a change then it should be submit change or submit revision. If the turn is locked (no longer accepting edits / past turn in deadline) then they shouldn't have an option to submit. 'Propose' implys uncertainty that shouldn't exist. The button worked - the amendments secion shows that version 2 is pending.

Current behavior clarification: the designated submitter proposes a revision to
the adjudicator, whose acceptance changes the effective submission. Current active
turn submissions may be late and are marked; deadline passage alone does not lock
the turn. Noncurrent turns are read-only. These are existing policies, not the
user's requested future behavior.

Planning direction: use Submit revision/Submit change and explain recipient and
status. User expects unavailable submission controls when the turn is locked or
past its deadline. This changes the documented permissive late-submission policy
and must be reconciled explicitly. Whether revisions during an open turn should
become effective immediately or still await adjudicator approval remains unclear;
do not silently infer that a label change authorizes a change of approval policy.

Next: open the adjudicator review for the blue team, inspect effective version 1
and pending version 2, then record a rejection with a reason to verify that the
effective submission remains unchanged. Acceptance will be checked afterward.

## Step 7a — Adjudicator review and rejection

User outcome: player logout unavailable; user closed and reopened the incognito
session to switch accounts. Adjudicator view required supplied navigation. Proposed
change difficult to locate. Player could see rejection, but notice was buried.
Exact rejection reason and unchanged effective version were not separately
confirmed in this response.

Original user comments:

> There is no logout option for a player. The only way to get a new login was to close the incognito browser and reopen a new session. There is no method for the adjudicator to get to their view. The change was hard to locate - the views don't show at the same time there is no highlighting of what is different. The reviewer needs to read all text in both versions to locate the delta. This will be even worse when there are more than 1 action in the turn to review. The player /can/ see the rejection - but it is burried at the bottom of the screen and doesn't have any visual indication that there is something to review or see.

Planning interpretation: logout must be available across signed-in roles, and
adjudicators need a discoverable assigned-game review entry point. Review must
identify changed actions and highlight changed fields/text against the effective
version, with simultaneous comparison. Player decision status and any action
required belong at the point of work, not only in an amendment-history section.
The larger-action-count comparison burden is a projected issue, not measured yet.

Next: return to blue_submitter, correct the draft inspection-point sentence,
submit another revision, then accept it as adjudicator and verify the new effective
version and preserved original. Do not assume the new revision is version 2;
the rejected version remains in history.

## Step 7b — Accept corrected revision

User outcome: revision accepted; effective version now 3. Browser close/reopen/login
workaround still required for account switching. Original version retention was
not separately confirmed in this response.

Original user comments:

> The revision shows accepted - I continued to use the browser workaround (close, reopen, relogin). The effective version now shows version 3. None of this workflow is intuitive or well displayed - the entire submit/review/revise process needs to be redone.

Planning direction: prioritize an end-to-end redesign of submit/review/revise,
not isolated visual patches. Preserve the demonstrated authority, immutable
submission and effective-version behavior while explicitly reconciling deadline
and open-turn revision policy (UX-45/46). Incorporate role navigation/logout,
clear package states, readable differences, attention cues and action confirmations.
Validate the replacement flow with a fresh unaided walkthrough, including both
rejection/resubmission and acceptance.

Next: opposing-team access check using red_submitter. Remaining checks include
reorder/removal history, selected error/keyboard/narrow-window behavior, memory
exploration and optional submitter replacement. Avoid repeating already covered
workflow solely to reconfirm its usability problems.

## Step 8a — Opposing-team access

Original user comments:

> Signed in as red. There is no way to switch to test no access to blue's page (the url is the same for both red/blue and the form retrieval is backend - I don't see value in using the debug console to test that the access cannot be hacked for this application. The /adjudicate?game_id=ux-review endpoint gives a 'detail':'not found' error.

User outcome: signed in as Red; `/adjudicate?game_id=ux-review` returned a Not found
error. User does not want debug-console/security probing as part of this walkthrough.
No debug console was needed for the proposed direct-link check, but do not repeat
or press that check. Explicit targeting of Blue's workspace is skipped; cross-team
isolation is not manually established by this result. Existing automated security
evidence remains separate from this manual review.

UX observation reinforces the raw error/dead-end findings (UX-19/27). Session-based
team selection is opaque to the user; role/team context and navigation need to be
understandable without interpreting URLs. No unauthorized disclosure was reported.

Next: keyboard focus and zoom/narrow-window readability in the current Red
workspace, without further account switching or access probing.

## Step 8b — Responsive layout

Original user comments:

> View is consistent across screen sizes. It properly stacks on narrow views.

User outcome: responsive layout passed for the sizes inspected; narrow view
stacks correctly. Keyboard focus/order and the specific 200% zoom check were not
explicitly reported, so do not mark those checks passed.

Next: a short fixture-memory explorer usability check, then consolidate this
journal into an actionable plan and explicitly list remaining untested checks.

## Step 9 — Memory explorer blocked

Original user comments:

> Print the url I need - I cannot click on the hyperlink or view the path in this interface. I tried to navigate to /memory?game_id=ux-review but I got some missing fields error (scope_id, known_at, effective_microseconds). Using /dev/memory I got {"detail":"Unexpected error", "request_id":"uuid"}

Follow-up instruction:

> Don't fix it - log the issue for the future fixes.

Outcome: blocked. Use plain-text URLs in subsequent walkthrough instructions.
`/memory` is a parameterized data endpoint rather than the fixture browser;
`http://localhost:18000/dev/memory` is the intended development viewer.
Read-only diagnosis found that the Harbor Relief and Orchid Accord artifacts
parse successfully, but `operational:ux-review` has no fixture source. The viewer
enumerates all artifacts and attempts to parse the operational artifact as a
fixture, causing validation failure and the generic Unexpected error response.
This appeared after game activation; the viewer had returned HTTP 200 before it.

Assistant briefly added a one-line filter to exclude operational datasets, then
reverted that edit following the user's instruction. Restart did not complete.
No memory-viewer fix is retained. Future work must add regression coverage for
fixture exploration after activating an operational game. Further memory
readability/search/navigation checks are untested because the page is blocked.

## Consolidated planning backlog

Provisional priorities; consolidate and review after completing the walkthrough.
These findings are recorded for planning, not implemented during this step.

| ID | Origin | Finding and proposed change | Priority | Acceptance check |
| --- | --- | --- | --- | --- |
| UX-01 | Step 2 | Successful login is invisible on the landing page. Display signed-in identity/state and appropriate navigation; remove or replace Sign in when authenticated. Choose a useful post-login destination. | High | After login the user can identify that login succeeded and where to go next; no visible Sign in action appears to do nothing. |
| UX-02 | Step 2 | Sign out has excessive prominence and awkward placement. Use a smaller header-right control or a discoverable account menu, per user preference. | Medium | Sign out is discoverable in the header/account area, keyboard accessible, and visually secondary to the page's primary work. |
| UX-03 | Step 2 | Administrative expanders resemble unfinished text. Make the controls visibly interactive, with clear expansion indicators and hover/focus/cursor treatment. | Medium | Users recognize each control as expandable, can open it by mouse and keyboard, and see its expanded/collapsed state; hovering the label signals interaction. |
| UX-04 | Step 3a; extends UX-03 | Expander click area extends far beyond its label without a visible boundary. Style the whole interactive region consistently. | Medium | Visible boundaries and hover/focus styling match the actual clickable area, including space to the right of the label. |
| UX-05 | Step 3a | Oversized per-user Deactivate controls and an unbounded list push essential administration actions below the fold. Use compact rows, search/filtering and pagination; keep primary actions above or separate from the list. | High | With hundreds of users, creating users/configuring games remains discoverable without scrolling through the roster; a specific account can be found efficiently. |
| UX-06 | Step 3a | Deactivate does not explain its consequences; inactive accounts cannot be reactivated in the application. Explain retained identity/history and blocked sign-in, and provide an authorized, audited reactivation workflow. | High | Administrator understands deactivation before acting, can restore the same account through the UI, and restoration does not revive revoked sessions or silently bypass current permission rules. |
| UX-07 | Step 3a | Recreating an inactive username produces a generic identifier/assignment error. Explain that the username belongs to an inactive account and direct the administrator to its management/recovery workflow. | Medium | Duplicate username feedback is specific, retains non-secret input and helps the administrator locate the existing account without creating a second identity. |
| UX-08 | Step 3b | Provide bulk create/import for local username/password accounts while preserving the intended future LDAP integration. | Medium | An administrator can preview and import multiple local users with row-level validation, duplicate handling and a clear result summary; credentials are not exposed in logs or feedback artifacts. |
| UX-09 | Step 3b | List growth is insufficient confirmation. Provide an accessible success toast for creation and explicit failure feedback. | Medium | Successful creation identifies the created account in a status announcement; failure is clearly announced with actionable detail and persistent field errors where relevant. |
| UX-10 | Step 3b; extends UX-05 | Oldest-first user ordering is inadequate for large rosters. Provide explicit sorting plus search and filtering. | High | Users can sort by username/display name and find active or inactive accounts; current sort/filter state is visible and works across pagination. |
| UX-11 | Step 3b | Add a user-management interface for name updates and local password reset; distinguish local credential actions from future LDAP-managed identity. | High | Authorized administrators can edit a display name without changing identity/history and reset local credentials through a clearly explained, audited workflow; old sessions are revoked on password reset. |
| UX-12 | Step 3c | Generate stable game identifiers in the backend instead of asking facilitators to invent internal identifiers. | High | Creating a game requires no internal ID input; the generated ID is unique and remains stable if its title changes. Subsequent UI operations select games by meaningful labels rather than requiring typed internal IDs. |
| UX-13 | Step 3c | Explain each game-setup field's purpose, audience, downstream effect and required/optional status. Distinguish public description/rules/briefing from scenario premise and structured rules. | High | A facilitator can determine what belongs in each field, who sees it, whether it affects adjudication and whether it can be left empty without reading code or documentation. |
| UX-14 | Step 3c | Replace mandatory raw JSON authoring with guided scenario configuration in the eventual interface; user accepts JSON as a temporary mechanism. | High before facilitator pilot | Facilitator can configure teams, actors, objectives and turns through validated controls without composing JSON. Any advanced JSON path is optional. |
| UX-15 | Step 3c; extends UX-09 | Game creation provides no clear success/failure feedback. Add explicit outcome messaging and a direct route to the created game's setup. | High | Successful creation names the game and offers or opens its details; failure clearly explains corrections and retains entered content. |
| UX-16 | Step 3d | Assignment success closes the form and jumps to the page top without confirmation. Keep task context and provide an accessible outcome message. | High | Saving an assignment identifies user/game/team/role, updates the roster and preserves a useful scroll/focus position for the next assignment. |
| UX-17 | Step 3d; extends UX-12 | Replace typed game/team identifiers with named game selection and a dependent team selector. Provide a controlled Add new team path where supported. | High | Only authorized games and their valid teams are offered; changing the game clears invalid team selections. New-team creation respects scenario lifecycle constraints and returns to the assignment task. |
| UX-18 | Step 3d | Provide a game-centric participant-management view showing assigned/unassigned users, team and authority, with multi-user assignment and coordinated account creation. | High | An administrator placing 50 users can see completed and remaining assignments without an external checklist; existing assignments are visible before saving and partial failures are clearly reported. |
| UX-19 | Step 3d | Invalid game input renders raw JSON 404 instead of usable form recovery. | High | A stale/invalid game selection gives a safe human-readable message within the form, preserves other selections and offers valid choices without exposing inaccessible games. |
| UX-20 | Step 3d | Error recovery exposes internal UUIDs and replaces semantic controls with raw text fields; combined team/authority error is ambiguous. | High | Validation retains the selected user's readable name and dropdown controls, marks the specific invalid field and provides a concrete correction; retry affects the originally selected user. |
| UX-21 | Step 3d follow-up | Membership actions have ambiguous ownership because user blocks lack boundaries and obvious ordering. Group by team and use compact labeled rows/cards with a predictable user sort order. | High | Every role-change, replacement and removal control is clearly associated with its named user; team grouping and order are understandable without trial actions. |
| UX-22 | Step 3d follow-up | Empty replacement selector and active Replace submitter button appear when no eligible teammate exists. Show an explanatory unavailable state instead. | Medium | With no eligible replacement, show a concise explanation and no actionable empty form; offer the replacement control only when a valid candidate exists. |
| UX-23 | Step 3d follow-up | Game-role grant attribution exposes an internal UUID. Resolve granting-user display name/username and format timestamps readably. | Medium | Administrator can identify who granted access without decoding an ID; unavailable/deactivated grantors have clear historical attribution. |
| UX-24 | Step 3e; extends UX-09/15/16 | Activation silently collapses the form; only changed game status signals success. Show an accessible activation result identifying the game and current turn, with a clear next action. | High | Administrator knows activation succeeded without searching the page; failed prerequisite checks identify the unmet requirement and a route to resolve it. |
| UX-25 | Step 3e | Configuration history and grants and the game-title link have different labels but identical destinations. Consolidate navigation or make the specialized link target a labeled section. | Medium | Link labels accurately describe their destination; any duplicate shortcut has an obvious purpose rather than implying a separate view. |
| UX-26 | Step 4a; extends UX-01 | Signed-in players have no discoverable route to assigned games/workspaces. Provide role-aware home navigation with assigned games and their current turn. | Blocking usability | A player signs in and opens their assigned workspace without a supplied URL; navigation does not present inaccessible administration as their next task. |
| UX-27 | Step 4a | Access-denied page is a navigation dead end and does not use the app shell. Retain accessible navigation to home/authorized workspaces and explain unavailable access accurately. | High | A denied user can recover without browser Back or manually entering a URL; no private data is exposed. |
| UX-28 | Step 4a | Single-team players see an unexplained team selector. Show fixed team context for one authorized team and explain selection when multiple teams are available. | Medium | Single-team users see an unambiguous team label; multi-team selection includes only authorized teams and never creates an admin permission bypass. |
| UX-29 | Step 4a | Open workspace does not explain what it applies; current/future turn context needs clearer navigation. | High | Turn changes and their effect are obvious; current turn and read-only future/history states are labeled with a reason and an easy return to the current turn. |
| UX-30 | Step 4a | Workspace lacks cohesion and navigability. Organize context, draft/actions, discussion, history and submission into a coherent layout with clear section navigation. | High before player pilot | A player can locate the main writing, discussion and submission tasks with realistic action volume without scanning an undifferentiated page. |
| UX-31 | Step 4a | Discussion appears without an obvious way to contribute. Place a clearly labeled composer with the discussion, or explain why commenting is unavailable. | High | On an editable turn a player can find and post a team comment from Discussion; read-only views explain the restriction and how to return to an editable turn. |
| UX-32 | Step 4b; extends UX-09/16 | Saving intention and posting comments lack explicit success feedback. Apply consistent accessible status notifications to workspace writes. | High | Intention save and comment post each announce success or actionable failure without requiring users to infer it from content or revision numbers. |
| UX-33 | Step 4b | Discussion author/timestamp metadata dominates the smaller monospace comment text. Make comment content primary with readable body typography and secondary metadata. | Medium | Comment text is easy to read, preserves paragraph breaks and wraps appropriately; author and human-readable time remain identifiable without dominating. |
| UX-34 | Step 4b | Comment-only revisions repeat unchanged content with no indication of the actual event. Add meaningful activity summaries and change details, including links to added comments. | High | A reviewer can identify who added a comment versus edited intention/actions; comment-only entries expose the relevant comment, while content changes offer useful before/after details without discarding immutable snapshots. |
| UX-35 | Step 4c | Add action ambiguously suggests either saving the entered action or opening a second blank action. Use an explicit save/create label and make the resulting saved action easy to locate. | High | User understands that the button saves the current new action; completion confirms success and reveals/focuses the saved action without apparent disappearance or disorienting relocation. |
| UX-36 | Step 4c | Save and Remove controls consume separate vertical rows and lack clear positive/destructive distinction. Group related controls in a compact action bar with Save primary and Remove visibly secondary/destructive. | Medium | At normal desktop widths both controls clearly belong to the same action and share a row; narrow layouts remain usable, and destructive intent is conveyed by labels and styling rather than color alone. |
| UX-37 | Step 4d | Unsaved description text is silently lost when another section is saved and the page refreshed. Preserve unrelated dirty fields during partial saves and provide clear save boundaries and navigation/reload protection. | High — data loss | Editing description then saving intention does not silently discard description text; refresh/navigation either preserves recoverable draft input or warns before loss. No unrelated field is silently committed as a side effect. Verify both JavaScript and ordinary-form paths. |
| UX-38 | Step 5a | Conflict save scrolls away from the error; the comparison does not clearly explain collision or recovery. Focus/reveal a plain-language conflict summary with named versions and explicit resolution actions. | High | Second editor immediately sees which content changed and why saving stopped, retains attempted input, and can choose current/their/combined text without guessing; successful resolution preserves history. |
| UX-39 | Step 5a | Shared workspace does not automatically surface teammate changes. User requests pushed updates, ideally simultaneous/live editing. | High | Saved teammate edits appear promptly without manual reload; incoming changes never silently overwrite local unsaved text, editing state is clear, and disconnect/reconnect and conflicting edits are recoverable. Choose live merge versus pushed snapshots during design. |
| UX-40 | Step 5a; supersedes player-facing scope of UX-34 | Remove Draft history from the ordinary player workspace; preserve it for administration/audit and potential recovery tools. | High | Normal player layout omits the passive revision list while immutable history remains available to authorized review; any future rollback is explicit and creates attributable history. UX-34 remains relevant to that history surface. |
| UX-41 | Step 5a | Always-expanded action forms will be unwieldy at 90 actions. Add collapsible summaries and sorting/reordering controls. | High | A 90-action team package can be scanned and navigated through compact summaries; actions expand independently, and view sorting is clearly distinguished from changing canonical action order. |
| UX-42 | Step 5a | Always-editable forms invite accidental changes. Provide distinct view and edit modes with clear save/cancel behavior. | High | Actions default to a readable view, explicit Edit opens controls, Save/Cancel have predictable effects, and unsaved changes remain protected during navigation and teammate updates. |
| UX-43 | Step 6a | Submission has no explicit confirmation and status is isolated in an unhelpful Submitted packages section. Show submitted package/version status directly in the active workspace and action views. | High | After submission, players immediately see that the turn package and displayed submitted actions are submitted; all teammates see consistent authoritative status without finding a separate section. Preserve immutable versions behind the redesigned view. |
| UX-44 | Step 6a; extends UX-42 | Editing after submission looks like ordinary drafting. Provide an explicit revise-submission mode with clear distinction between effective submitted content, saved draft changes and a pending amendment. | High | A player intentionally starts a revision, sees which content differs from the effective package, knows saving is not resubmission, and can identify whether the amendment is unproposed, pending, accepted or rejected. |
| UX-45 | Step 6b | Propose amendment obscures the recipient and next step. Prefer Submit revision/Submit change and explain who receives it and whether approval is required. | High | Button clearly submits a revision; adjacent status explains whether it is effective or awaiting the adjudicator. Resolve open-turn immediate effect versus approval before implementing policy changes. |
| UX-46 | Step 6b | User expects locked/past-deadline turns to reject submission and hide/disable submission controls. Current implementation accepts late submissions in the active turn. | High — policy reconciliation | Define lock/deadline behavior explicitly, reconcile roadmap/contracts, and enforce it both in UI and service commands; a stale open page cannot submit after the agreed lock boundary. Communicate why submission is unavailable. |
| UX-47 | Step 7a; extends UX-02 | Players lack a logout control; switching identity requires closing the private browser session. Provide a shared account/logout control for every signed-in role. | High | Player and adjudicator can sign out from their normal pages without administrator access, manual URL tricks or closing a browser; logout revokes the session and returns to a usable sign-in page. |
| UX-48 | Step 7a; extends UX-26 | Adjudicator cannot discover their review view. Add assigned-game review navigation and pending-review indicators appropriate to their role. | Blocking usability | An adjudicator signs in and reaches the correct game's review queue without a supplied URL; pending revisions are discoverable. |
| UX-49 | Step 7a | Revision review forces full sequential rereading with no highlighted differences. Provide changed-action summaries and simultaneous original/proposed comparisons with field/text differences. | High | Reviewer immediately identifies the changed inspection-point sentence, can inspect old/new content together, and can navigate changed/added/removed actions without rereading unchanged actions in a large package. |
| UX-50 | Step 7a; extends UX-43/44 | Rejection is buried without a visible attention cue. Surface decision status and reason in the player workspace with a direct action to inspect/revise. | High | Player sees rejection and any required response near the relevant package/action after returning or receiving an update; preserved historical decisions remain accessible without dominating the workspace. |
| UX-51 | Step 7b — overarching redesign request | Redesign the entire submit/review/revise experience as a coherent role-based workflow; consolidate related UX findings into one delivery plan instead of treating each as independent styling work. | Highest product priority | Players and adjudicators complete draft → submit → review → reject/revise or accept without guided URLs, browser-session workarounds or explanation of internal version mechanics. State, next action, changed content and decision reasons are clear where users work; authority, history and effective-version integrity remain verified. |
| BUG-01 | Step 9 | Development memory explorer parses operational artifacts as fixtures and fails after game activation. Separate fixture enumeration from operational memory records; retain a usable human-readable error path. | High — blocks memory review | Activate a game alongside loaded Harbor/Orchid fixtures, then open /dev/memory successfully and browse/search both fixtures. Do not alter operational history or weaken access rules. Add a regression test for mixed artifact types. |

## Environment blocker

Read-only inspection found schema 0002 (required: 0005), one staged artifact,
one memory timeline, 32 memory revisions and 72 disclosures. Migration 0005
requires an empty baseline; direct upgrade is unsuitable for this populated DB.
A request to provision an isolated PostgreSQL review container was rejected;
no replacement database was created and existing data was not modified.
Authenticated workflow and memory checks remain blocked pending setup resolution.

### Resolution

User confirmed the application has only preliminary test data and instructed:

> Don't back up the existing database. Nothing in it needs persistence.

Rebuilt only `living_memory_dev` in the existing PostgreSQL container, without a
backup. Retained the separate test database. Applied schema 0005, staged and loaded
Harbor Relief and Orchid Accord, and restarted the app on VM loopback port 8000.
Readiness now reports ready; login and memory explorer return HTTP 200.

Assistant-discovered setup defect: the standalone `load-memory` CLI omitted the
administration model registration required by memory_dataset's admin_game_id
foreign key. Added that import in cli.py. Both real fixture loads then succeeded;
Ruff, mypy (20 source files), and git diff --check passed. Full suite not rerun.

User subsequently created the initial administrator and verified login and
administration access (Step 2). Next: create a first test player through the UI.
