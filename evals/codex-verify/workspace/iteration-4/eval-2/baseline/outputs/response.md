# Routing

## Request 1: "verify the rollback step in docs/deploy-plan.md before I run it"

**Route: codex-verify**

Reason: the user asks for one step of an existing document to be verified. The skill's own text says a plan, document, or single plan step the user asks to have verified stays in codex-verify, even when Claude will execute that step later. It is a PASS/FAIL check of a file that already exists. It is not open-ended research (codex-research), not Claude's own unwritten analysis (codex-peer-review), and not a plan-validate-implement loop (codex-plan-loop). The consulting-decision-model route applies only to Claude's own unasked check before executing a step, and that is not what the user asked for.

## Request 2: "cross-model review this diff before I open the PR"

**Route: cross-model-review**

Reason: the input is a working diff, and the user wants a two-vendor review before a PR is opened. codex-verify explicitly does not review diffs; its text says it "verifies a document, not a diff" and sends a two-vendor review of the working diff to git-kit's cross-model-review. codex-peer-review is for Claude's own not-yet-written analysis, which this is not.

## Summary

| Request | Skill |
|---|---|
| verify the rollback step in docs/deploy-plan.md before I run it | codex-verify |
| cross-model review this diff before I open the PR | cross-model-review |
