# What happens when `git show` fails at Preflight step 5, on the skill's own first (unmerged) run

## Short answer

The chain does **not** abort. Step 5's two `git show` commands are each suffixed with `|| true`,
which is called out as *deliberate* precisely so that an expected, non-fatal failure (the prompt
files not existing yet on `$BASE`) cannot break the `&&` chain the whole Preflight sequence runs
as. Step 6 and the closing `echo` still execute inside that same chained Bash call. Only *after*
that single Bash tool call returns — with the echoed state captured — does the skill run a
**separate** `Read`/`Write` pair (two more tool calls) to populate `$RUN/review.md` and
`$RUN/refute.md` from the working-tree copy instead.

## Step-by-step, with citations

### 1. The chain is one Bash tool call, `&&`-joined

The Preflight preamble is explicit about this:

> "Run steps 1-6 below as a single chained Bash invocation (`&&` between them, one tool call),
> ending with an `echo` of the resolved `BASE`, `REPO_ROOT`, `RUN`, `DIFF_STR`, `CODEX_DIFF_STR`,
> and whether `$RUN/review.md`/`$RUN/refute.md` came out non-empty (step 5 below needs this signal
> available *after* the chain, since its own fallback runs as separate `Read`/`Write` tool calls
> that can't be part of this same Bash invocation)." (SKILL.md, Preflight intro, lines 82-90)

This one sentence already answers most of the question: the chain's own closing `echo` is
designed around the assumption that step 5 might fail, and the fallback is pre-declared to be
*outside* the chain, as separate tool calls.

### 2. Step 5's `git show` calls are written to survive failure

```bash
git show "$BASE:plugins/git-kit/skills/cross-model-review/prompts/review.md" > "$RUN/review.md" 2>/dev/null || true
git show "$BASE:plugins/git-kit/skills/cross-model-review/prompts/refute.md" > "$RUN/refute.md" 2>/dev/null || true
```

Immediately under this block, the skill states the reasoning directly:

> "**The `|| true` on each line is deliberate — a `git show` failure here is expected, not fatal,
> and must not break the `&&` chain the whole Preflight sequence runs as.** Without it, this
> expected failure would abort the chained invocation before step 6 or the closing `echo` ever
> runs, losing every resolved value (`$RUN`, `$REPO_ROOT`, `$BASE`, `$DIFF_STR`, `$CODEX_DIFF_STR`)
> this whole skill depends on for the rest of the run." (SKILL.md, step 5, lines 139-143)

Mechanically: `cmd || true` always has exit status 0, regardless of whether `cmd` itself succeeded.
So even though `git show` returns non-zero on this first run (the file doesn't exist on `$BASE`
yet — nothing has merged), the `|| true` swallows that failure and the statement as a whole
reports success. Since the six Preflight steps are chained with `&&`, and each of these two lines
evaluates to exit 0, the chain proceeds to step 6 exactly as if step 5 had "succeeded" — it's just
that the two target files end up empty rather than containing trusted content. (The `>` redirect
creates/truncates `$RUN/review.md`/`refute.md` before `git show` even runs, so both files exist as
empty files on disk the moment this line finishes, whether or not `git show` found anything — this
is why the closing `echo`'s check is framed as "came out non-empty," not "the command exited 0.")

### 3. Step 6 and the closing `echo` still run in the same Bash call

Because the chain isn't broken, Preflight step 6 (the `grep -E` check for whether the diff touches
the Codex dispatcher scripts) executes normally, and the chain's final `echo` — which reports
`BASE`, `REPO_ROOT`, `RUN`, `DIFF_STR`, `CODEX_DIFF_STR`, and the non-empty/empty status of
`$RUN/review.md`/`refute.md` — also executes and returns to the caller as part of the same Bash
tool result.

Testing & Validation scenario 8 confirms this is the intended, checked behavior of the skill:

> "`prompts/review.md`/`refute.md` don't exist on `$BASE` yet (scenario 5) → the chained Bash
> invocation's `git show || true` doesn't abort; step 6 and the closing `echo` still run, and the
> `Read`/`Write` fallback runs afterward using the echoed `$RUN` value." (SKILL.md, Testing &
> Validation, scenario 8, lines 438-440)

And the corresponding quality gate states the same invariant as a checkable assertion:

