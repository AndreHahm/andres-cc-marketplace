# Risk-to-Evidence Matrix

How much evidence a given risk level warrants, for Phase 2-3's classification. Risk is the risk of the
*behavior changed*, not the size of the diff -- a one-line change to an auth check is higher risk than a
500-line refactor of an already-covered internal helper.

| Risk level | What qualifies | Evidence bar for `adequate` |
|---|---|---|
| **High** | Auth/permission logic, data-destructive operations, security boundaries, anything touching secrets/credentials, public API contract changes | At least one behavior test or manual trial directly exercising the changed path, plus a security/adversarial check when the change touches a trust boundary. Structural/static checks alone are never `adequate` here. |
| **Medium** | Business logic changes, new user-facing behavior, changes to shared/reused code paths | At least one behavior test or a manual trial that actually exercised the changed path and observed the result. |
| **Low** | Internal refactors with no behavior change, comment/doc-only changes, changes already covered by an existing, still-passing test suite that wasn't touched | Static/structural checks passing is sufficient; a full new behavior test is not required to reach `adequate`. |

**When risk level itself is unclear or disputed**, classify at the higher of the two plausible levels
rather than defaulting low -- AKR-NFR-004's "honest uncertainty" principle applies here too: don't resolve
ambiguity in the direction that makes less verification look adequate.

**Post-fix re-verification always applies regardless of risk level.** A fix for a previously-failing check
needs that same check re-run and observed passing, independent of how the original risk level was
classified -- the risk assessment above governs how much *new* verification a change needs, not whether an
already-existing, previously-failing check gets re-confirmed after a fix.
