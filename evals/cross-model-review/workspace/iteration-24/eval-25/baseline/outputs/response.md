No hook or tool blocked me. I read the four skill files, with SKILL.md only to about byte 29,000 of 40,946 (partway into Phase 2). I ran none of the skill's commands.

## Which form applies
The session used EnterWorktree and a call was refused, so the forms in `codex-pass-assembly.md`, "In an EnterWorktree session", apply:
- One command per Bash call, no `&&` or `;`, no heredoc, no separate `export`. Run from the worktree root that EnterWorktree set, with no `cd`.
- Preflight says every later `$VAR` is shorthand for its already resolved literal. A live `$RUN`, `$MERGE_BASE`, `$BASE` or `$SCOPE` would be empty in a later Bash call anyway.
- `CLAUDE_PLUGIN_ROOT` is empty, so the documented `${CLAUDE_PLUGIN_ROOT:-.claude}` resolves to `.claude`. I write that literal out, because the variable expansion is part of what the check refused.

**Not spelled out by the skill text:** it literalizes `$RUN`-type values and the index prefix, but its EnterWorktree helper form still shows `${CLAUDE_PLUGIN_ROOT:-.claude}`. Replacing it with `.claude` is my resolution. It is the same file, and it matches this repo's `resolve-plugin-root-to-claude-mirror` rule. First confirm each mirrored script exists (for example with Glob); if one is missing, stop and report.

## (1) Write helper with stdin
First use the `Write` tool to put the text in `<session scratchpad>/<file>`. Never write it into the repo or `$RUN`. Then run one Bash call:

```bash
bash ".claude/scripts/git-review-write-run-file.sh" "/tmp/tmp.abc" claude_fresh_eyes.json - < "<absolute session scratchpad>/claude_fresh_eyes.json"
```

The general form is `... "/tmp/tmp.abc" <name> [--append] <part>... - < <scratchpad file>`. For example, the first part of a Phase 1 Codex file (batch 1) would be:

```bash
bash ".claude/scripts/git-review-write-run-file.sh" "/tmp/tmp.abc" review_for_codex.1.md @review.md - < "<absolute session scratchpad>/codex-part1.txt"
```

- Add `@accepted.md` after `@review.md` only if that file exists.
- Later pieces use `--append`, one call each: `@diffs-1/<slice>.codex.diff` (`diffs-1b` after a folder pick), then the closing text on `-`. `-` may appear once per call.
- The name is a bare file name.
- `Write` may prompt. If it does, approve that one call only. The redirected helper call may prompt too; give it no persistent allow rule.

## (2) Planner re-run after a folder pick

```bash
GIT_INDEX_FILE="/tmp/tmp.abc/index" bash ".claude/scripts/git-review-scope-run.sh" "/tmp/tmp.abc" 1b 0123456789abcdef0123456789abcdef01234567 'main' --scope 'plugins/git-kit' --exclude-dir '<picked folder>/'
```

- Use one `--exclude-dir` per pick. The tag is `1b`, so it writes `manifest-1b.json` and `diffs-1b`.
- The index is a prefix assignment. A separate `export` would be lost, and intent-added untracked files would silently drop out.
- If this is a round two, also repeat `--prior-manifest` and `--completed-slice`.
- `|| PLAN_FAILED=1` is dropped: the variable would not survive the call. Read the exit code instead; non-zero means `PLAN_FAILED`, never a pass (ask: unscoped review or stop). Planner exit 2 is different from a refused call, where the planner never ran.
- The wrapper's mirror form is deliberately ungranted, so expect a prompt.

Then cross-check against `manifest-1b.json`, as its own call followed by `Read`:

```bash
GIT_INDEX_FILE="/tmp/tmp.abc/index" git diff --no-renames --name-only 0123456789abcdef0123456789abcdef01234567 -- 'plugins/git-kit' > "/tmp/tmp.abc/changed.names"
```

## (3) Accepted-findings brief

```bash
python3 -I ".claude/scripts/git-review-accepted-findings.py" brief --run-dir "/tmp/tmp.abc"
```

- Run it from `REPO_ROOT`, with no index prefix.
- The documented command has no `:-.claude` default, so unmodified it would resolve to `/scripts/...` and fail.
- A helper failure (exit 2) is an inspection limit, not a stop. A harness refusal is different; see the last section.
- It writes `/tmp/tmp.abc/accepted.md` only if there is something to brief. Report any `not applied:` lines in `inspection_limits`.

## Where each value comes from

| Value | Source |
|---|---|
| `/tmp/tmp.abc` (`RUN`) | Preflight's closing `echo` (from `mktemp -d`). Never re-create it |
| `/tmp/tmp.abc/index` | Literal `RUN` + `/index`, the throwaway index Preflight seeded |
| `0123...4567` | `MERGE_BASE`. The documented closing `echo` list does not name it, though it appears inside the echoed `DIFF_STR`, just before any `-- <scope>`. Here the task supplies it |
| `main` | `BASE` from the `echo` (user's request, else the default) |
| `plugins/git-kit` | `SCOPE` resolved from the user's request. Not in the `echo` list by name (`DIFF_STR` contains it). If unset, omit `--scope` and `-- ...` entirely |
| `.claude` | The `:-.claude` default, relative to the worktree root |
| `1b` | Fixed tag for the folder-pick re-run |
| Picked folder | User's `AskUserQuestion` pick from `candidate_dirs` in `manifest-1.json`, only if it matches `^[A-Za-z0-9_][A-Za-z0-9._-]*/$` |
| Run-file name | Fixed by the skill |
| Scratchpad path | The session's own scratchpad. If there is none, stop and report |

No text from the diff, Codex output or a `$RUN` file becomes shell syntax. Manifest text enters a command only through the checked folder pattern (or the checked slice-name pattern).

## If SCOPE contains a single quote
Stop and ask the user for a different scope. Do not escape it, re-quote it, switch to double quotes or drop the scope. The documented stop covers writing the Preflight script, so such a value should never reach these calls; the text does not restate it for later calls, and I apply the same rule there. It also covers a newline, a leading `-`, and the same cases in `BASE`.

## If it is still refused
Stop and report the exact call and the refusal. Do not try another way: no raw redirect or `Write` into `$RUN`, no `cd` elsewhere, no wrapper script for these calls (the script form is for Preflight only), no different command, no disabled isolation, and no skipping the step as if it passed. The same applies when the write helper itself refuses (bad `$RUN`, or a part outside it): that is a failed write, so stop and report it. A normal permission prompt is not a refusal; approve that one call only.
