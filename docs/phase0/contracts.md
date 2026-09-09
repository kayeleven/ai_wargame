# Baseline contracts and policies

Status: accepted Phase 0 implementation baseline, 2026-09-09. Provisional operational targets remain subject to pilot evidence.

## Player content

A turn submission has `overall_intention` (free text) and `actions` (a variable-length ordered collection). Each action contains exactly these player-authored fields: `Title`, `Description`, `Intent of Action`, and `Anticipated reaction`, all free text. `action_id` is system metadata. Zero actions is permitted for the initial fixture; there is no fixed game-level maximum. Technical payload limits remain a Phase 1 operational decision, not a game rule.

Do not require structured targets, resources, execution times, or domain labels from players. Preserve text and ordering exactly. Missing structured context is unknown, not zero, false, or an empty resource allocation. Incomplete native drafts may remain drafts; detailed submission completeness validation will be specified in Phase 1. Imports retain omissions instead of inventing field values; the initial imported example has all four text fields.

An anticipated reaction is the submitting player's expectation. Overall intention is context for all actions, not an additional adjudicated action. Neither text implies an established effect. Human or AI interpretations must be separate, source-linked, and labeled proposed, confirmed, disputed, or unresolved.

`content_version: 1` identifies this content structure. `version` identifies an immutable submission revision. Stable action identifiers survive revisions; the submission version fixes the action text and overall intention together. Import mappings and original artifacts remain accessible to authorized reviewers.

## Fixture record envelope

Every source record has a stable `id`, `kind`, `game_id`, `branch_id`, `effective_turn`, `recorded_at`, `disclosures`, `source_refs`, and a kind-specific `body`. These describe a fixture interchange format, not database tables or a public HTTP API. `source_refs` address record IDs; `action_ref`/`action_id` address actions within their source submissions. Stable action IDs may repeat across submission versions; record IDs may not.

`effective_turn` locates simulated applicability; `recorded_at` states when the system learns or records it. `disclosures` maps each authorized audience to its first availability timestamp. Eligibility requires recording and disclosure at or before the selected cutoff and membership in the selected game/branch. A future effective turn does not hide an already-known commitment or scheduled effect. Status and effective turn determine whether an effect is active. Superseding records preserve earlier versions and remain unavailable at earlier cutoffs.

A player view includes only authorized records and authorized source links. It excludes other audience disclosure metadata. References embedded in record bodies must also be authorized; summaries and traversal must follow the same rules. No hidden link IDs, counts, titles, or explanations should reveal excluded material. The adjudicator sees hidden reports and unresolved claims, not omniscient certainty.

## Authority and turn lifecycle

- Team members share knowledge, edit shared drafts, and comment. Only the designated submitter submits the team's turn package. A future second submitting player must have a distinct submission identity.
- Submission freezes the complete package at the deadline. Members cannot silently overwrite a submitted version. Optimistic conflict detection is the Phase 1 baseline; character-level collaboration is not required.
- Joint review follows simultaneous submission. The adjudicator may accept a versioned amendment before ruling. Affected review results must be marked stale and reassessed. Later drafts alone do not replace accepted submissions.
- One human adjudicator records rulings, authorizes effects, and separately authorizes feedback release. Submissions, discussions, commitments, and model output cannot directly mutate canonical state. Effect application must be atomic and idempotent in Phase 1.
- Cross-team sharing requires explicit consent and named coordination records. It does not grant access to linked private drafts. In the fixture both councils consent to `coordination-1`.
- RFIs distinguish intent clarification, retrieval of known information, intelligence collection requests, and establishing missing scenario facts. An unanswered RFI is a visible dependency. An answer that discloses an existing fact changes knowledge, not that fact's historical existence.
- A late answer is used prospectively. Reconsideration requires an explicit new correction/ruling preserving the old one; no automatic historical rewrite. Branching is outside this fixture.

## Model boundary (static only)

Preparation receives a contract version, game/branch/turn, audience, cutoff, method configuration, and frozen authorized record/submission references. The Turn 4 adjudicator example uses the review snapshot only. Production adapters must resolve references through authorization before sending content to a model; a filename or list of IDs is not an access-control mechanism.

Outputs contain issues, evidence references, proposed relationships, unresolved questions, assumptions, alternatives, proposed effects, and proposed disclosures. Evidence and proposed links must resolve within authorized inputs or logged authorized retrievals. Unknown references and malformed outputs are validation failures. Record actual supplied context, settings, raw output, validation errors, and reviewer edits in Phase 2. Never treat submitted or imported prose as trusted instructions.

No output grants authority. Stale inputs require reassessment; endpoint failure or invalid output permits human review to continue. Static examples cover success, unavailability, invalid evidence, and a result made stale by the amendment. No model has generated these examples.

## Deployment assumptions and provisional targets

Use offline Ubuntu hosting with Windows VDI browser clients and a configurable local model endpoint. Initial pilot target: eight concurrent users; ordinary interactive operations should meet p95 at or below two seconds, measured as browser request-to-response time under a documented mix of drafts, submission, RFI, and retrieval operations. Inference and its queue are measured separately. These are future validation targets, not achieved measurements or full-game capacity claims.

Before the first deployment design, confirm supported Ubuntu/browser versions, VDI network topology, identity, administrator access, and certificates (O-04). Select stack and packaging in Phase 1 (O-05); confirm local model capabilities, hardware, and offline provisioning before Phase 2 (O-06). Final workload proportions, inference targets, backup frequency, and recovery objectives remain O-10 and must be fixed before full-game readiness testing.
