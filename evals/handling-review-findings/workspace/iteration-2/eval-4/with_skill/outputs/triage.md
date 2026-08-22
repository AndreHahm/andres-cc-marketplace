# Triage: Round-2 finding on `handler.py:120`

**PR #142** — this is a simulated exercise; no `gh`/API calls were made. Reasoning only, per the
`handling-review-findings` skill's Workflow step 2 (classification) and step 3 (routing).

## The two findings being compared

| | Round 1 (already resolved) | Round 2 (just posted) |
|---|---|---|
| Severity | Major | Minor |
| Location | `handler.py:120` | `handler.py:120` (same file+line) |
| Defect described | Authorization check missing — the endpoint doesn't verify the caller owns the resource before deleting it | No test coverage for the error path when the resource doesn't exist |
| Status | Fixed, thread resolved citing commit `abc123f` | Unclassified — this triage |

## Is the round-2 finding new, or a repeat of round 1?

**New.** Per `references/round-and-dedup-rules.md` ("Dedup mechanism: file+line match is a candidate
signal, never sufficient by itself"), a same-file/same-line match only narrows which earlier findings
to compare against — it never by itself declares a repeat. The rule is explicit that dedup requires
comparing the actual defect described, not just where it sits, and gives as its own worked example
exactly this shape: *"an authorization defect and a missing error-path test on that same line"* — two
distinct findings that can legitimately coexist at one location.

That is precisely what these two findings are:

- Round 1's defect is a **missing authorization check** — a security/access-control gap in the
  endpoint's own logic (caller identity vs. resource ownership is never verified).
- Round 2's defect is a **missing test** for a *different* code path — what happens when the target
  resource doesn't exist at all (a not-found/error-handling path, unrelated to who is allowed to
  delete it).

These describe different failure modes with different fixes (a logic change adding an ownership check,
vs. a test-suite addition exercising a not-found branch). Fixing round 1's authorization gap does not
address round 2's test-coverage gap, and vice versa — they are independent. There is no ambiguity here
(the two defects are clearly distinct, not a borderline case), but even if there were, the rule's own
guidance is to default to "new" whenever the comparison is uncertain, since a false "new" only costs an
extra look while a false "repeat" silently drops a real finding.

**Conclusion: round-2 finding is classified as NEW, not a repeat of the resolved round-1 finding.**

## Fix / File / Decline decision

Classification inputs (Workflow step 2/3, `references/settings-and-round-budget.md`):

- **Round budget**: this is round 2, within `review_findings_max_rounds` (default `3`, no local
  override indicated) and past `review_findings_min_rounds` (default `1`) — an in-budget round either
  way, so the round budget itself does not route this to Issue.
- **Three named exceptions** (none apply):
  1. *Direct instruction* — no one has asked for this specific finding to be filed instead of fixed.
  2. *Out-of-scope component* — `handler.py` is the same file already touched by this PR's round-1 fix;
     this is squarely in-scope, not an unrelated component.
  3. *Too large for this session* — adding a unit/integration test for one error path (resource not
     found) is a small, well-scoped task, not a multi-file architectural change or a task needing
     capabilities this session lacks. Per the skill's own guidance, "merely inconvenient" is not
     sufficient to invoke this exception — default to attempting the fix.
- **Severity gate**: `review_findings_severity_gate` defaults to `false` (confirmed against this repo's
  `plugins/git-kit/git-kit.settings.json`, no local override given in this scenario). At `false`, every
  finding gets fixed regardless of severity — the Minor severity here does **not** route this to
  Decline. (Had the gate been `true`, this Minor/nit finding would decline by default unless someone
  explicitly asked for it — but that is not this scenario's setting.)

**Decision: Fix path.** The round-2 finding is real, new, and in-scope. It is a Minor severity finding
but the severity gate is off, so it is fixed like any other finding rather than declined. It does not
match any of the three exceptions, so it is not filed as an issue.

Per Workflow step 4, once implemented, the fix (adding test coverage for the not-found error path at
`handler.py:120`) would need verification — here, that means the new test itself passing and actually
exercising the not-found branch — before the thread is replied-to (citing the fixing commit's SHA and
what verification confirmed) and resolved. **No such fix, commit, reply, or resolve action was taken as
part of this exercise** — the prompt is a simulated triage decision only, with no real PR, no real
`handler.py` to edit, and an explicit instruction not to run any `gh`/API calls. This document records
the classification and routing decision that `handling-review-findings` would apply next, not the
downstream fix/verify/reply/resolve execution itself.

## Round-1 status (unaffected)

The already-resolved round-1 finding is untouched by this triage — it stays fixed and resolved, citing
its own commit `abc123f`. Nothing about the round-2 finding reopens or revisits it.
