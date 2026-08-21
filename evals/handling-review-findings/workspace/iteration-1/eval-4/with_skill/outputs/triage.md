# Triage: PR #142, round-2 finding on `handler.py:120`

## Finding under triage

> **Minor** (round 2, just posted) — no test coverage for the error path in `handler.py:120` when the
> resource doesn't exist.

## Step 1 — Dedup against round 1

Round 1 already raised a finding on the exact same file and line:

> **Major** (round 1, already resolved) — authorization check missing in `handler.py:120` — the
> endpoint doesn't verify the caller owns the resource before deleting it. Resolved citing commit
> `abc123f`.

Per `references/round-and-dedup-rules.md`'s dedup mechanism: **file+line match is only a candidate
signal, never sufficient by itself** to call a finding a repeat. The actual defect content must be
compared:

- Round 1's defect: a missing **authorization check** — the endpoint doesn't verify the caller owns
  the resource before a delete proceeds. This is a logic/security defect in the *happy-path* delete
  flow (an unauthorized caller can successfully delete someone else's resource).
- Round 2's defect: missing **test coverage** for a *different* code path — what happens when the
  resource being deleted doesn't exist at all (the not-found / error path). This says nothing about
  authorization; it's a coverage gap for a distinct branch of the same handler.

These are two legitimately different concerns that happen to cite the same line number, almost
certainly because `handler.py:120` is the single line marking the top of the delete-endpoint function
that both reviewers pointed at — one flagging what the function *does* (skips an owner check), the
other flagging what the function's *tests* don't exercise (the not-found branch). The
round-and-dedup-rules reference explicitly calls out this exact shape: "an authorization defect and a
missing error-path test on that same line" as its own worked example of findings that must not be
collapsed together.

There is no meaningful ambiguity here to fall back on the "when uncertain, classify as new" default —
the two findings describe clearly different defects. But even if this were borderline, the rule's
tie-break also lands on "new": a false "new" costs an extra look, a false "repeat" silently drops a
real finding.

**Conclusion: this is a genuinely new finding, not a repeat of the round-1 authorization finding.**
The round-1 thread (already resolved, `abc123f`) is not reopened or touched by this triage — it stays
exactly as-is.

## Step 2 — Round and severity classification

- **Round**: explicitly stated as round 2, and nothing suggests otherwise (it's newly posted against
  the PR's current head, after round 1's fix was pushed and resolved). Round 2 is within the
  fix-eligible window (rounds 1-2 → Fix path).
- **Severity**: Minor, as stated by the reviewer.
- **Scope**: not scope-deferred — adding a unit/integration test for one already-identified error path
  is a small, in-session-sized change, not something requiring further analysis.
- **New security-relevant gate?** No — this is a test-coverage gap, not the introduction or structural
  change of a permission/auth/trust-boundary gate, so
  `.claude/rules/require-security-review-before-new-gate.md` does not apply here (that rule was
  already relevant to the *round-1* authorization finding, not this one).

## Step 3 — Apply round-cap / severity-gate decision

Checked `review_findings_severity_gate` per SKILL.md's Settings section: no
`.claude/git-kit.local.json` override exists in this checkout, so the git-tracked default in
`plugins/git-kit/git-kit.settings.json` applies: `"review_findings_severity_gate": false`.

With the gate `false`, **every round 1-2 finding gets fixed regardless of severity** — the Minor
severity does not route this to Decline. (Had the gate been `true`, this Minor finding with nobody
explicitly requesting the fix would route to the Decline path instead — noted here for completeness,
but it does not apply under the actual configured default.)

Round 2 + gate `false` → **Fix path** (Workflow step 4).

## Decision: Fix

1. **Fix**: add test coverage for the delete-endpoint's not-found path — a test asserting the expected
   behavior (e.g. a 404/appropriate error response, no exception, no partial side effects) when
   `handler.py`'s delete handler is invoked for a resource that doesn't exist.
2. **Verify**: this is a test-only addition with no production-logic change, so per
   `.claude/rules/require-tests-for-behavior-changes.md` the test itself *is* the verification
   mechanism — run the new test (and the surrounding suite) and confirm it passes against current
   behavior, i.e. confirm the error path already behaves correctly and is now actually covered rather
   than just asserted.
3. **Only after verification passes**: commit via `Skill(git-kit:commit)` (never a raw `git commit`),
   push, then reply to *this* finding's own review thread (not the round-1 thread) with the fixing
   commit's SHA and a one-line summary of what the new test confirms, and only then resolve that
   thread via the `resolveReviewThread` GraphQL mutation (`references/github-api-mechanics.md`).
4. If verification had failed, the thread would stay open in round 2, unreplied-to-as-resolved — not
   applicable here since this triage assumes the fix will be written and verified as described above,
   but noted as the fallback per Workflow step 4.

**Note**: This is a simulated exercise — no real PR, no `gh`/API calls were made or attempted. The
above is the triage decision and the fix/reply/resolve plan only; no commit, push, reply, or thread
resolution was actually executed.
