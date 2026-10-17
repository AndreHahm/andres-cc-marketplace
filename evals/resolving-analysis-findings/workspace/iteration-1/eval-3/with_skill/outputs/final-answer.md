# Codacy Bandit_B603 on plugins/example-kit/scripts/run-git.py line 120

Nothing has been edited and no codacy/gh command was run (sandbox). Here is where the skill puts us.

## Step 1: fresh record (not done here)
Before any edit I would run `Skill(collecting-analysis-findings)` for the PR's current head. It must confirm that file, line 120 and issue_id are still present, and that the analysis is not stale or running. Sandbox forbids it, so this is a pending prerequisite.

## Step 2: new vs baseline
Treated as a `new` finding, since it fails this PR's check. Baseline status is unconfirmed until the fresh record.

## Step 3: ladder
- Rung 1 (fix in code): first confirm in the code that line 120 is a list-form `subprocess` call, with no `shell=True`, and a literal subcommand, with no untrusted text in the command. If untrusted text does reach the command, it is a real finding and gets fixed in code. Do NOT swap bare `git` for an absolute path; that trades a Warning for Semgrep's Error-level dangerous-subprocess-use.
- Rung 2 (inline `# nosec B603 B607  # <reason>` on the line that opens the call): if it is the accepted-on-purpose shape (AcceptedUse, per docs/ci.md "Codacy: git through subprocess in plugin scripts"), this is the default rung. Use the trailing `# reason` form, not `-- reason`, and edit the canonical plugins/ file (sync the .claude mirror). Stay within the line length.
- Rung 3 (per-issue ignore) and rung 4 (`exclude_paths`) are not appropriate: production code, and the issue id moves with the code.

## Decision rights: I must ask first
Medium is not in the list (Minor, Info, Warning) that I may decide alone. So rung 2 on a Medium finding requires AskUserQuestion, even though the repo has a standing decision for this pattern. Question I would send:

> **Suppress Bandit_B603 on plugins/example-kit/scripts/run-git.py:120?**
> Codacy reports this as Medium (Security). Once confirmed, the call is list-form, no `shell=True`, literal subcommand, which this repo accepts for git-through-subprocess (docs/ci.md). Proposed edit, local only, no remote write: add `# nosec B603 B607  # list-form call, literal git subcommand, no shell` on line 120. Rung 1 (fix in code) is not available for this pattern, since no code shape avoids the rule.
> Options: (1) Approve the inline suppression as shown; (2) Fix in code instead; (3) Do nothing for now.

I stop here until you answer. Nothing is applied before then.

## Step 5/6 after approval
1. Edit the plugins/ file with the reason comment, and sync the mirror.
2. After the push and analysis, re-run `Skill(collecting-analysis-findings)`. Confirm the head matches and the analysis is finished, that the B603 count dropped, and that no new rule appeared. Check Prospector_bandit too, because it duplicates the same line. Codacy honoring `# nosec` is unconfirmed, so it can only be verified by that re-check.
3. If Codacy ignores the comment, fall back to rung 3. That needs a separate per-command AskUserQuestion showing the exact `codacy pull-request ... --ignore-issue <id> --ignore-reason AcceptedUse --ignore-comment ...` text.

Report afterwards: counts before and after, what was left (baseline).
