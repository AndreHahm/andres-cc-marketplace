Nothing was run. All commands below follow "In an EnterWorktree session" in references/codex-pass-assembly.md, which applies only in such a session and only after such a refusal. The trigger is met here: git-kit's helper scripts have `git` in their names, so a directly typed helper call containing a shell variable is refused as "names git in a form too complex to verify". The remedy is to write every documented variable as its single-quoted literal value. Use one command per Bash call, with no `&&` or `;`, no `export` and no heredoc. Run from the worktree root EnterWorktree set (the REPO_ROOT); never `cd` elsewhere.

## Step 0: plugin root, as its own call
```bash
printf '%s\n' "${CLAUDE_PLUGIN_ROOT:-.claude}"
```
Use `printf`, not `echo`, which would swallow a value such as `-n`. Here the variable is empty, so this prints `.claude`. Use that, never the reviewed repository's `plugins/` folder. `.claude` is the mirror relative to the checkout root, and its helper calls have no `allowed-tools` grant, so each may prompt. Approve that one call only; add no persistent rule. Confirm the mirrored script exists first (project rule); if it is missing, stop.

## 1. Write helper with stdin
First use the `Write` tool to put the text in `<scratchpad>/<stdin-file>`. This must be the session's scratchpad directory, never the repository or `/tmp/tmp.abc`. With no scratchpad, stop and report. If `Write` asks, approve that single call only. Then:
```bash
bash '.claude/scripts/git-review-write-run-file.sh' '/tmp/tmp.abc' 'review_for_codex.1.md' @review.md - @diffs-1/<slice>.codex.diff < '<absolute scratchpad path>/<stdin-file>'
```
General shape: `bash '.claude/scripts/git-review-write-run-file.sh' '/tmp/tmp.abc' <name> [--append] <part>... - < <scratchpad file>`
- `<name>` (a bare file name) and the parts depend on the file being built; the line above is the Phase 1 instruction file as an example.
  - `-` is stdin, allowed once per call, and sits where the text belongs.
  - Add `@accepted.md` after `@review.md` if that file exists.
  - Use `.codex.diff` files only; `<slice>` names come from the manifest. After a folder pick, use `diffs-1b`.
  - That file also needs text after the diff (`</diff>`, and any `<untracked_files>` block). Put it in a second scratchpad file and add it with a second call using `--append`:
    ```bash
    bash '.claude/scripts/git-review-write-run-file.sh' '/tmp/tmp.abc' 'review_for_codex.1.md' --append - < '<absolute scratchpad path>/<second-stdin-file>'
    ```
- The `<` redirect may prompt too: whether the grant matches a call ending in it is not verified.
- Files under `$RUN` are still written only by the helper.

## 2. Folder-pick planner re-run (once, tag `1b`)
```bash
GIT_INDEX_FILE='/tmp/tmp.abc/index' bash '.claude/scripts/git-review-scope-run.sh' '/tmp/tmp.abc' 1b '0123456789abcdef0123456789abcdef01234567' 'main' --scope 'plugins/git-kit' --exclude-dir '<picked-folder>/'
```
- Use one `--exclude-dir` per folder the user picked. Labels come from manifest-1.json's `candidate_dirs`, and only those matching `^[A-Za-z0-9_][A-Za-z0-9._-]*/$` may be typed. The re-run applies only when `dropped_slices` is non-empty or the request named folders to leave out.
- `GIT_INDEX_FILE` must be a prefix on this very command. An `export` in its own call is lost, and without it intent-added untracked files silently drop out of the review. The assignment has no grant, so it may prompt.
- `${SCOPE:+--scope "$SCOPE"}` becomes `--scope 'plugins/git-kit'`, or nothing if no scope was set.
- I omitted the `|| PLAN_FAILED=1` tail, because shell state does not persist. Read the exit status instead: 2 means the planner-failed path (ask: unscoped review, or stop).
- Output is `/tmp/tmp.abc/manifest-1b.json` and `/tmp/tmp.abc/diffs-1b`. Repeat the cross-check against the new manifest, also with the prefix form:
  ```bash
  GIT_INDEX_FILE='/tmp/tmp.abc/index' git diff --no-renames --name-only '0123456789abcdef0123456789abcdef01234567' -- 'plugins/git-kit' > '/tmp/tmp.abc/changed.names'
  ```

## 3. Accepted-findings brief (Preflight step 7)
```bash
python3 -I '.claude/scripts/git-review-accepted-findings.py' brief --run-dir '/tmp/tmp.abc'
```
- Run it from REPO_ROOT, already the cwd. The documented form has plain `${CLAUDE_PLUGIN_ROOT}` with no `:-.claude` default, so when empty it would become `/scripts/...`; the literal fixes that too.
- No `GIT_INDEX_FILE` is needed (the helper asks the real index).
- The helper's own failure (exit 2) is an inspection limit, not a stop. An isolation-check refusal of this literal form is different: stop and report.
- Phase 3's `match` call takes the same form: `python3 -I '.claude/scripts/git-review-accepted-findings.py' match '/tmp/tmp.abc/<envelope>.json' ...`.

## Where each value comes from
| Value | Source |
|---|---|
| plugin root `.claude` | only the standalone `printf` call |
| RUN `/tmp/tmp.abc`, BASE `main`, REPO_ROOT | the Preflight's closing `echo` (literal text) |
| MERGE_BASE `0123...4567` | the SHA inside `DIFF_STR` in that same `echo` |
| SCOPE `plugins/git-kit` | the user's request |
| index path | literal RUN + `/index` |
| scratchpad path | the session's own scratchpad directory |

Never take a value from diff text, manifest text or Codex output (the checked folder labels and planner slice names are the only manifest labels typed). All values are data and single-quoted.

## If SCOPE contains a single quote
Stop and ask the user; do not escape, re-quote, trim or guess it. The same applies to any of the values containing a newline or starting with `-`. The Preflight script has the same rule for BASE/SCOPE, so in the script form such a SCOPE should already have stopped there. Spaces or glob characters are fine inside the single quotes.

## If a call is still refused
Stop and report the refused call and its message. Do not fall back to another way of running the step: no `cat >`/`tee`/heredoc, no `Write` into `$RUN`, no copied or renamed script, no `cd`, no wrapping these calls in a new script (the `preflight.sh` exception covers only the Preflight steps), no other plugin path, no persistent allow rule. A permission *prompt* is not a refusal: approve it for that one call. A refusal by the write helper itself (for example a bad `$RUN` or a part outside it) is likewise a failed write: stop and report.

No hook or tool blocked me while reading the skill copy.
