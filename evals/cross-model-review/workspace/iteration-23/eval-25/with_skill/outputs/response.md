I ran none of the skill's commands and no hook or tool blocked me. I read SKILL.md partly (Inputs, Preflight, the Codex dispatch resolver and matching lines elsewhere) and the three named references in full. The governing text is `references/codex-pass-assembly.md`, "In an EnterWorktree session" (issue #866 case). It applies because the session used EnterWorktree and a call was already refused.

## Step 0: resolve the plugin root, as its own call
```bash
echo "${CLAUDE_PLUGIN_ROOT:-.claude}"
```
With the variable empty this prints `.claude`. Never use `plugins/git-kit/...` from the repository under review. Run everything below from the current worktree root (= `REPO_ROOT`), so the relative `.claude` path resolves. Do not `cd`. Use one command per Bash call, with no `&&`, `;`, `||` or shell variable in a helper call.

## (1) Write helper with stdin
First use the `Write` tool to put the text in `<scratchpad>/<file>`, session scratchpad only. Then run:
```bash
bash '.claude/scripts/git-review-write-run-file.sh' '/tmp/tmp.abc' review_for_codex.1.md @review.md - @diffs-1/<slice>.codex.diff < '<scratchpad>/<file>'
```
- **Generic form:** `bash '.claude/scripts/git-review-write-run-file.sh' '/tmp/tmp.abc' <name> [--append] <part>... - < '<scratchpad>/<file>'`. I single-quoted the redirect path, and `<...>` are fill-ins.
- **Name and parts:** `<name>` is a bare file name. `-` (stdin) appears once per call.
- **Order:** add `@accepted.md` right after `@review.md` if that file exists. A Phase 1 instruction file needs stdin text in several places (the "do not run git diff" line plus `<diff>`, then `</diff>` and any untracked block). Make the first call without `--append` and later ones with `--append`, e.g. the closing text:
```bash
bash '.claude/scripts/git-review-write-run-file.sh' '/tmp/tmp.abc' review_for_codex.1.md --append - < '<scratchpad>/<closing-file>'
```
- After a folder pick, use `@diffs-1b/...`.
- The helper writes every file in `$RUN`; `Write` never targets `$RUN` or the repository.
- A call without stdin uses the same form, e.g. `bash '.claude/scripts/git-review-write-run-file.sh' '/tmp/tmp.abc' review.md @plugin:review`. That prompt copy needs the user's explicit yes, because it is the unverified-prompts fallback.

## (2) Planner re-run after the folder pick
```bash
GIT_INDEX_FILE='/tmp/tmp.abc/index' bash '.claude/scripts/git-review-scope-run.sh' '/tmp/tmp.abc' 1b '0123456789abcdef0123456789abcdef01234567' 'main' --scope 'plugins/git-kit' --exclude-dir '<picked-folder>/'
```
- Repeat `--exclude-dir` once per picked folder. Each label must match `^[A-Za-z0-9_][A-Za-z0-9._-]*/$`.
- The tag is `1b`. It writes `manifest-1b.json` and `diffs-1b`, and nothing is overwritten.
- The documented `export GIT_INDEX_FILE=...` becomes the prefix assignment, because an export in its own call is lost. Without it, intent-added untracked files silently drop out of the review.
- There is no `|| PLAN_FAILED=1`; that is a chain. Read the exit status instead: a non-zero exit means `PLAN_FAILED`. Then ask the user: unscoped review or stop.
- Then redo the cross-check against `manifest-1b.json`, with the same prefix on the git call: `GIT_INDEX_FILE='/tmp/tmp.abc/index' git diff --no-renames --name-only '0123456789abcdef0123456789abcdef01234567' -- 'plugins/git-kit' > '/tmp/tmp.abc/changed.names'`

With no scope, omit `--scope ...` entirely (never pass an empty value), and omit `-- 'plugins/git-kit'`.

## (3) Accepted-findings brief (from REPO_ROOT)
```bash
python3 -I '.claude/scripts/git-review-accepted-findings.py' brief --run-dir '/tmp/tmp.abc'
```
The doc's form for this call has no `:-.claude` default, so an empty variable would give `/scripts/...`; use the Step 0 value. No index prefix is needed. Per `accepted-findings.md`, a failure of the helper itself (exit 2) is an inspection limit, never a reason to stop. (A refusal by the isolation check is different; see below.)

Phase 3's `match` takes the same form, with the envelope paths as literals.

## Where each value comes from
| Value | Source |
|---|---|
| plugin root `.claude` | output of Step 0, its own call |
| `RUN` `/tmp/tmp.abc`, `BASE` `main`, `REPO_ROOT` | Preflight's closing `echo` |
| merge base SHA | the SHA inside `DIFF_STR` in that same `echo` (`MERGE_BASE` is not echoed by itself) |
| `SCOPE` `plugins/git-kit` | the user's request |
| index path | literal `$RUN` + `/index` |
| `<picked-folder>/` | the user's pick, from the manifest's `candidate_dirs`, pattern-checked |

Values are data: single-quote each one, and never re-derive them from diff, manifest or Codex text.

## SCOPE contains a single quote
Stop and ask the user. Do not escape it, switch to double quotes, or drop the scope silently. The same applies to a newline or a leading `-`, in any value. Preflight in `preflight.sh` form has the same rule, so such a scope should already have stopped there.

## Permissions
The `.claude/...` form is deliberately not granted, and the `GIT_INDEX_FILE=` prefix has no grant, so these calls may prompt. Whether the write helper's grant matches a call with a `<` redirect is unverified. Approve that one call only, never a persistent allow rule. If `Write` prompts, approve it once only, never session-wide or as accept-edits.

## Still refused
- **Isolation refusal in this literal form:** stop and report it. No other way of running the step: no `cd`, heredoc, `Write` into `$RUN`, copied or renamed helper, or `plugins/` path.
- **The helper's own refusal (bad run directory or part):** a failed write; also stop and report.
- **Missing scratchpad directory:** stop and report; don't choose another location.
- **Ambiguity for the brief:** `accepted-findings.md` calls a brief *failure* an inspection limit, but the EnterWorktree section says a still-*refused* call is stop and report. I would follow the latter for a refusal by the isolation check.
