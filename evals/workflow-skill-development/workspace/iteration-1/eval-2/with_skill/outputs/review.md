# Structural Review: Draft Workflow Skill (SKILL.md body)

Reviewed against `workflow-skill-development`'s anti-pattern checklist and validation checklist.

## Findings

### AP-6 — Unnumbered phases (Critical)
The entire "Steps" section is a single prose paragraph ("First... Then... After...") rather than
numbered phases. There is no `### 1. ...`, `### 2. ...` structure, and no per-phase entry/exit
criteria. As written, a reader (human or agent) can't tell where one phase ends and the next
begins, or what state must be true before starting each one.

**Fix:** Break into explicit numbered phases, e.g.:
```
### 1. Check Deployment State
**Entry:** deployment target identified.
**Action:** inspect current deployment status.
**Exit:** status is known and recorded (healthy / degraded / unknown).

### 2. Deploy
**Entry:** Phase 1 exit confirms "healthy" / "proceed" state.
**Action:** run the deploy.
**Exit:** deploy command completed (success or failure recorded).

### 3. Verify & Notify
**Entry:** Phase 2 exit is "deploy succeeded."
**Action:** verify the deployment, notify the team.
**Exit:** verification result confirmed and team notified.
```

### AP-7 — Missing exit criteria (Critical)
Related to AP-6 but distinct: even if phases were numbered, none of the three steps defines what
"done" looks like. "If everything looks good" (step 1) is not a checkable exit condition — good by
what measure? "Verify the deployment succeeded" (step 3) doesn't say what verification means
(health check? smoke test? manual check?) or what a pass/fail outcome looks like.

**Fix:** Every phase needs a concrete, checkable exit condition — a specific command's exit code, a
specific health-check response, a specific log line — not a vague adjective like "looks good" or
"succeeded" with no defined check.

### AP-5 — Broken file reference (Critical)
The skill links `[rollback-procedure.md](references/rollback-procedure.md)`, but
`references/rollback-procedure.md` does not exist in the skill's directory. This is exactly the
kind of broken reference AP-5 requires be caught before submission — a reader following this link
on a failed deploy would hit a dead end at the worst possible moment (mid-incident).

**Fix:** Either create `references/rollback-procedure.md` with real rollback content, or remove the
reference until the file exists. Every file path referenced from SKILL.md must be verified to
resolve.

### AP-8 — No real verification step (Major)
The Validation Checklist requires "a verification step at the end of the workflow." The draft
gestures at this ("verify the deployment succeeded") but folds it into the same run-on sentence as
notification, with no separation, no method, and no failure branch. There's no explicit final
validation step distinct from — and outcome-gating — the rest of the workflow, and no instruction
for what to do if verification fails (which is presumably where the missing rollback doc was meant
to apply).

**Fix:** Make verification its own numbered phase with a concrete check and an explicit
success/failure branch (failure → invoke rollback procedure; success → notify team).

## Not flagged
- **AP-2 (Monolithic SKILL.md)**: The excerpt is short; can't assess overall file length from this
  snippet alone. No finding either way.
- **AP-3 (Reference chains)**: Only one reference is present (`rollback-procedure.md`), and it's one
  hop from SKILL.md — no chain to flag, independent of the fact that the target is missing (AP-5).

## Summary
| Checklist item | Status |
|---|---|
| Numbers all phases with entry/exit criteria | FAIL — no phase numbering, no entry/exit criteria (AP-6, AP-7) |
| No broken file references | FAIL — `references/rollback-procedure.md` does not exist (AP-5) |
| Verification step at end of workflow | FAIL — verification is vague and unstructured, no failure branch (AP-8) |

All three checklist items fail. The draft needs to be restructured into numbered phases with
explicit entry/exit criteria, the missing rollback reference needs to be created or removed, and a
concrete, outcome-gating verification phase needs to be added at the end.
