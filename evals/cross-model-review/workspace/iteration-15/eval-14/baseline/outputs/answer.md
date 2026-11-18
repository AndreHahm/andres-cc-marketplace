# Batch 1, Phase 1 Codex instruction file after an EnterWorktree refusal (baseline skill copy)

Source: the `plugins/git-kit/skills/cross-model-review/` copy given for this baseline: `SKILL.md`,
`references/codex-pass-assembly.md` ("Writing a run file", "Phase 1 Codex instruction file") and
`references/scoped-review.md` sections 3 and 4.

**Coverage gap up front:** this copy of the skill says nothing about EnterWorktree, or about a
refusal that says "this command feeds bash text naming git in a plain command, which cannot be shown to
stay inside the worktree". It does not mention a workaround for writing a stdin part whose text contains
the word `git`, and it does not say how environment variables should reach `node` when a separate
`export` line is refused. Everything below comes from what the skill does say. Where the skill is
silent, I say so instead of making up a workaround.

## 1. What the refusal means under this skill

`codex-pass-assembly.md` ("Writing a run file") says every file the model writes goes through one
helper, `bash "${CLAUDE_PLUGIN_ROOT:-.claude}/scripts/git-review-write-run-file.sh" "$RUN" <name> ...`,
with a quoted heredoc as the stdin part. It also says: **"A refusal is a failed write: stop and report
it, never fall back to another way of writing the file."**

The skill does not say whether this applies only to a refusal by the helper itself or also to a refusal
by the harness. Read literally, the instruction file was not written, so the write failed. The skill
gives exactly one way to write a run file, so I do not invent another.

## 2. How I write the instruction file now

The skill allows nothing beyond the helper. Within that, the only change I can make is one that keeps
the required content. These are the parts the helper accepts:

- `@plugin:review`: the trusted `review.md` prompt. It does not need to be typed into stdin.
- `@diffs-1/<slice>.codex.diff`: each `.codex.diff` file for the batch, as a file part inside `$RUN`.
- `-`: stdin from a quoted heredoc, once per call. Use `--append` to build the file over several calls.

The file must still contain, in this order: `review.md`; a line telling Codex not to run `git diff` or
any shell command to fetch the diff; then `\n<diff>\n<diff text>\n</diff>\n` for the batch's
`.codex.diff` files; and the `<untracked_files>` block if batch 1 has untracked paths. The output file is
`review_for_codex.1.md`. Here is the call sequence the skill describes:

```bash
bash "${CLAUDE_PLUGIN_ROOT:-.claude}/scripts/git-review-write-run-file.sh" "$RUN" review_for_codex.1.md @plugin:review - @diffs-1/<slice>.codex.diff - <<'EOF'
...
EOF
```

The helper accepts only one `-` per call. So, in practice:

1. First call (no `--append`): `@plugin:review`, then `-` with the heredoc. The heredoc holds the
   "do not run git diff..." line and `\n<diff>\n`.
2. `--append` call: `@diffs-1/<slice>.codex.diff` for each slice in batch 1.
3. `--append` call: `-` with a heredoc holding `\n</diff>\n`, plus the `<untracked_files>` block if
   there is one.

Step 1's heredoc has to name `git diff`, because the skill requires that sentence. That is exactly the
content that was refused. **The skill offers no sanctioned way to say this without the word `git`.** It
does not allow rewording the required instruction, and it does not allow moving it into a file part
from some other source. Dropping the sentence would break the Phase 1 contract, so I would not do it.

Correct action under this skill: **treat the refused write as a failed write, stop, and report it to
the user**. The report names the helper call, the refusal text, and the fact that
`review_for_codex.1.md` was not written. Without the instruction file, batch 1 has no Codex Phase 1
dispatch. It falls under the resolver's step 3 handling: `AskUserQuestion`, asking whether to proceed
with batch 1 reviewed by Claude only (Medium confidence, disclosed in `inspection_limits`) or to stop.
Other batches still dispatch if their own writes succeed.

(The scenario also says the first dispatch for batch 1 timed out. That assumes the file was written
anyway, for example through an allowed form or after the user intervened. Sections 3 and 4 describe
the shapes for that case.)

## 3. Codex dispatch command shape (batch 1, Phase 1)

From `SKILL.md`'s resolver, Step 1 (the sandboxed bridge). The env var goes on a separate `export` line
before `node`:

