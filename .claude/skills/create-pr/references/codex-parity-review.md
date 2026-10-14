# CI-Parity Codex Delta Review (step 4.5)

Why: a PR can pass every local gate and still fail CI's `Codex delta review` with new blocking findings
(issue #540, PR #505). CI runs four fixed reviewers (`plugin-rulebook-checker`, `dependency-reviewer`,
`security-reviewer`, `skill-reviewer`) as Codex exports on a GPT model, cold, over the whole diff, and
blocks on any Major or Critical on a changed line. Step 4's `cross-model-review` is a different, report-only
pass; this step runs CI's own entry point so those findings surface before the push.

## What the script does

`scripts/git-codex-parity-review.py --output <path>` (this repository only):

- Reads the Codex CLI pin from `.github/workflows/marketplace-ci.yml`, so it cannot drift from CI.
- Reads `CODEX_KIT_REVIEW_TIMEOUT_MS` the way CI does: the repository variable of that name (via
  `gh variable list --json`) when it is a valid number, else the fallback in the workflow's
  `vars.CODEX_KIT_REVIEW_TIMEOUT_MS || '<fallback>'` expression. The output says which one it used.
- Reads `CODEX_KIT_REVIEW_MODEL` with `gh variable list --json` (it is a repository variable, not a workflow
  value). Unset, unreadable or malformed means the local Codex default runs, and the output says so.
- Warns (does not fail) when the local `codex --version` differs from CI's pin.
- Fetches `origin main` into `refs/remotes/origin/main` with an explicit refspec, so it works under any configured
  fetch refspec (best effort; a warning if it fails), then runs `uv run python -m scripts.marketplace_ci
  run-codex-review --base-sha <tip of origin/main>` (CI's `base.sha`) and prints the base SHA it used.

Pass `--output` a **fresh** file in the session scratchpad on every run, a retry included (for example
`codex-parity-<epoch>.json`). The script never deletes or overwrites: an existing path (file, directory or symlink,
even a dangling one) is refused with exit 2, and a path inside the checkout is refused too. A completed run's
result must be the full payload `run-codex-review` writes (a string `mode`, the list fields, a boolean
`blocking`); anything else, including its `error` failure payload, counts as "could not run". The CI entry point's
per-reviewer instruction files go to `<output stem>-instructions/` beside `--output` (via `--instructions-dir`), so
nothing is written into the checkout; the script leaves that directory in place and refuses (exit 2) when that path
already exists, a symlink included.
The model variable is looked up on `origin`'s repository (`gh variable list --repo`), the repo this branch is pushed to;
a value the bridge would reject (anything outside `[A-Za-z0-9._-]`, or over 64 characters) is ignored with the fallback warning.
In this repository's own sessions `CLAUDE_PLUGIN_ROOT` is empty, so run the script from the checkout root as
`uv run python .claude/scripts/git-codex-parity-review.py` (the `.claude/` mirror; SKILL.md has a matching grant and
`.claude/rules/resolve-plugin-root-to-claude-mirror.md` explains why). Every helper call (git, gh, codex) is bounded
by a 60 s timeout, so a stalled network falls through to a warning or exit 2.

## Exit codes

| Exit | Meaning | What to do |
|---|---|---|
| 0 | Clean | Continue to the push |
| 1 | A valid result with `blocking: true` | Read the `--output` JSON: `findings[]` with `blocking: true`, plus `structural_findings[]`. Show path, line, severity, rule. Ask fix / re-run / bypass |
| 2 | Could not run (Codex missing, `origin/main` unresolved, dispatch failed, timeout, or a missing, malformed or contradictory result file) | **Never a pass.** Ask retry / bypass |
| 3 | No marketplace CI in this checkout | Skip the step and state that in session output |

After a fix, commit it the way SKILL.md's Pre-flight step 2 already does (that step carries the skip-Auto-PR and
skip-push instructions), then re-run step 4 on the updated diff (unless the user bypasses it) and step 4.5 again.

## Bypass

Only the user chooses it: at the `AskUserQuestion` shown on exit 1 or 2, or by declining the data-egress question (recorded as "egress declined"). Neither `--bypass-*` flag skips this step, and it runs even when step 4 was bypassed. Report it in session output and add
one line to the PR body's existing "Open Items" section naming the exit code and that the local parity round
was bypassed. Do not add a section to the template.

## Before flipping a draft to ready

A raw `gh pr ready` has no git-kit guard, so this is a documented step, not an enforced one. Before flipping
a draft that was not just created by this run, re-run `git-codex-parity-review.py` and apply the table above,
alongside `cross-model-review`.

## Limits

- If the branch changed a review-dispatch-critical (Tier-1) file, the script prints a warning and still runs.
  CI hard-refuses in that case, and the local run executes the branch's own copy of that code with your Codex
  credentials, so treat a clean result as non-authoritative.
- Ten minutes or more per run. The reviewers read the working tree locally and send the diff and any files
  they read to OpenAI under the user's Codex account (hence a separate confirmation on every run).
- On timeout the whole process group (`uv`, `node`, `codex`) is killed (POSIX), or the whole tree via `taskkill /F /T` (Windows, not exercised on a real Windows host); the wait
  for the pipes to close afterwards is bounded.
- The wrapper is a working-tree script like any other (tests, hooks): a branch can edit it, and the Tier-1
  warning covers only CI's dispatch files. Treat a clean result as advisory, not authoritative.
- Parity is best effort: reviewer output varies between runs and a local Codex version can differ from CI's.
- Windows: Codex's read-only sandbox may be unavailable. The run then exits 2; offer WSL or a bypass.
- Related: #525 (CI blocks on pre-existing findings in touched files) affects CI and this round equally.
