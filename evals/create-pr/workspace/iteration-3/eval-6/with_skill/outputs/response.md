# Dry Run: create-pr Step 3.85 (Priority Label Resolution)

No Bash/git/gh/Skill/Agent tool calls were actually invoked — this is a narrated walkthrough of what
`create-pr`'s SKILL.md would do, based on reading it directly.

## Part A — `acme/widgets`, no taxonomy file

**Scenario:** branch `feat/example-widget`, everything committed and pushed, no PR open, no issue
mentioned, user says "create a PR for this" for a simple bug fix. `acme/widgets` has never adopted
`docs/github-label-taxonomy.md` — the file doesn't exist in that repo at all.

Walking the skill in order:

1. **Pre-flight Checks** — `git status` clean (everything already committed/pushed), so step 2 (nested
   `commit`) is skipped. Step 3.5 (session open-issues check) finds nothing to report. Step 4
   (cross-model-review gate) would run/ask normally — not relevant to priority labels, skipped over here.
2. **Step 1** — branch already pushed, so the push is a no-op / already satisfied.
3. **Step 2** — draft the PR description from the resolved template.
4. **Step 3** — `AskUserQuestion`: "Create this PR as a draft, or ready-to-merge?" (must always be asked,
   never assumed). For this walkthrough I'll assume the answer is **Ready-to-merge**, since the work is
   described as already-fixed and nothing suggests it's in-progress — flagging this as my own filled-in
   assumption, not something the skill lets you skip asking.
5. **Step 3.5** — validates the title against `scripts/marketplace_ci/pr_policy.py`. That script doesn't
   exist in `acme/widgets` (it's this marketplace's own CI tooling), so per the skill's own text this
   step "is a no-op in a repository without `scripts/marketplace_ci/pr_policy.py`." Skipped.
6. **Step 3.75** — resolve an assignee: `gh api user --jq '.login'` (falls back to repo owner if that
   fails/empty). Since this is a dry run, I'll use the placeholder `<login>` for the resolved account.
7. **Step 3.85 — the step in question.** The rule is:

   > if `docs/github-label-taxonomy.md` has no `p:` Priority section, skip this step... don't pass
   > `--label` below, and never block PR creation on it.

   In `acme/widgets`, `docs/github-label-taxonomy.md` doesn't exist at all — so trivially, it has no `p:`
   Priority section. This is exactly the no-op condition the step names. **Step 3.85 is skipped
   entirely.** No priority is resolved, no `p:` label is chosen (not even a default), and PR creation is
   never blocked by this. The step is explicit that this is expected and fine: "`git-kit` is a
   general-purpose plugin, so no installing repository is required to have adopted this taxonomy."

8. **Step 4 (gh pr create)** — per the skill's own instruction: "including `--label \"p: <tier>\"` from
   step 3.85 only when that step actually resolved a tier (omit the flag entirely in a repository with no
   `p:` taxonomy)." Since step 3.85 resolved nothing, `--label` is omitted entirely — not passed as an
   empty string, not defaulted to any tier, simply absent from the command.

### The exact literal `gh pr create` command (Part A)

Using the ready-to-merge template (step 3's assumed answer above), with `--assignee` from step 3.75 and
**no `--label` flag** (step 3.85 was a no-op):

```bash
gh pr create --title "fix(widgets): resolve example widget bug" --body "Your PR description" --base main --assignee <login>
```

(If step 3's answer had instead been "Draft," the only difference is a `--draft` flag added — the
`--label` omission is unaffected either way:)

```bash
gh pr create --draft --title "fix(widgets): resolve example widget bug" --body "Your PR description" --base main --assignee <login>
```

Note there is no `--label "p: ..."` anywhere in either form — that's the entire point step 3.85 makes for
a repository that never adopted the taxonomy.

---

## Part B — `andres-cc-marketplace`, internal refactor of a helper function

**Scenario:** small internal refactor of a helper function. No bug, no user-facing behavior change,
nothing blocking other work, and nothing in the change description explicitly frames it as
cosmetic/nice-to-have.

This repository's `docs/github-label-taxonomy.md` *does* define a `p:` Priority section, so step 3.85
is not a no-op here — it runs and resolves exactly one tier.

Walking the resolution logic from step 3.85 (and the identical wording in `docs/github-label-taxonomy.md`
§6):

- `p: critical` — requires a security/data-loss risk, a broken build/CI, or blocking an active release.
  None apply here.
- `p: high` — requires a user-facing bug fix, or blocking other in-progress work. Explicitly ruled out:
  "no bug... nothing blocking other work."
- `p: low` — requires **an explicit cosmetic/nice-to-have signal** (e.g. framed as optional polish). The
  scenario explicitly states nothing frames this as cosmetic/nice-to-have — so this tier is also ruled
  out.
- `p: medium` — the default "unless the change signals otherwise."

The skill's own text calls out this *exact* scenario by name as the worked example of what stays at the
default:

> an ambiguous case (e.g. an unframed internal refactor) stays at `p: medium`, never inferred down to
> `p: low` by elimination.

**Resolved label: `p: medium`.**

**Why:** an internal refactor with no stated bug, no user-facing impact, and no blocking relationship
doesn't trip the `critical` or `high` criteria — but critically, it also *isn't* an explicit
cosmetic/nice-to-have signal, so it's not eligible for `p: low` either. The skill is deliberately
prescriptive here: ambiguity (a plausible-but-unstated case) must never be resolved "downward" to `p: low`
just because nothing else obviously fits — `p: low` requires a positive, explicit signal, not just the
absence of a reason to pick something higher. With `critical`, `high`, and `low` all ruled out (the first
two affirmatively, the last for lack of the required explicit signal), the change falls through to the
stated default, `p: medium`, and `--label "p: medium"` is included in the `gh pr create` call.
