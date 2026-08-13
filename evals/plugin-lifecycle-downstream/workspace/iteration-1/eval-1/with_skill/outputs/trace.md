# Dry-Run Trace: Critical Finding in Phase 5 (Audit) on a Component Already Edited This Session

**Scenario:** Running `plugin-lifecycle-downstream` against a target plugin. Phase 5 (Audit)
surfaces a Critical finding in a component that this same session already edited earlier for
an unrelated reason.

**Scope of this trace:** from Phase 5 surfacing the finding, through every gate the pipeline's
own instructions require, up to (but not including) the moment a fix is actually applied.
Every claim below is grounded in `SKILL.md` or `workflows/run-qa-pipeline.md` with a
line/section citation. Nothing below is inferred beyond what those two files state.

---

## 1. Phase 5 (Audit) runs and produces the finding

**Entry condition:** "Validation succeeded." (`run-qa-pipeline.md` line 73 — Phase 5 Entry)

**Actions** (`run-qa-pipeline.md` lines 75-83): Phase 5 dispatches the `plugin-auditor` skill
over the declared scope. `plugin-auditor` in turn dispatches `dependency-reviewer`,
`consistency-reviewer`, `security-reviewer`, `plugin-validator` (whole-plugin),
`plugin-rulebook-checker` (Structured output mode), `activation-reviewer`,
`completeness-reviewer`, the type-matched `*-reviewer`, and `scripts-reviewer`/`hook-reviewer`
where applicable — reusing Phase 3's `plugin-rulebook-checker`/`plugin-validator` results for
scope already covered there rather than re-dispatching. Findings are "Attribute[d] ... to
components/files, normalize[d] ... into the shared schema," each source report is preserved,
and an audit rollup is written. Phase 5 then "Evaluate[s] the declared audit success
criteria."

**The finding itself:** nothing in either file singles out a finding's *file* as special based
on prior session activity — Phase 5's Actions describe attribution and normalization only by
component/file identity, with no branch for "this file was already touched this session."

**Audit success criteria** (`SKILL.md` lines 194-196): "Default audit success requires no
unresolved Critical dependency, consistency, or security finding. Warnings and recommendations
may continue only when recorded as deferred or accepted risk with rationale." A Critical
finding is by definition unresolved at the moment Phase 5 surfaces it, so it fails this
criterion — this is a blocking finding.

**Phase 5 Exit** (`run-qa-pipeline.md` line 85): "**Exit:** If successful, continue. If
blocking findings exist, continue only to Phase 6."

So the immediate effect of the Critical finding is mechanical routing, not an automatic fix:
Phase 5's own exit rule sends the run to Phase 6 and *only* Phase 6 — it does not skip ahead to
Phase 7/8/etc., and it does not itself apply anything. This exactly mirrors Phase 6's stated
**Entry** condition (`run-qa-pipeline.md` line 89): "Phase 5 has blocking audit findings. If
none exist, record `not_needed`." The two lines are two halves of the same routing rule.

---

## 2. Phase 6 (Fix & Re-audit) opens — but does not yet touch any file

**Actions, first sentence** (`run-qa-pipeline.md` line 91): "Preflight check first, if not
already run this run (per 'Mutation and Confirmation')."

Per `SKILL.md`'s "Mutation and Confirmation" section (lines 215-225):

> "Phase 1 is read-only. Phase 2 is the first potentially mutating phase, so run the shared
> Open-PR and Branch-scope preflight ... immediately before its first write. **This check runs
> at most once per run.** ... Phases 2, 4, 6, and 8 ... each check this before their own first
> write and run the preflight only if it hasn't already run this run — never re-run it at a
> later phase once it has fired, and never let a later phase mutate without it having fired at
> all."

Since Phase 5's Entry required "Validation succeeded" (i.e., Phase 3 passed, possibly after a
Phase 4 fix cycle), the preflight may already have fired in Phase 2 or Phase 4. If it has not
— e.g., Phase 4 was `not_needed` and Phase 2 was skipped — Phase 6 runs it now, before doing
anything else. Either way, by this point the Open-PR/Branch-scope preflight has fired exactly
once, and Phase 6 has still made no write to the target plugin.

**Next, the fix-batch gate.** Phase 6's Actions continue (`run-qa-pipeline.md` lines 91-95):
"Obtain approval, apply minimal fixes through matching development skills, and re-dispatch the
originating reviewer against live files." This "Obtain approval" step is a restated pointer
into `SKILL.md`'s shared "Mutation and Confirmation" procedure — the SKILL.md text says
explicitly (lines 248-251): "Every Commit step in `workflows/run-qa-pipeline.md` (Phases 2, 4,
6, 8, and the Documentation commit in Phase 9) follows this same six-step sequence — restated
there only as 'commit,' not re-derived per phase."

The six-step "Before each fix batch" sequence (`SKILL.md` lines 227-246) is:

1. "Present finding IDs, proposed files, and the implementation component."
2. "Obtain per-item or clearly bounded batch approval."
3. "Apply through the matching development skill — for a skill-type finding, either the
   matching development skill directly or `skill-improver-loop`'s automated fix-review cycle;
   `skill-improver-loop` does not accept any other component type."
