# Triage: PR #142 — Codex finding on `parse_config()` (config.py:47)

**Simulated exercise — no `gh`/API calls made.** This file records the triage decision, the exact
reply text that would be posted to the finding's inline thread, and the resolve/no-resolve decision,
per `handling-review-findings` (`plugins/git-kit/skills/handling-review-findings/SKILL.md`) and
`references/round-and-dedup-rules.md`.

## Finding

> **Major** — `parse_config()` at `config.py:47` doesn't handle a missing `timeout` key and raises
> `KeyError` instead of falling back to the documented default.

Reviewer: Codex. Posted against PR #142's current head SHA.

## Round classification

- Round 1 opens at the PR's first push-for-review, with no prior fix-driven push. This is stated to
  be exactly that review, so this finding belongs to **Round 1**.
- Dedup check (per `references/round-and-dedup-rules.md`): no earlier round exists for this PR, so
  there is nothing to compare against — the finding is trivially **new** by definition, not a repeat.

## Severity and gate interaction

- Stated severity: **Major** (Codex's own label, taken live at classification time, not carried over
  from anywhere).
- Settings: `review_findings_severity_gate` = `false` (default, as stated in the task). Per the
  Settings section, with the gate `false`, **every Round 1-2 finding gets fixed regardless of
  severity** — the gate's Minor/nit-decline branch doesn't even apply here.
- For completeness: even if the gate were `true`, this finding would still route to the Fix path,
  since the gate only auto-declines Minor/nit-level findings, and Major is explicitly excluded from
  that carve-out (and separately protected by the Hard Cap exception, which forbids ever
  silently deferring-and-merging a Critical/Major finding).

## Scope-deferral check

Not scope-deferred. The fix is a small, self-contained, in-session change — add a fallback to the
documented default when the `timeout` key is absent from the parsed config (e.g. `config.get(
"timeout", DEFAULT_TIMEOUT)` or an explicit `try/except KeyError` around the lookup) — not something
requiring real data-flow analysis or cross-cutting investigation. It does not go to the Issue path on
scope grounds.

## New-security-gate check

`parse_config()`'s missing-key handling is a config-parsing defect, not the introduction of a new
authentication/authorization/permission/trust-boundary gate. `.claude/rules/require-security-review-
before-new-gate.md` does not apply — no `security-reviewer` dispatch is triggered by this finding.

## Decision: Fix path (Round 1) — SKILL.md Workflow step 4

1. **Apply the fix**: make `parse_config()` fall back to the documented default timeout value when the
   `timeout` key is missing from the parsed config, instead of letting the `dict` lookup raise
   `KeyError`.
2. **Verify**: this is application code (`config.py`), not a skill/agent/script inside a plugin-devkit
   component, so `require-tests-for-behavior-changes.md`'s plugin-component test mechanisms don't
   apply here. Per Workflow step 4's "otherwise" branch, verification is a re-read of the fix against
   the finding it addresses — confirm the new code path is reached when `timeout` is absent and that
   the value it falls back to matches the documented default (not an arbitrary placeholder). If this
   repo has an existing test suite covering `config.py`, running the relevant tests is good practice,
   but is not itself mandated by this skill for a non-plugin-component change.
3. **Verification is a hard precondition on reply-and-resolve** — nothing is posted to the thread
   until the fix is confirmed correct.
4. **Commit**: via `Skill(git-kit:commit)` — never a raw `git commit` (per
   `.claude/rules/route-through-git-kit-lifecycle-skills.md`).
5. **Push**, then reply to the finding's own inline thread (mechanics: `references/github-api-
   mechanics.md` — `gh api repos/{owner}/{repo}/pulls/{pull_number}/comments/{comment_id}/replies`),
   stating the fixing commit SHA and a one-line verification summary.
6. **Resolve** that thread only after the reply is posted (GraphQL `resolveReviewThread`, since there
   is no REST endpoint for this).

Nothing above was executed — no fix was actually applied, no commit made, no `gh`/API call issued.
This is the decision that would be carried out.

## Exact reply text (to post to the finding's own inline thread)

```
Fixed in <fixing-commit-SHA>: `parse_config()` now falls back to the documented default timeout
value when the `timeout` key is absent from the config, instead of raising `KeyError`. Verified by
re-reading the fix against the reported defect — the missing-key path now returns the documented
default rather than raising.
```

(`<fixing-commit-SHA>` is a placeholder — in a real run this would be the actual short SHA of the
commit created in step 4 above, filled in immediately before the reply call per `references/round-
and-dedup-rules.md`'s "already-fixed threads get resolved with commit-SHA evidence" rule.)

## Thread resolution

**Resolve: yes, but only after the reply above is posted and only once verification (step 2) has
actually passed.** This is a Round 1 Fix-path finding — SKILL.md Workflow step 4 requires reply-then-
resolve once verification confirms the fix, and `references/round-and-dedup-rules.md`'s "Already-
fixed threads get resolved with commit-SHA evidence" section applies directly: since this finding is
being fixed (not filed or declined), the thread should end up **resolved**, not left open. If
verification had failed instead, the thread would stay unresolved and the finding would remain open
in Round 1 rather than being replied-to or resolved.

## Report (Workflow step 7)

One finding this triage pass: **1 fixed** (Round 1, Major, Codex, `config.py:47`). Nothing filed,
nothing declined. No Critical/Major finding is being deferred, so no separate risk-acceptance
`AskUserQuestion` is required before a later `merge-pr` run.
