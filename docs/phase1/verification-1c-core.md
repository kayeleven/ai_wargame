# Phase 1C-core verification

Status: implementation and local acceptance complete; the fresh-checkout gate is
recorded separately.

The permanent read model separates datasets, games, root branches, visibility
scopes, stable record/relationship identities, immutable revisions, disclosures,
explicit references, and ordered endpoints. Database constraints cover ownership,
same-identity supersession, uniqueness and half-open nonempty intervals. The
transactional loader validates supersession/reference graphs, targets, scopes,
source provenance, and relationship endpoints before commit.

Harbor Relief is preserved as the nine-oracle acceptance fixture. Orchid Accord
adds three controller groups for four actors, irregular turn lengths, custom
record/relationship types, a hidden endpoint in a three-endpoint relationship,
a correction and validity boundary, delayed record/relationship disclosure, and
a relationship revision. Both use the same manifest parser, loader, reader,
search, traversal, pagination and explorer.

Static verification refreshed on 2026-09-11 after remediation review:

- `ruff check .`: passed.
- strict `mypy`: passed.
- both packages validated and checksummed; Harbor reconciliation reported 46
  matched and zero unresolved differences; Orchid reported one declared-only
  intentional correction.
- `git diff --check`: passed.
- PostgreSQL unit/integration/migration suite: 44 passed, including distinct
  disclosure timestamps, executable Orchid oracle reconciliation, and frozen
  record/relationship cursor watermarks.
- Chromium browser suite, including both datasets with JavaScript enabled and
  disabled: 7 passed.

The fresh-checkout Docker gate remains separate and must close before 1C-admin
backup/restore acceptance. MEM-03 supports direct prerequisite/enabling links;
multi-hop traversal remains deferred to Phase 3.
