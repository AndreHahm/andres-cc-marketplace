# cross-model-review dry run: Preflight, the Phase 1 instruction file and the Write tool

Source: `plugins/git-kit/skills/cross-model-review/SKILL.md` and `references/codex-pass-assembly.md` (the plugins/ copy). Nothing was run.

## Short answer

- **Preflight:** one chained Bash call, written inline. I don't write it to a scratch script.
- **Phase 1 instruction file:** I build it with `scripts/git-review-write-run-file.sh`. The "do not run `git diff`" line goes in through stdin as a quoted heredoc.
- **The Write tool is not used anywhere in this run.** The only exception the skill allows for `Write` applies only after `EnterWorktree` and a refused Bash call. Neither happened here. The output file for this eval is a test-harness artifact, not part of the review.

## Why the scratch-script idea does not apply

SKILL.md (intro): "This skill has no `Write` grant (it cannot be limited to a path)". Every file the model writes goes through `git-review-write-run-file.sh` into `$RUN`. Its one stated exception: "After `EnterWorktree`, an isolation-check refusal allows `Write` to the session scratchpad only."

`references/codex-pass-assembly.md`, "In an EnterWorktree session", narrows this further: "In such a session only, and only after such a refusal, use these forms". Both conditions have to hold:

1. The session used `EnterWorktree`. **It did not.** The session started directly in the repository.
2. Claude Code's worktree-isolation check refused a Bash call. **None was refused.**

Neither holds, so the `<scratchpad>/preflight.sh` form is not available. Readability is not a reason to use it. The `Boundaries` section explains why `bash <scratchpad>/preflight.sh` is kept out of the grants: it would need `Bash(bash:*)`, which also admits `bash -c` and any script, and one approval would cover every command inside it.

## How I run the Preflight

Per SKILL.md's Preflight section, I run the Inputs block and steps 1-6 as **one chained Bash invocation**: `&&` between the steps, one tool call. Bash calls share no shell state, so splitting the chain would lose `$RUN`, `$MERGE_BASE`, `DIFF` and the exported `GIT_INDEX_FILE`.

Before the call, I resolve `BASE` (default `main`) and `SCOPE` (default none) from the request. The chain, in order:

1. The Inputs block:
   - `umask 077`, `BASE`, `MERGE_BASE=$(git merge-base "$BASE" HEAD)`.
   - `UNSCOPED_CHANGED_FILES`, then the `PLANNER_TOUCHED` grep and its stop line. If it fires, I ask through `AskUserQuestion` and re-run the chain only on an explicit yes, with `PLANNER_APPROVED=1`.
   - `UNTRACKED_FILES`, `RUN=$(mktemp -d)`, `export GIT_INDEX_FILE="$RUN/index"`.
   - `git-review-copy-index.sh`, setting `INDEX_COPY_FAILED` on failure.
   - `git-review-intent-add.sh`, setting `INTENT_ADD_REFUSED` on a refusal.
   - The `DIFF` argv array and `DIFF_STR`.
2. Step 1: run the planner through `git-review-scope-run.sh` (setting `PLAN_FAILED` on failure), then `"${DIFF[@]}" > "$RUN/full.diff"; DIFF_STATUS=$?`.
3. Steps 2-4: the batch and eligibility work rests on the manifest, and `REPO_ROOT=$(git rev-parse --show-toplevel)`.
4. Step 5: two `git show "$BASE:plugins/git-kit/skills/cross-model-review/prompts/{review,refute}.md" > "$RUN/..." 2>/dev/null || true` commands.
5. Step 6: the `DISPATCHER_TOUCHED` grep, with `|| true`.
6. A closing `echo` of `BASE`, `REPO_ROOT`, `RUN`, `DIFF_STR`, `DISPATCHER_TOUCHED`, `PLANNER_TOUCHED`, `PLAN_FAILED`, `DIFF_STATUS`, the manifest path, `TARGET_PATHS`, `UNTRACKED_FILES`, `INDEX_COPY_FAILED`, `INTENT_ADD_REFUSED`, and whether `review.md` and `refute.md` came out non-empty.

**Permissions.** `git diff`, `git show` and the `export GIT_INDEX_FILE` assignment are deliberately left out of `allowed-tools`, so they prompt. In this repo's own sessions `CLAUDE_PLUGIN_ROOT` is empty, so the `:-.claude` mirror form selects the `.claude/` copy of the helpers. That form is also ungranted and prompts. You approve each prompt once for this run; don't add a persistent allow rule.

