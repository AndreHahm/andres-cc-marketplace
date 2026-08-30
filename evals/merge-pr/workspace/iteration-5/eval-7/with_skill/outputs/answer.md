# Step 2 Readiness Check — Classification and Conclusion

## Inputs

Required-check list (from branch protection, resolved via the REST endpoint per step 2):
1. `Hygiene (PR contract)`
2. `Python quality (ruff, ty, pytest)`
3. `Fork PR (unsupported)`
4. `Publish Codex policy result`

`statusCheckRollup` (from step 1's fetch) contains only 3 entries:
- `Hygiene (PR contract)` — CheckRun, `status: COMPLETED`, `conclusion: SUCCESS`
- `Python quality (ruff, ty, pytest)` — CheckRun, `status: IN_PROGRESS`
- `Publish Codex policy result` — CheckRun, `status: COMPLETED`, `conclusion: SUCCESS`

`Fork PR (unsupported)` has no matching entry anywhere in `statusCheckRollup`.

## Four-state classification

Applying SKILL.md step 2's four-state rule (passing / failing / pending / missing) to each of the 4
required contexts:

| Required context | statusCheckRollup entry | Classification | Reason |
|---|---|---|---|
| `Hygiene (PR contract)` | CheckRun, COMPLETED/SUCCESS | **passing** | `status: COMPLETED` with `conclusion: SUCCESS` |
| `Python quality (ruff, ty, pytest)` | CheckRun, IN_PROGRESS | **pending** | `status: IN_PROGRESS` is one of the pending statuses (QUEUED/IN_PROGRESS/WAITING/REQUESTED/PENDING) |
| `Fork PR (unsupported)` | *no entry at all* | **missing** | No `CheckRun`/`StatusContext` entry with this name/context exists in `statusCheckRollup` for the current head commit — never ran. This is explicitly *not* the same as pending, since nothing has actually started running. |
| `Publish Codex policy result` | CheckRun, COMPLETED/SUCCESS | **passing** | `status: COMPLETED` with `conclusion: SUCCESS` |

None of these states collapse into another: `Fork PR (unsupported)` is reported distinctly as
**missing**, not folded into "still running" (which would misrepresent it as pending) and not treated
as a silent pass just because it never showed up.

## Readiness verdict

**Not ready to merge.** The rule is: *every* required context must classify as **passing**. Here, 2 of
4 do not:
- `Python quality (ruff, ty, pytest)` — pending
- `Fork PR (unsupported)` — missing

The one narrow exception in step 2 (the `--bypass-codex-review` path) only applies when the *sole*
non-passing required context is `Publish Codex policy result`. That doesn't apply here for two
independent reasons: (1) `Publish Codex policy result` is itself already passing — there's nothing to
bypass — and (2) even if it weren't, two *other* required contexts (`Python quality...` and
`Fork PR (unsupported)`) are also non-passing, which on its own rules out the exception regardless of
`Publish Codex policy result`'s state.

Per step 2's instructions, this stops the check here — the skill does not proceed to step 3 (merge-rights
check) on a not-ready PR. The report to the user would be:

> 2 required contexts not passing:
> - `Python quality (ruff, ty, pytest)` — pending (still running for the current head commit)
> - `Fork PR (unsupported)` — missing (never ran for the current head commit)
>
> Not ready to merge.

## Advisory disclosures in this scenario

Step 2's two advisory disclosures (out-of-sync-with-base / commits behind base, and unresolved review
threads) are explicitly scoped in SKILL.md to be **"computed once the three required checks above pass
(or the bypass exception applies)."** In this scenario neither condition holds — the required-check gate
fails outright, and no bypass exception applies (see above) — so step 2 stops at the required-check
report and never reaches the point where those disclosures would be computed or surfaced. They simply
don't run in this pass.

Conceptually, though, to answer the "do they block readiness" question directly: **no, never** — by
design these are advisory-only signals, categorically different from the four-state required-check gate:

- They are computed and surfaced only when the hard required-check gate has already been satisfied (or
  provisionally satisfied via a valid bypass) — they are a downstream, informational layer, not a
  gate of their own.
- A non-zero "commits behind base" count is purely informational: GitHub's own REBASE/SQUASH merge
  handles a stale branch mechanically at step 7, and resyncing (if wanted) is `/sync-branch`'s job, not
  this skill's.
- A non-zero "unresolved review threads" count is a coarse signal ("how many threads remain open"), not
  a triage of severity/content — it never stops the skill, and it's explicitly distinguished from the
  hard "no outstanding CHANGES_REQUESTED" gate, which *is* one of the three required checks.
- Both disclosures are always stated explicitly at step 5's confirmation — even when the value is zero
  — so the user is never misled into thinking "no CHANGES_REQUESTED" or "all required checks passing"
  means "no open concerns at all." But stating them is purely for visibility; neither one can turn a
  ready PR into a not-ready one, or vice versa.

So: only the four-state required-check classification (and the separate no-outstanding-CHANGES_REQUESTED
review check) can block readiness. The two advisory disclosures never do — and in this specific scenario,
since readiness already failed on the required-check gate, they aren't even reached/computed this pass.
