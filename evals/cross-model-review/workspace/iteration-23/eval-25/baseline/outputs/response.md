Nothing was run; no hook or tool blocked me. Sources: arm-b's SKILL.md, codex-pass-assembly.md, scoped-review.md and accepted-findings.md, plus this repo's loaded rule on resolving an empty plugin root to the `.claude` mirror.

## What to do after the refusal

The documented variables are shorthand. SKILL.md's Preflight section says Bash calls share no shell state, and every later `$VAR` must be replaced by the concrete value Preflight echoed. So retype each call with literals:
- One command per Bash call. No `&&`, `;`, `export`, heredoc or leftover `$VAR` / `${...:-...}`.
- Run from the session's worktree root, with no `cd`. The planner wrapper requires the cwd to be the work tree root, and the `.claude/...` paths are relative to it.
- Confirm that the mirrored script exists before using it.

### (1) Write helper with stdin
First use the `Write` tool to put the text in the session scratchpad, e.g. `<scratchpad>/claude_fresh_eyes.json`. Never `Write` into the repository or `/tmp/tmp.abc`. Then run one standalone call:

```bash
bash .claude/scripts/git-review-write-run-file.sh /tmp/tmp.abc claude_fresh_eyes.json - < '<scratchpad>/claude_fresh_eyes.json'
```

- General shape: `... /tmp/tmp.abc <name> [--append] <part>... - < '<scratchpad file>'`.
- `<scratchpad>` is the session's literal absolute scratchpad path.
- `-` (stdin) may be used once per call. Other parts are `@<path inside RUN>`, `@plugin:review` and `@plugin:refute`.
- If the Phase 1 Codex file needs stdin text in several places, make the first call without `--append` and later ones with it.
- Example: `bash .claude/scripts/git-review-write-run-file.sh /tmp/tmp.abc review_for_codex.1.md @review.md @accepted.md - < '<scratchpad>/p1-head.txt'`. Include `@accepted.md` only if it exists. Then append `@diffs-1b/<slice>.codex.diff` (`diffs-1` if there was no re-run) and the closing text.
- The call may prompt. Approve that one call only. The same applies to the `Write`: no session-wide or accept-edits approval.

### (2) Folder-pick planner re-run
This runs only if the plan has `dropped_slices` or the request named folders to leave out. It runs once, with tag `1b`:

```bash
GIT_INDEX_FILE='/tmp/tmp.abc/index' bash .claude/scripts/git-review-scope-run.sh /tmp/tmp.abc 1b 0123456789abcdef0123456789abcdef01234567 'main' --scope 'plugins/git-kit' --exclude-dir '<picked-folder/>'
```

- Add one `--exclude-dir` per folder the user picked. If no scope was set, drop `--scope`.
- The index must be a prefix assignment. An `export` in its own call is lost, and without it intent-added untracked files silently drop out of the review.
- The script writes `/tmp/tmp.abc/manifest-1b.json` and `/tmp/tmp.abc/diffs-1b`, never overwriting. It prompts by design, because neither the mirror path nor the prefix assignment is granted.
- `PLANNER_TOUCHED` still governs: if it was 1, the user's earlier explicit yes is required.
- A non-zero exit means the plan failed. Ask: unscoped review, or stop. It is never a pass.
- Then repeat the manifest cross-check in its own call, and `Read` the results:

```bash
GIT_INDEX_FILE='/tmp/tmp.abc/index' git diff --no-renames --name-only 0123456789abcdef0123456789abcdef01234567 -- 'plugins/git-kit' > /tmp/tmp.abc/changed.names
```

### (3) Accepted-findings brief
```bash
python3 -I .claude/scripts/git-review-accepted-findings.py brief --run-dir /tmp/tmp.abc
```

- Run it from REPO_ROOT (the worktree root).
- The documented command has no `:-.claude` default, so with an empty plugin root it would become `/scripts/...` and fail. That is why the mirror path must be written out.
- No `GIT_INDEX_FILE`: the helper checks the real index and `HEAD`.
- It writes `/tmp/tmp.abc/accepted.md` only when there is something to brief. It may prompt, since the grant names the plugin-root form.
- Report `not applied:` lines and stderr notes as inspection limits.

## Where each value comes from

| Value | Source |
|---|---|
| `/tmp/tmp.abc` (RUN) | Preflight's closing `echo`, i.e. its `mktemp -d`; never re-created |
| `/tmp/tmp.abc/index` | RUN + `/index`, seeded by Preflight |
| `0123…4567` (MERGE_BASE) | The value given as resolved by Preflight. The documented echo list names DIFF_STR, which contains it, not MERGE_BASE itself. Take it from there; do not recompute against another base |
| `main` (BASE) | User request or default, echoed by Preflight |
| `plugins/git-kit` (SCOPE) | User request (no default) |
| `.claude` | The `${CLAUDE_PLUGIN_ROOT:-.claude}` default, written out because the variable is empty; it resolves to the worktree's mirror |
| `1b` | Fixed tag for the folder-pick re-run |
| `--exclude-dir` | The user's picks from the manifest's `candidate_dirs`, only labels matching `^[A-Za-z0-9_][A-Za-z0-9._-]*/$`; others are "not offered for exclusion (unusual name)" |
| Output file names | Fixed by the skill, matching `[A-Za-z0-9][A-Za-z0-9._-]*` |
| stdin text | Scratchpad file written with `Write` |

Never type a manifest file path, diff text or Codex output into a command. `@diffs-*/<slice>.codex.diff` uses only planner slice names.

## If SCOPE contains a single quote
**Stop and ask the user for a different scope.** Do not escape it, switch to double quotes, drop it or silently widen the scope. The same applies to a newline or a leading `-`, and to BASE. The skill states this rule for the Preflight script's assignments. I apply it equally to the single-quoted literal in (2), because SCOPE and BASE are data, never shell syntax. A SCOPE like that should already have stopped a scripted Preflight. Calls (1) and (3) do not use SCOPE.

## If it is still refused
**Stop and report it**: the exact call and the refusal text. No other route: no heredoc retry, `python -c`, `cp`, direct `Write` into RUN, wrapper script for these calls (the script form is for Preflight only), `cd` to the main checkout, another script path or disabling the sandbox. If the mirrored file is missing or the session has no scratchpad, also stop and report.

- **Write helper:** its own refusal (bad RUN, part outside RUN) is also a failed write, so stop.
- **Planner:** a non-zero exit after it actually ran is different from a refusal; it goes to the ask above.
- **Brief:** a failure after it ran (e.g. exit 2) is only an inspection limit and the review continues. A refusal before it ran falls under the "still refused: stop and report" rule.

## Gaps in the skill text
- Its EnterWorktree section still shows the helper call with `${CLAUDE_PLUGIN_ROOT:-.claude}` and `"$RUN"`, and does not name this "names git in a form too complex" refusal. The fully literal forms are my application of its "substitute the concrete string" instruction.
- It shows no literal command for (2) or (3), and does not mention the mirror path for (3).