**After the chain returns,** I substitute the echoed literal values into every later call. Every `$VAR` from then on means that literal string. Then I act on the result:

- A non-zero `DIFF_STATUS` is a Git error: report it and ask for a valid `BASE`.
- Exit 0 with an empty `full.diff` means there is nothing to review: stop.
- `INTENT_ADD_REFUSED=1` overrides both: the diff is unreliable, so report the helper's error and stop.
- `PLAN_FAILED=1` is never a pass. Follow the fallback in `scoped-review.md` section 1.
- If `review.md` or `refute.md` came out empty, ask through `AskUserQuestion` whether to use the plugin's working-tree prompts. On a yes, materialize them with `git-review-write-run-file.sh "$RUN" review.md @plugin:review` (and `refute.md` with `@plugin:refute`), still not with `Write`, and set `REVIEW_UNVERIFIED` / `REFUTE_UNVERIFIED`.

## How I write the Phase 1 instruction file

`references/codex-pass-assembly.md`, "Phase 1 Codex instruction file". Per batch `<N>`, the content of `$RUN/review_for_codex.<N>.md` is, in order:

1. The trusted `$RUN/review.md`.
2. A line telling Codex **not to run `git diff` or any shell command to fetch the diff**. Issue #78: a diff that Codex ran itself failed on large changes, while an embedded diff succeeded.
3. Each of the batch's `.codex.diff` files, wrapped as `\n<diff>\n<diff text>\n</diff>\n`. I never use a `.diff` file, which is Claude's wider diff.
4. Only if `$UNTRACKED_FILES` contains paths in this batch: an `<untracked_files>` block. It names only those paths, each having passed the pattern check. It tells Codex to read each one with a read-only file tool, never a shell command, and ends with the untrusted-data sentence.

I write it with the write helper. My own text goes in as stdin through a **quoted heredoc**, so nothing expands. The helper joins parts verbatim, so I put the newlines and `<diff>` tags in the stdin text. Because stdin is allowed once per call, I build the file across several calls: the first without `--append`, the rest with it. For example:

```bash
bash ".claude/scripts/git-review-write-run-file.sh" "<literal RUN>" review_for_codex.1.md @review.md - <<'EOF'

Do not run `git diff` or any shell command to fetch the diff; the diff is embedded below.

<diff>
EOF
bash ".claude/scripts/git-review-write-run-file.sh" "<literal RUN>" review_for_codex.1.md --append @diffs-1/<slice>.codex.diff - <<'EOF'
</diff>
EOF
```

There is one `--append` call per further `.codex.diff` slice. There is a final `--append` with the `<untracked_files>` block if needed.

- **Path form.** `.claude/scripts/...` is the `${CLAUDE_PLUGIN_ROOT:-.claude}` form resolved for this repo's session. Per the rule on resolving the plugin root, it runs from the repo root.
- **The heredoc names `git`.** That is fine here: the "feeds bash text naming git" refusal is described only for sessions after `EnterWorktree`. If the helper refuses (symlinked `$RUN`, a part outside `$RUN`, and so on), that is a failed write: stop and report it. Never fall back to the Write tool or any other writer.

I then dispatch with `--reviewer-type fresh-eyes-reviewer --instruction-file "$RUN/review_for_codex.<N>.md" --target-paths "$TARGET_PATHS" --dispatch-id "cross-model-review-$(date +%s)-fresh-eyes-codex-<N>"`, through the Step 1 bridge form with `CODEX_KIT_REVIEW_REPO_ROOT` and `--cwd`. Before that, I ask the mandatory First-Send Confirmation. I save the envelope to `$RUN/codex_fresh_eyes.<N>.json`.

## Is the Write tool used anywhere in this run?

**No.** Every file written during the review is written one of two ways:

- **By the Preflight chain's own shell redirects**, to fixed names under `$RUN`: `full.diff`, `review.md` and `refute.md`. The planner wrapper writes `manifest-1.json` and `diffs-1/`.
- **By `git-review-write-run-file.sh`**: `review_for_codex.<N>.md`, `claude_fresh_eyes.json`, `claude_challenger.json`, `challenger_instructions_for_codex.<N>.md`, and any `@plugin:` fallback prompts.

No `preflight.sh` and no scratchpad stdin files are created. Those exist only in the EnterWorktree-after-refusal path. Nothing is written inside the repository.
