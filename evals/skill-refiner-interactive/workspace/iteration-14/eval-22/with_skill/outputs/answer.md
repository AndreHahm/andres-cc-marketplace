# Eval 22: Tool scoping (undeclared tool) goal, ADVISORY on one Bash command

## Goal result

**PASS**

## Basis

The goal's verification in `references/goal-derivation.md` (Finding → Goal → Verification table, row "Tool scoping (undeclared tool)") reads:

> Every invoked tool is declared in `allowed-tools`, or cleared by R6's deliberately-ungranted exceptions | Re-run the checklist's tool-scoping scan → no undeclared tool flagged as Major; an ADVISORY (unverified) result does not fail the goal and stays in the report

The re-run scan flags nothing as Major. Its only result is one Bash command rated ADVISORY (unverified) under R6's deliberately-ungranted exceptions, because the stated reason could not be confirmed. The goal's own text says that such an ADVISORY "does not fail the goal", so the verification returns the expected result and the goal is PASS.

Because the goal is PASS, the Measurement step's FAIL path (the `AskUserQuestion` for "Accept with reason" / "Continue refining") does not run.

## What happens to the advisory in the session report

- The advisory is reported as **ADVISORY (unverified)**, not as a Major finding and not as a FAIL. `references/pre-analysis-checklist.md` requires that an R6 result rated ADVISORY is reported as ADVISORY.
- It is listed in the report's `Tool scoping (R6):` line, which must name the undeclared-tools list. The advisory goes there as an ADVISORY entry. It is not added to the undeclared-tools list as a violation.
- It stays in the report as an open item for the operator to read. It does not block the session, and it needs no recorded accept-with-reason.

Quoted sentence relied on: "an ADVISORY (unverified) result does not fail the goal and stays in the report".