4. "Obtain separate approval before committing, including exact files and message."
5. "Commit via `Skill(git-kit:commit)` — never a raw `Bash(git commit:...)` call." (with the
   note that this is also hard-blocked by `git-kit`'s `guard-raw-commit.sh` PreToolUse hook)
6. "After the commit, run `Bash(git status:*)` and `Bash(git show --stat:*)` against the
   intended file list, per `.claude/rules/plugin-rulebook-enforcement.md`'s post-commit
   verification requirement."

The scope of this trace stops at the boundary between step 2 and step 3 — i.e., up to
obtaining approval, not the act of applying the fix.

---

## 3. The approval gate that must fire before step 3

Concretely, before any `Edit`/`Write` against the target plugin's file is made for this
Critical finding, the pipeline's own instructions require:

- The finding ID, the proposed file(s), and which development skill will implement the fix
  are **presented** to the user (step 1).
- **Explicit approval** is obtained — "per-item or clearly bounded batch approval" (step 2).

Only after that does step 3 ("Apply through the matching development skill") occur — which is
outside the scope requested for this trace.

Additionally, immediately before the eventual Commit step (step 5), the Open-Item Discipline's
Pre-Commit Disclosure check applies (`SKILL.md` lines 260-263): "immediately before every
Commit step (Phases 2, 4, 6, 8, and the Documentation commit in Phase 9), collect and state
every open item surfaced so far, including the mirror-sync check." This too is a distinct,
later gate from the step-2 approval and is not reached until after a fix has actually been
applied and is about to be committed — again outside this trace's requested boundary, but
confirming there is no single blanket approval that covers both applying and committing.

---

## 4. Does the file's prior in-session edit change, shortcut, or pre-approve any of this?

Nothing in either file grants adjacency-based shortcuts. The governing statement is
`SKILL.md`'s "Confirmation Discipline" section (`run-qa-pipeline.md` lines 236-240):

> "Pipeline confirmation authorizes read-only orchestration only. Preparing tests, applying
> fixes, keeping documentation edits, and committing each require their own bounded approval.
> **Never treat approval in one phase as authorization for a later mutation.**"

This is stated generally — about approval from an earlier *phase* of this same pipeline run —
and the two files never separately carve out an exception for a file the session already
edited for an unrelated reason before this pipeline started, or earlier within it. There is no
clause anywhere in `SKILL.md` or `run-qa-pipeline.md` that says a component's proximity to
already-touched work reduces, merges, or pre-satisfies the "Present finding IDs ... / Obtain
... approval" step, and no clause exempts such a finding from the "Before each fix batch"
sequence or from the preflight-and-approval requirement generally.

Two further provisions reinforce that this specific finding is treated exactly like any other,
regardless of the file's edit history this session:

- **Core Contract #3** (`SKILL.md` line 67): "The component that applies a fix does not verify
  its own work. The originating validator or reviewer rechecks live files." — the verification
  path for this finding is a re-dispatch of the originating audit reviewer against live files,
  not anything carried over from the earlier, unrelated edit.
- **Independent Recheck** (`SKILL.md` lines 268-272): "Revalidation and re-audit must read
  current files. Re-dispatch the checker that produced each finding and add a regression check
  for affected dependencies or related components. Do not accept a fixer summary, diff
  description, or score recomputation as verification." — again, no carve-out for a
  recently-touched file; the independent re-check requirement applies uniformly.

So: per the pipeline's own documented instructions, the Critical finding's adjacency to a file
this session already edited for an unrelated reason does **not** change, shortcut, or serve as
pre-approval for the Phase 6 fix-batch gate. The finding is presented (finding ID, proposed
file, implementation component) and approval is obtained exactly as it would be for a finding
in a file the session had never touched before.

---

## Summary of the trace, in order

1. Phase 5 dispatches `plugin-auditor`; the Critical finding is normalized into the shared
   finding schema and written into the audit rollup (`run-qa-pipeline.md` lines 75-83).
2. The Critical finding fails Phase 5's stated audit success criteria (`SKILL.md` lines
   194-196), so Phase 5 exits by routing "continue only to Phase 6" (`run-qa-pipeline.md` line
   85) — this routing is automatic/mechanical, not itself a fix and not itself a mutation.
3. Phase 6 opens (Entry: "Phase 5 has blocking audit findings," line 89) and first checks
   whether the Open-PR/Branch-scope preflight has already fired this run; if not, it runs it
   now, before any write (`run-qa-pipeline.md` line 91; `SKILL.md` lines 217-225).
4. Phase 6 then must, per the shared "Before each fix batch" sequence: (1) present the finding
   ID, proposed file(s), and implementation component, and (2) obtain per-item or
   clearly-bounded batch approval — **before** step 3, "Apply through the matching development
   skill" (`SKILL.md` lines 227-231).
5. Nothing in either file treats the file's earlier, unrelated in-session edit as satisfying,
   shortcutting, or pre-approving that step-2 approval; `SKILL.md`'s "Confirmation Discipline"
   states explicitly that approval from elsewhere in the run is never authorization for a later
   mutation (`run-qa-pipeline.md` lines 236-240).
6. The trace ends here, at the approval-obtained-but-not-yet-applied boundary — step 3
   ("Apply through the matching development skill") and everything after it (the Commit
   sub-sequence, Pre-Commit Disclosure, re-dispatch/verification) is outside the requested
   scope of this dry run.
