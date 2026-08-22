# Triage Decision — PR #142, Codex finding on `config.py:47`

## Finding under triage

> **Major** — `parse_config()` at `config.py:47` doesn't handle a missing `timeout` key and raises
> `KeyError` instead of falling back to the documented default.

Source: Codex, first review round after this PR's first push-for-review.

## Step 1 — Round classification

This is **round 1**. Per `references/round-and-dedup-rules.md`, round 1 opens at the PR's first
push-for-review with no prior fix, and this is explicitly stated to be "the first review after the
PR's first push-for-review." There is exactly one finding in this round so far (Codex's). No
fix-driven push has happened yet, so there is no earlier round to dedup against — this finding is
trivially new (nothing to compare it to).

## Step 2 — Exception check (Settings and Round Budget, "three named exceptions")

Checking all three named exceptions before anything else, since any match routes this to the Issue
path regardless of round:

1. **Direct instruction** — nobody (user or human reviewer) has said to file this instead of fixing
   it. Does not apply.
2. **Out-of-scope component** — `config.py` is presumably within this PR's own changed scope (the
   finding is against a file the PR is actively being reviewed on, with no indication it's untouched
   by this PR). Does not apply.
3. **Too large for this session** — this is a small, local, mechanical fix: add a fallback for a
   missing dict key before raising. It is not an architectural change, not a multi-file trace, not
   something requiring capabilities this session lacks. Does not apply — and per the settings
   reference, "when uncertain whether something is genuinely too large versus just tedious, default
   to attempting the fix rather than reaching for this exception." This isn't even a borderline case.

None of the three named exceptions apply.

## Step 3 — Severity gate check

`review_findings_severity_gate` is `false` (the default, as stated in the prompt). The severity gate
is only relevant to Minor/nit findings in any case — this finding is **Major**, so the gate would
never apply to it even if it were `true` (per `references/round-and-dedup-rules.md`'s "Severity-gate
interaction" section, the Hard Cap protection for Critical/Major is orthogonal to this setting, and
the gate itself only auto-declines Minor/nit findings). Decline path does not apply.

## Step 4 — Routing decision

**Fix path.** This is a real, in-scope, round-1 finding, none of the three named exceptions apply,
and it isn't a Minor/nit finding subject to the severity gate. Per Workflow step 3: "Otherwise → Fix
path (step 4), for every round through `review_findings_max_rounds`." Round 1 is trivially within any
configured budget (default 1–3).

## Step 5 — What the Fix path actually requires (Workflow step 4)

1. **Apply the fix** — add a fallback to the documented default when `timeout` is absent from the
   parsed config, e.g. `config.get("timeout", DEFAULT_TIMEOUT)` (or the equivalent for however
   `parse_config()` currently accesses the dict), instead of a bare `config["timeout"]` lookup that
   raises `KeyError`.
2. **Verify** — this is not a skill/agent/script *behavior* change under
   `.claude/rules/require-tests-for-behavior-changes.md` in the plugin-devkit sense (it's an
   application bug fix in the hypothetical PR's own codebase, not a plugin component), so verification
   here means a re-read of the fix against the finding it addresses: confirm `parse_config()` no
   longer raises `KeyError` on a missing `timeout` key, and confirm it falls back to the *documented*
   default specifically (not just any default value) — matching exactly what Codex's finding called
   out as missing.
3. **Verification is a hard precondition on replying and resolving.** Per Workflow step 4: "Verification
   is a hard precondition on replying and resolving — a reply-and-resolve never happens on the strength
   of a pushed commit alone." In this simulated exercise, that means: I do not draft this as an
   already-sent reply or an already-resolved thread. The reply text below is what I *would* post, and
   only *after* the fix is committed, pushed, and confirmed to actually resolve the `KeyError`/missing-
   default behavior described in the finding.
4. **Commit** via `Skill(git-kit:commit)` — never a raw `git commit` per
   `.claude/rules/route-through-git-kit-lifecycle-skills.md` — with `--push` explicitly requested (since
   `commit`'s own `commit_auto_push` defaults to `false` and isn't left to that default here).
5. **Reply-with-SHA is conditional on the push having actually landed.** If the push is declined or
   fails, the commit SHA doesn't yet exist on the remote — the finding stays open in the same round
   (round 1) until the fix is actually pushed, exactly as if verification itself had failed. (This
   exercise assumes the push lands cleanly, since no such failure is described in the prompt.)
6. **Reply, then resolve** — only once the push is confirmed landed and verification passed.

## Drafted reply text (to post to Codex's inline thread, only after verification passes and the fix is pushed)

> Fixed in `a1b2c3d` (placeholder SHA — replace with the actual fixing commit's SHA once pushed).
> `parse_config()` now falls back to the documented default timeout when the `timeout` key is absent
> from the config dict, instead of raising `KeyError`. Verified by re-reading the fix against this
> finding: a missing `timeout` key no longer raises, and the value used matches the documented default.

## Resolution statement

The thread is **resolved only after** this reply is posted, and **only because verification actually
passed** — confirming the fix genuinely eliminates the `KeyError` and correctly applies the documented
default, not merely that a commit was pushed. Per `references/github-api-mechanics.md`'s "Already-fixed
threads get resolved with commit-SHA evidence" principle: reply first (citing the fixing SHA and what
verification confirmed), and only then call `resolveReviewThread` on that thread's node ID. If
verification had instead failed (e.g. the fix applied a default but not the *documented* one, or missed
another dict-access path that could still raise), the thread would stay open in round 1, unreplied and
unresolved, until a corrected fix passes verification — per Workflow step 4's explicit "If verification
fails, don't reply or resolve — the finding stays open in the same round."

## Summary

| Question | Answer |
|---|---|
| Round | 1 |
| Exception applied | None |
| Severity gate applicable | No (Major, and gate is `false` regardless) |
| Routing | Fix path |
| Reply posted? | Only after fix is committed via `Skill(git-kit:commit) --push`, pushed, and verified |
| Thread resolved? | Only after the reply, and only because verification passed — never on a pushed commit alone |
