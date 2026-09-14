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
