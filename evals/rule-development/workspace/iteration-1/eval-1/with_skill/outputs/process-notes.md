# Process Notes — check-git-status-before-discarding-changes.md

## Steps taken (following the rule-development skill)

1. **Stated the behavioral gap**: Claude runs `git checkout -- <path>` on a request like "discard
   my last edit" without first running `git status`/`git diff` to see what's actually uncommitted,
   risking irreversible loss of unrelated uncommitted changes in the same file.

2. **Determined scope**: Global rule (no `paths:` frontmatter) — this applies to any file in any
   repo, not a specific language or directory tree.

3. **Redundancy check** (Glob + Grep, as required by the skill's Redundancy Filter):
   - Globbed all files in the real `.claude/rules/` directory (21 files) and grepped for
     `checkout|discard|git status` across them.
   - Found 5 hits: `read-and-retrace-skill-chains-before-finalizing.md`,
     `plugin-rulebook-enforcement.md`, `starting-work-before-first-change.md`,
     `orphaned-worktree-git-read-fallthrough.md`, `route-through-git-kit-lifecycle-skills.md` —
     none of these govern discarding uncommitted working-tree changes; they cover commit/PR
     lifecycle routing, post-commit verification, and worktree-removal read fallthrough.
   - Read `recheck-state-before-side-effecting-action.md` in full since it looked closest in
     spirit (re-check state immediately before a side-effecting action). Determined it is
     **not** a duplicate: it's `paths:`-scoped to skills/hooks/scripts and specifically targets
     TOCTOU on *external async* state (CI run conclusion, PR head SHA, bot reactions) that the
     agent doesn't control. My new rule targets a different failure mode — a *local* git
     working-tree discard command run without ever looking at local state first, triggered
     directly by a conversational request, not by an async external signal. Cited that rule's
     "Enforcement" section as precedent for this rule's own disclosed-limitation wording instead
     of merging into it.
   - No existing rule covers "check status before a destructive git command on uncommitted
     changes" — proceeded to create a new file rather than editing an existing one.

4. **Wrote Incorrect/Correct examples**: Incorrect shows the exact plausible mistake (jumping
   straight to `git checkout -- <path>` off the phrase "last edit"). Correct shows running
   `git status`/`git diff` first, discovering the file actually has two unrelated uncommitted
   hunks, and surfacing that ambiguity to the user rather than guessing which one is "last."

5. **Frontmatter**: `title` + `impact: CRITICAL` (data-loss potential, irreversible outside editor
   undo history — matches the skill's Impact Reweight guidance for CRITICAL).

6. **Ran the Decompose → Filter → Reweight cycle**:
   - Decompose: single concept (check state before a destructive discard) — no split needed.
   - Misalignment filter: yes, an agent plausibly produces exactly the Incorrect example — "discard
     my last edit" is a natural, common phrasing that maps ambiguously onto file-scoped git
     commands.
   - Redundancy filter: done in step 3 above.
   - Impact: CRITICAL (irreversible data loss).

7. **Security self-check**: scanned the assembled file for hex/base64-like strings, secret-adjacent
   keywords, and internal URLs. None present — the examples use generic paths (`src/utils.py`)
   and no real code/credentials.

8. **Simulated `/rules-review`** (could not actually invoke the live skill against the sandboxed
   output location, since this rule was intentionally written outside the real `.claude/rules/`
   directory per the task's sandboxing instructions): manually traced the rule's Incorrect example
   against the rule text and confirmed it would fire (destructive command precedes any status/diff
   check); manually traced a legitimate case — an agent that runs `git status`/`git diff`, confirms
   the working tree matches the user's described single edit, and then runs `git checkout --` — and
   confirmed the rule's Correct example does not flag that case as a violation, so no obvious false
   positive on the common legitimate path.

## Checklist verification (rule-development's Rule Creation Checklist)

- [x] Behavioral gap stated as "does X, should do Y"
- [x] Rule type: global
- [x] Incorrect example shows a plausible agent mistake
- [x] Correct example is a minimal fix of the same scenario
- [x] Description states WHAT and WHY, imperative form ("MUST first run...")
- [x] Frontmatter has `title` and `impact`
- [x] Body under ~50 lines (checked by line count in the source file)
- [x] One topic per file
- [x] No overlap with CLAUDE.md or other rules (see redundancy check above)
- [x] Descriptive hyphenated filename: `check-git-status-before-discarding-changes.md`
- [x] No sensitive information in examples
- [x] Compliance simulated (see "Simulated `/rules-review`" above) — not run live, per sandboxing
      constraints on this task
