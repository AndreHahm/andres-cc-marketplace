# Process Notes (Baseline Run)

No skills were used for this task, per instructions (baseline condition). Steps taken:

1. Read the task: user reported that Claude runs `git checkout -- <path>` to "discard my last
   edit" without first running `git status`, risking loss of other uncommitted changes in the same
   file. Asked to write a `.claude/rules` file for this.
2. Skimmed the existing `.claude/rules/*.md` files already present in context (from the system
   reminder) to match this repo's established rule-file conventions: a `# Title` behavior-description
   name, `## When this applies`, `## Rule`, `## Why` sections, sometimes an `## Incident` reference.
   No dedicated rule-authoring skill was invoked — this was done by direct inspection of existing
   rule files' structure only.
3. Chose a behavior-description filename consistent with this repo's naming convention (per
   `consult-naming-conventions-first.md`, which says rules use "behavior-description" naming):
   `check-status-before-discarding-changes.md`.
4. Drafted the rule content covering: when it applies (discard/undo/revert requests on a
   working-tree file), the concrete rule (always run `git status`/`git diff` before a destructive
   discard command; don't over-scope to more than what was asked; ask before widening scope to
   `reset --hard`/`clean`), and the why (destructive discard commands remove all uncommitted changes
   to a file, not just the most recent edit).
5. Per the sandboxing instructions, wrote the rule file only to the designated `outputs/` directory
   under the eval workspace, not to the repo's real `.claude/rules/` directory.
6. Wrote this process-notes.md file to the same `outputs/` directory.
7. Recorded timing/token estimates to `timing.json` in the same directory.

No other files in the repo were modified. No git commands were run against the actual repository
state (no `git status`/`git checkout` executed) since the task was purely to author a policy
document, not to perform any git operation.
