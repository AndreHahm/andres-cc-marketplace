# Dry Run: Filing a Bug in `acme/widgets` (No `p:` Taxonomy)

## Setup

`acme/widgets` is a fresh repository that has never adopted this marketplace's
`docs/github-label-taxonomy.md` — there is no such file in that repo, and therefore no `p:` Priority
section anywhere in it. A user reports a straightforward bug and asks to file it as a new GitHub issue.
This triggers `github-issue-lifecycle`'s Workflow 1 (`workflows/create-an-issue.md`).

## Walking through Workflow 1

1. **Step 1 — Check for Existing Issues.** The skill searches (`gh issue list --search "<keywords>"` and
   `gh api search/issues ...`) for a duplicate. Nothing about this step depends on the label taxonomy;
   it proceeds normally.
2. **Step 2 — Delegate Drafting.** Once no duplicate is found, the skill invokes
   `Skill(git-kit:github-issue-creator)` with the bug report, explicitly instructing it to avoid literal
   bot-trigger mentions. That skill drafts a local markdown issue file under `issues/`. Nothing here
   touches labels either.
3. **Step 3 — File It Live.** The skill runs `gh issue create --title "<title>" --body-file <draft-path>`
   against `acme/widgets`, after a redaction/bot-trigger re-check. The issue is filed with no `--label`
   flag at all — label assignment isn't part of this step.
4. **Step 4 — Verify.** The skill attempts to reproduce/re-confirm the bug. Not label-related.
5. **Step 5 — Initial Impact Analysis.** A first-pass severity/impact read based on the issue's own
   template fields (e.g. the same Critical/High/Medium/Low framing `github-issue-creator`'s template
   already uses for its "Impact" section). This produces a severity judgment in prose/analysis, but does
   not itself write anything to GitHub.
6. **Step 5.5 — Assign Priority Label.** This is the step that matters for the question asked. Its very
   first line is: **"This repository only — a no-op elsewhere."** The instruction is explicit:

   > Check whether `docs/github-label-taxonomy.md` exists and defines a `p:` Priority section. If it
   > doesn't, skip this entire step — `github-issue-lifecycle` is a `git-kit` component, and `git-kit` is
   > a general-purpose plugin installable in any repository; no repository installing it is required to
   > have adopted this specific `p:` taxonomy, and issue filing must never block on a label scheme the
   > target repository never opted into.

   Since `acme/widgets` has no `docs/github-label-taxonomy.md` at all, this check fails immediately, and
   the entire rest of Step 5.5 (reading current labels, computing the resolved tier, the
   `gh issue edit --add-label`/`--remove-label` reconciliation logic, the "report if the label doesn't
   exist" fallback) is skipped outright. No `gh issue edit` call is made. No error, warning, or blocking
   behavior results — the step is a pure no-op and the workflow moves on.
7. **Step 6 — Link to Originating PR (If Applicable).** Independent of labeling; proceeds/asks as normal
   depending on PR state.

## Direct answer

**No, the issue does not end up with a `p:` label.** Step 5.5 never applies (or even attempts to apply)
any `p: critical`/`p: high`/`p: medium`/`p: low` label, because its own gating condition —
`docs/github-label-taxonomy.md` existing and defining a `p:` Priority section — is false for
`acme/widgets`. The issue is filed via `gh issue create` with no `--label` argument, and Step 5.5 exits
without making any `gh issue edit` call.

**Nothing about the missing taxonomy blocks or otherwise affects filing the issue.** The design is
explicitly defensive against exactly this scenario: the SKILL.md's own quality-gates checklist states
"Workflow 1's Step 5.5 and Workflow 2's Step 7 label-update are always a no-op in a repository without
`docs/github-label-taxonomy.md`'s `p:` Priority section — issue filing/triage never blocks on a label
scheme the installing repository never opted into." Steps 1-4 and 6 all proceed exactly as they would in
this marketplace's own repo; only Step 5.5's labeling logic is skipped. The issue is filed successfully,
verified, and impact-analyzed in prose — it just never receives a `p:` label, since there is no taxonomy
in `acme/widgets` to apply one from.

## Why this is the current, intentional behavior (not an oversight)

The SKILL.md's own "Testing & Validation" section documents that this scoping was *not* the original
design — it was added specifically in response to a round-1 automated PR review finding (PR #326, Codex,
P2): "unconditionally requiring this repo's own `p:` taxonomy would have blocked issue filing/triage in
any other repository installing `git-kit`... without that taxonomy adopted." The fix scoped Step 5.5 (and
the symmetric Workflow 2 Step 7 re-triage logic) to "this repository only — a no-op elsewhere," matching
an equivalent pattern already used by `create-pr`'s own step 3.5. So the behavior in `acme/widgets` isn't
an edge case the skill happens to handle gracefully — it's the exact scenario the most recent fix to this
capability was written to guarantee stays a no-op rather than a blocker.

One nuance worth flagging: if `acme/widgets` happened to have its own repo-local automation resembling
`issue-opened-labeler.yml` that auto-applies labels on issue open, that would be entirely independent of
this skill and outside its awareness — but nothing in the scenario as given suggests `acme/widgets` has
any such automation, and the skill's own reconciliation logic for that automation (the "residual timing
risk" paragraph) is itself gated behind the same taxonomy check, so it likewise never engages here.
