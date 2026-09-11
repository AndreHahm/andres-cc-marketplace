# Decision Record: Deprecate Legacy CSV Importer

## Decision

We are deprecating the legacy CSV importer in favor of the new bulk API endpoint, effective next release.

## Status

Approved

## Date

2026-09-11

## Context

The legacy CSV importer has been the primary mechanism for bulk-loading data into the system. A new bulk API endpoint is now available that supersedes it. Continuing to maintain both paths adds redundant surface area, so the decision is to standardize on the bulk API endpoint going forward and retire the CSV importer.

## Decision Details

- **What's deprecated:** The legacy CSV importer.
- **What replaces it:** The new bulk API endpoint.
- **Effective:** Next release.
- **Scope:** All bulk data-loading workflows currently relying on the CSV importer should migrate to the bulk API endpoint.

## Rationale

- The bulk API endpoint is the newer, presumably more capable and better-supported path for bulk operations.
- Maintaining two parallel import mechanisms (CSV importer and bulk API) creates duplicated logic, duplicated testing burden, and user confusion about which path to use.
- Consolidating onto a single, modern interface reduces long-term maintenance cost.

## Consequences

- **Users/integrators** currently depending on the CSV importer will need to migrate to the bulk API endpoint before or at the next release.
- **Documentation** referencing the CSV importer should be updated to point to the bulk API endpoint, and marked as deprecated where the importer is still mentioned.
- **Support/communication**: affected users should be notified ahead of the release so they have time to migrate.
- **Removal timeline**: this decision marks the importer as *deprecated* effective next release — it does not by itself specify a hard removal date. A follow-up decision (or the next release notes) should confirm whether deprecation means "marked deprecated but still functional" or "fully removed" at that release, and if kept temporarily, when actual removal will occur.

## Open Questions / Follow-ups

- Confirm exact migration path/guide for existing CSV importer users.
- Confirm whether the CSV importer will be hard-removed at the next release or kept in a deprecated-but-functional state for a transition period.
- Identify any downstream systems or scripts that call the CSV importer directly and need updating.

## Notes

This record was created as a standalone decision log entry per the request "record a decision: we're deprecating the legacy CSV importer in favor of the new bulk API endpoint, effective next release." No additional source material (e.g., an existing architecture doc, ticket, or discussion thread) was provided as input, so this record captures the decision as stated along with standard follow-up items a deprecation decision typically requires.
