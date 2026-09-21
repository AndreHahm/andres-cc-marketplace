## Summary
Two independent failures this session let a live PR-review triage bypass `handling-review-findings`
entirely: once by an agent choosing to hand-triage via raw `gh api` calls instead of invoking the skill
at all, and once by an agent's own `Skill()` dispatch attempt silently failing on a wrong-but-plausible
scoped name (`git-kit:handling-review-findings`) that this session's dispatch mechanism doesn't
recognize — the bare name (`handling-review-findings`) does, and correctly resolves the `.claude/`
mirror. Both times, the agent fell back to manually narrating the skill's documented procedure instead
of a real, separately-verified invocation.

## Environment
- **Product/Service**: `plugins/git-kit/skills/handling-review-findings/` (mirrored under
  `.claude/skills/handling-review-findings/`), and more broadly every `Skill(git-kit:<name>)`-style
  cross-reference throughout git-kit's own skill files
- **Region/Version**: this repo, observed live during PR #364's own review triage, 2026-09-21

## Reproduction Steps
1. **Incident 1 (round 1, no dispatch attempted at all):** after PR #364's round-1 review findings
   (CodeRabbit + Codex) landed, the triaging agent fixed both findings and replied to both threads via
   direct `gh api repos/{owner}/{repo}/pulls/{n}/comments/{id}/replies` calls — never invoking
   `handling-review-findings` at all, and never writing the marker
   `guard-raw-pr-review.sh` requires before those calls. The calls succeeded anyway, because that guard
   has its own separate, independently-confirmed bypass (issue #365) — but the deeper problem
   demonstrated here is that nothing prompted or required going through the skill for a task squarely
   inside its own documented "When to Use" list in the first place.
2. **Incident 2 (round 2, dispatch attempted, wrong name, silent fallback):** asked to "start a next
   reviewer round using `handling-review-findings`," the agent called
   `Skill(skill: "git-kit:handling-review-findings")`, which returned `Unknown skill:
   git-kit:handling-review-findings`. The agent then fell back to manually reading and narrating the
   skill's file content by hand for the rest of that round's triage, rather than a genuine invocation.
3. Verified live just now: `Skill(skill: "handling-review-findings")` (bare name, no `git-kit:` prefix)
   **does** resolve successfully, reporting its own base directory as
   `/home/andre-hahm/Repos/andres-cc-marketplace/.claude/skills/handling-review-findings` — confirming
   the dispatch mechanism works fine in this session and uses the `.claude/` mirror, and that the
   scoped `git-kit:` prefix is what actually caused Incident 2's failure.
4. Confirmed this isn't a one-off wording choice: `grep -rlo "Skill(git-kit:" plugins/git-kit/skills/*/SKILL.md`
   matches 10 of git-kit's own skill files, with at least 8 distinct skills cross-referenced via that
   exact scoped form (`Skill(git-kit:commit)`, `Skill(git-kit:create-pr)`,
   `Skill(git-kit:collaborating-on-a-pr)`, `Skill(git-kit:cross-model-review)`,
   `Skill(git-kit:finishing-work)`, `Skill(git-kit:github-issue-creator)`,
   `Skill(git-kit:github-issue-lifecycle)`, `Skill(git-kit:manage-codeowners)`, and more) — every one of
   these is a documented instruction for an agent, reading that same SKILL.md, to dispatch a sibling
   skill using a form this session's own dispatch mechanism doesn't recognize.

## Expected Behavior
A skill correctly named and cross-referenced per this repo's own pervasive documented convention should
dispatch successfully, or fail in a way that doesn't silently invite a full manual reimplementation of a
security/process-relevant workflow (marker handshakes, round/dedup budget tracking, fix/issue/decline
routing, reply-then-resolve discipline) by an agent working around the failure instead of surfacing it.

## Actual Behavior
- The scoped `Skill(git-kit:<name>)` form documented throughout git-kit's own skills fails outright in
  this session with no indication of the correct alternative.
- Nothing in `handling-review-findings`, `route-through-git-kit-lifecycle-skills.md`, or any adjacent
  rule requires — or even prompts consideration of — actually invoking the skill (via a working
  dispatch) before hand-triaging a PR review round; an agent can silently substitute its own narrative
  reimplementation of the whole workflow with no structural signal that this happened.
- The consequence isn't hypothetical: Incident 1's skip is exactly what let `guard-raw-pr-review.sh`'s
  bypass residual (#365) go unexercised by its own intended safeguard and reach GitHub unblocked.

## Impact
**High**, per explicit request — this isn't a narrow formatting bug but a structural gap in the one
skill this repo relies on to safely and consistently triage third-party PR review findings (round
budgeting, dedup, severity-gate discipline, and GitHub-side reply/resolve/issue-filing mechanics all
live only in this skill). A dispatch failure or an agent's own choice to skip it currently degrades
silently to an unverified manual narration with no safeguard catching the substitution.

## Additional Context
Not prescriptive about the fix shape — possible directions worth reviewing together, not mandated
individually:
- Determine and document the actually-correct skill-dispatch name form for this repo/session context
  (bare name vs. `plugin:skill`), and correct or annotate the ~10-file `Skill(git-kit:<name>)` convention
  throughout git-kit's own skills if it's systematically wrong for how skills are actually invoked here.
- Consider whether `handling-review-findings` (or a wrapping rule) should have some structural signal —
  even a lightweight one — when a PR-review triage happens without ever having gone through the skill,
  rather than relying entirely on the operator noticing after the fact, as happened here.
- Re-verify `guard-raw-pr-review.sh`'s marker-handshake guard actually gets exercised end-to-end by a
  real `handling-review-findings` invocation now that the correct dispatch form is known, rather than
  only by hand-simulation of its marker-write step (which is what both this session's rounds ultimately
  did, even the "correct" one).

## Related
- #365 — the specific guard-script bypass this session's Incident 1 skip left unexercised. Filed
  separately since it's a self-contained, narrowly-scoped regex/tokenization bug in one script, while
  this issue is about the broader dispatch-reliability and process-integrity question around the skill
  that's supposed to route through that guard in the first place. Linked as a sub-issue of this one.