```bash
export CODEX_KIT_REVIEW_REPO_ROOT="$REPO_ROOT"
node plugins/codex-kit/skills/codex-review-bridge/scripts/bridge-invoke.mjs \
  --reviewer-type fresh-eyes-reviewer \
  --instruction-file "$RUN/review_for_codex.1.md" \
  --execution-profile read-only \
  --target-paths "$TARGET_PATHS" \
  --dispatch-id "cross-model-review-$(date +%s)-fresh-eyes-codex-1" \
  --cwd "$REPO_ROOT"
```

Here `RUN=/tmp/tmp.abc` and `REPO_ROOT=/repo/.claude/worktrees/x`. The envelope is saved to
`$RUN/codex_fresh_eyes.1.json`.

- `CODEX_KIT_REVIEW_REPO_ROOT` reaches the node process because it is exported in the same shell before
  `node` runs. The bridge has no `--repo-root` flag. Never pass `--repo-root` to `bridge-invoke.mjs`,
  because the bridge silently ignores it. `--cwd "$REPO_ROOT"` is also passed.
- The `export CODEX_KIT_REVIEW_*` lines are deliberately left out of `allowed-tools` (Boundaries), so
  each one raises a permission prompt.
- This assumes the First-Send Confirmation (`AskUserQuestion`) has already been answered "Send to Codex
  for this run" before the first real dispatch. The dispatch count it states includes a possible
  timeout retry for each batch.

## 4. Timeout retry command shape

`scoped-review.md` section 4: a `timeout` typed failure on batch 1 means asking via `AskUserQuestion`
whether to retry **that batch once** or leave it to Claude alone this round. Retry only on an explicit
yes. The retry sets `export CODEX_KIT_REVIEW_TIMEOUT_MS=480000` before the `node` call:

```bash
export CODEX_KIT_REVIEW_REPO_ROOT="$REPO_ROOT"
export CODEX_KIT_REVIEW_TIMEOUT_MS=480000
node plugins/codex-kit/skills/codex-review-bridge/scripts/bridge-invoke.mjs \
  --reviewer-type fresh-eyes-reviewer \
  --instruction-file "$RUN/review_for_codex.1.md" \
  --execution-profile read-only \
  --target-paths "$TARGET_PATHS" \
  --dispatch-id "cross-model-review-$(date +%s)-fresh-eyes-codex-1" \
  --cwd "$REPO_ROOT"
```

Both variables reach `node` as exported shell environment in the same Bash call. The skill describes
only the `export ...` then `node` form. It gives no alternative, such as a `VAR=value node ...` prefix
or `env`, for when an `export` line is refused.

- If the retry succeeds, batch 1 is finished and goes on to its Phase 2 challenger dispatch.
- If the retry fails or is declined, batch 1 is **unfinished**: its Claude findings stay single-sided
  (Medium) and this is disclosed in `inspection_limits`. Other batches are dispatched either way.

## 5. What I must not do

- Never write the instruction file another way after the helper call is refused. That rules out the
  `Write` tool (the skill has no `Write` grant), a shell redirect, `cat >`, `printf >`, a `tee` to
  `$RUN`, and similar ("never fall back to another way of writing the file").
- Never drop or water down the "do not run `git diff` or any shell command" instruction, and never
  replace the embedded diff with a command for Codex to run (issue #78).
- Never use a `.diff` file in a Codex-bound file. Use only the `.codex.diff` files. Never type a manifest
  path into a diff command.
- Never pass `--repo-root` to `bridge-invoke.mjs`, and never mix the two scripts' flag shapes.
- Never enable the `codex-windows-guardrails` fallback yourself.
- Never retry a timeout without an explicit yes, never retry more than once per batch, and never skip
  other batches because batch 1 timed out.
- Never discard envelopes from batches that already finished.
- Never add a persistent allow rule for the `export CODEX_KIT_REVIEW_*` lines.

## 6. If a form is still refused

The skill's general rule applies: a refusal is a failure, so stop and report it, and never switch to a
different command or mechanism. Specifically:

- **Write helper refused** (any form): the instruction file was not written, so stop and report it. Batch
  1 gets no Codex pass and goes through the resolver step 3 `AskUserQuestion` (Claude-only for this batch,
  or stop).
- **Dispatch or retry command refused** (for example the `export` line or the `node` call): the skill
  documents no other way to pass the variables. Report the refusal. Treat batch 1 as a Codex failure
  (resolver step 3, or unfinished after a timeout), disclose it in `inspection_limits`, and keep every
  finished envelope.

The skill copy has no EnterWorktree-specific workaround, such as a different heredoc wording, a
different way to launch the helper, or putting the env vars inline. I would not improvise one. That
gap should be reported to the user.
