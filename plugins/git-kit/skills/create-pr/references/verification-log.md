# Verification Log

Dated "verified live" notes for specific steps in `SKILL.md`, extracted to keep that file under R13's
line budget (same reason `references/test-scenarios.md` and `references/bot-trigger-mention-incident.md`
were already extracted — see `SKILL.md`'s Testing & Validation section for the pointer back here).

**Step 3.5 (`check-pr-title.py`) — verified live, 2026-08-16:** confirmed `PASS` on a real compliant title
(`docs(plugin-devkit): ...`, used for PR #42) and `FAIL` with the correct reason on three synthetic bad
titles — a `style:`-typed title (rejected: not in this repo's allowed-type list, even though `style` is a
valid `commit` type), a `ci:`-typed title (same reason), and an uppercase-scope title (rejected: fails the
title regex). All four results matched `pr_policy.py`'s actual behavior, called directly rather than
reimplemented.

**Step 3.75 (assignee resolution) — verified live end-to-end, 2026-08-16:** `gh api user --jq '.login'`
resolved correctly, and this exact `create-pr` run used it to create a real PR (#43) with
`--assignee AndreHahm` — `gh pr view 43 --json assignees` confirmed the assignee actually landed. The
`gh repo view --json owner --jq '.owner.login'` fallback path resolved correctly too, though wasn't
exercised as the active path (the primary `gh api user` lookup succeeded) — and since this repo's
authenticated user and owner are the same account, a real divergence between primary and fallback still
isn't covered; a multi-maintainer repo would be needed to observe that.

**Best Practice 6 and step 5's reason check (no literal bot-trigger mentions) — 3 rounds, PR #257/#258,
2026-08-31:** see `references/bot-trigger-mention-incident.md` for the full narrative (rounds 1-2 from
PR #257, round 3's two findings — the bypass-reason gap and this file's own R13 line-count fix — from
Codex and Devin's automated review of PR #258 itself). No fresh `skill-tester` eval re-run for any
round; each was verified by re-observing the real PR/GitHub Actions state after applying it.

**Pre-flight Checks step 3.5 (session open-issues check) — added 2026-09-08:** documentation-only
Testing & Validation coverage (concrete scenarios plus the quality-gates checklist in `SKILL.md`), not a
fresh `skill-tester` eval run — this is a new, narrow decision procedure layered onto an already-tested
skill, verified by re-reading it against the scenarios in `references/test-scenarios.md` rather than a
blind-comparison eval.

**Step 3.85 (priority-label resolution) — added 2026-09-14:** verified live — `gh pr create --help`
confirms `-l, --label name` exists as documented, and `gh label list --search "p:"` confirmed all four
`p: critical`/`p: high`/`p: medium`/`p: low` labels already exist in this repository.
**`skill-tester` blind-comparison eval (eval-5, iteration-2, 2026-09-14):** Full Pipeline,
`evals/create-pr/workspace/iteration-2/benchmark.json` — with_skill 80% (4/5 assertions), baseline 0%
(0/5) — baseline invented a generic `priority: high` label (missing this repo's `p: critical` tier
for a security-relevant bug) and omitted a label entirely for the ambiguous-tier case, the exact
anti-pattern step 3.85 exists to prevent. One honest near-miss on the with_skill side: for the
ambiguous refactor case, it resolved `p: low` (reading the change as matching the "cosmetic or
nice-to-have" criterion directly) rather than the `p: medium` default the eval expected — a
defensible reading of the documented criteria, not a failure to apply a label, but flagged here since
it didn't match the specific assertion as written.

**Step 3.85 — round-1 automated PR review findings (PR #326), fixed 2026-09-14:**
1. **Codex (P2):** step 3.85 unconditionally required this repo's own `p:` taxonomy, which would have
   blocked `/create-pr` in any other repository installing `git-kit` (a general-purpose plugin, per its
   own `plugin.json` description) without that taxonomy adopted. Confirmed real. Fixed by scoping the
   step to "this repository only — a no-op elsewhere," matching step 3.5's own existing
   repository-detection pattern (check whether `docs/github-label-taxonomy.md` exists before requiring
   anything). Applied the same scoping to `github-issue-lifecycle`'s Step 5.5 and Step 7, which Codex's
   finding explicitly named as sharing the same gap.
2. **CodeRabbit (Minor):** independently found the exact ambiguous-refactor discrepancy already
   disclosed above (eval-5 Part B expected `p: medium`, with_skill resolved `p: low`). Fixed by
   tightening `p: low`'s own criteria to require an explicit cosmetic/nice-to-have signal, rather than
   being inferable by elimination for a merely-ambiguous change — an internal refactor with no stated
   cosmetic framing now stays at the `p: medium` default. Both verified by re-reading the new wording
   against the finding each addresses, and (for finding 1) against `git-kit`'s own `plugin.json`
   description confirming it's genuinely repo-agnostic.

**`skill-tester` blind-comparison eval (eval-6, iteration-3, 2026-09-14):** Full Pipeline,
`evals/create-pr/workspace/iteration-3/benchmark.json` — with_skill 100% (4/4 assertions), baseline
50% (2/4) — baseline correctly omitted a label in the no-taxonomy repo but, without the tightened
wording, explicitly resolved `p: low` for the unframed refactor ("absent any such signal, 'low' is
the best-fit choice") — the exact anti-pattern the fix targets, confirming the fix's own necessity.
