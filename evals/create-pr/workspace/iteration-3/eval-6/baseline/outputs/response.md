# Priority Label Decisions — Dry Run

## Part A: `acme/widgets`, no priority-label taxonomy, simple bug fix

**Situation:** Branch `feat/example-widget` is fully committed and pushed. No PR is open yet, no issue is
referenced. The repo has no defined priority-label taxonomy at all. The user just says "create a PR for
this."

**How I'd decide whether to apply a priority label:**

1. First I'd check what labels actually exist in the repo (e.g. `gh label list`) rather than assume. If I
   were doing this for real I'd look at `.github/` for any label config, CONTRIBUTING docs, or a label
   sync file — but per the premise here, there is no defined priority-label taxonomy at all (no
   `priority:*`/`P0-P3`-style labels, no documented convention).
2. Given that, I would **not** apply a priority label. Inventing a label that doesn't exist in the repo's
   label set would either fail outright (`gh pr create --label` errors on an unknown label) or, if it
   happened to succeed, would introduce an ad hoc taxonomy that isn't shared, documented, or consistent
   with anything else in the project. Silently deciding "this feels like a P2" and slapping a
   just-invented label on the PR is worse than doing nothing — it fabricates a category nobody agreed to.
3. If I thought priority labeling would genuinely be useful going forward, the right move is to *raise
   it* with the user/maintainers as a separate suggestion ("this repo has no priority taxonomy — want me
   to propose one?"), not to unilaterally decide a scheme and start applying it inside an unrelated bug-fix
   PR.
4. So for this PR: no priority label, no attempt to guess one. I'd just create a normal PR with a clear
   title and description summarizing the bug fix.

**Exact `gh pr create` command I'd run:**

```
gh pr create --title "Fix example widget bug" --body "Fixes a bug in the example widget." --base main --head feat/example-widget
```

(No `--label` flag at all, since no priority taxonomy exists to draw from.)

---

## Part B: repo with a documented critical/high/medium/low taxonomy, small internal refactor

**Situation:** The taxonomy is documented, with "low" explicitly defined as *cosmetic or nice-to-have*.
The change is a small internal refactor of a helper function: no bug, no user-facing behavior change,
nothing blocking other work, and the change description doesn't itself frame the work as cosmetic or
nice-to-have.

**Label I'd apply: `low`**

**Reasoning:**

- Work through the tiers top-down and eliminate:
  - **critical** — reserved for things like outages, data loss, security issues, or work blocking a
    release. Doesn't apply; this is a non-urgent internal refactor.
  - **high** — typically significant bugs, regressions, or work blocking other people/teams. Doesn't
    apply; explicitly stated as "nothing blocking other work."
  - **medium** — usually reserved for real functional changes or fixes that matter but aren't urgent
    (e.g., a real bug with a workaround, a meaningful feature). This refactor changes no behavior and
    fixes no bug, so it doesn't carry the substantive impact "medium" usually implies.
  - **low** — cosmetic or nice-to-have. A pure internal refactor with zero external effect (no bug fixed,
    no behavior changed, nothing unblocked) is, in practical terms, exactly the kind of work that's "nice
    to have" for code health but not necessary right now. Even though the PR description doesn't use the
    words "cosmetic" or "nice-to-have" itself, the *substance* of the change (internal-only, no
    functional impact, non-blocking) matches that tier's definition more closely than any other.
- I would **not** default to "medium" just because the description doesn't explicitly self-label as
  low/cosmetic. Priority should be assessed from the actual impact of the change, not from whether the
  author happened to use the taxonomy's own vocabulary in the description. A refactor with no bug, no
  user-facing effect, and nothing depending on it has low urgency and low impact by definition — that's
  what "low" is for, regardless of the exact wording used to describe it.
- If I were uncertain whether the maintainers intended "low" to require literal cosmetic framing versus
  covering any zero-impact internal change, I'd flag that ambiguity rather than silently guess — but
  absent any such signal, "low" is the best-fit, defensible choice here.