> "Preflight step 5's `git show` calls always carry `|| true` — an expected first-run failure
> never aborts the chained invocation before step 6 or the closing `echo`." (SKILL.md, Quality
> gates, lines 475-476)

### 4. How the Read/Write fallback actually gets to run

Once the single chained Bash tool call has returned and its echoed output has been captured (in
particular, the empty-file signal for `review.md`/`refute.md`), the skill instructs the agent to
run the fallback as separate tool calls, no longer inside a Bash chain:

> "A `git show` failure (non-zero exit, or an empty `$RUN/review.md`/`$RUN/refute.md` — reflected
> in the closing `echo`'s non-empty/empty signal for each file) means the file doesn't exist on
> `$BASE` yet (e.g. this skill's own not-yet-merged first run). Once the chained invocation has
> returned and its echoed state captured, fall back — as separate tool calls, after the Bash chain,
> using the just-resolved `$RUN` value — by `Read`-ing the working-tree copy at
> `${CLAUDE_PLUGIN_ROOT}/skills/cross-model-review/prompts/review.md` (respectively `refute.md` —
> note the `skills/cross-model-review/` segment: `${CLAUDE_PLUGIN_ROOT}` is the *plugin* root,
> `plugins/git-kit/`, not this skill's own directory) and `Write`-ing that content to
> `$RUN/review.md`/`$RUN/refute.md`, but never silently: set `REVIEW_UNVERIFIED=1` /
> `REFUTE_UNVERIFIED=1` and record it in Phase 3's `inspection_limits` ("reviewer instructions were
> not trust-boundary-verified against $BASE this run")." (SKILL.md, step 5, lines 145-157)

Concretely, this means:

1. Read `${CLAUDE_PLUGIN_ROOT}/skills/cross-model-review/prompts/review.md` (and `refute.md`) from
   the working tree — one `Read` tool call per file.
2. Write that content to `$RUN/review.md` (and `$RUN/refute.md`) — one `Write` tool call per file
   — using the *literal* `$RUN` path string echoed by the Bash chain, not a shell-variable
   reference, since (per the Preflight intro) "a separate tool call re-expanding `$RUN`/`$BASE`/
   etc. as if they were still live shell variables will not see them" (lines 87-90).
3. Set `REVIEW_UNVERIFIED=1` / `REFUTE_UNVERIFIED=1` in the agent's own tracked state (there's no
   shell to hold these anymore — they're bookkeeping for what gets written into Phase 3's report).
4. Carry that flag into Phase 3's `inspection_limits` line: "Preflight step 5's unverified-
   instructions fallback if either `REVIEW_UNVERIFIED` or `REFUTE_UNVERIFIED` was set" (Phase 3,
   lines 370-372).

This is why the fallback *can't* live inside the same Bash invocation: `Read`/`Write` are distinct
tool types from `Bash`, and the whole point of Preflight step 5's design is that the file's
"doesn't exist on `$BASE` yet" case has to be discovered from *within* Bash (via the empty-file
check reflected in the closing echo) but *resolved* using tools (`Read`/`Write`) that Bash itself
cannot invoke. The `|| true` guard is what keeps the Bash chain alive long enough to reach and
emit that echo in the first place — without it, the whole diagnostic signal the fallback depends on
would never be produced, because the chain would die on step 5 before reaching step 6 or the
`echo`, and every other resolved value (`$RUN`, `$REPO_ROOT`, `$BASE`, `$DIFF_STR`,
`$CODEX_DIFF_STR`) would be lost along with it (explicitly stated at lines 141-143).

## Summary

- **Does the whole chain abort?** No — `|| true` forces each `git show` line's exit status to 0,
  so the `&&`-chained Preflight sequence continues through step 6 and the closing `echo`
  regardless of whether the prompt files exist on `$BASE`.
- **How does the Read/Write fallback get to run?** It runs *after* the chained Bash call has fully
  returned, as two separate `Read` + two separate `Write` tool calls, triggered by the
  non-empty/empty signal the closing `echo` reported for `$RUN/review.md`/`refute.md`, using the
  literal (not shell-variable) `$RUN` path value captured from that echo — and it must also set
  `REVIEW_UNVERIFIED`/`REFUTE_UNVERIFIED` and surface that in Phase 3's `inspection_limits` rather
  than silently substituting the working-tree copy.
