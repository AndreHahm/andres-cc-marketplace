# Triage: PR #150, Round 3 — README.md changelog formatting finding

**Finding:** Minor — inconsistent list formatting in `README.md`'s changelog section.
**Round:** 3 (well within `review_findings_max_rounds: 3`).
**Context:** The user reviewing this triage has explicitly said: "don't fix that one now, just
file it as an issue, I want to batch changelog cleanup separately." Nothing else needs fixing or
changing this round — the only thing that would be committed is the issue-draft file under
`issues/`.

## 1. Which named exception justifies filing instead of fixing

**Exception 1 — Direct instruction.** The user has explicitly instructed that this specific
finding be filed as an issue rather than fixed right now, in order to batch it with other
changelog cleanup separately. That is exactly what Exception 1 covers: "The user or a human
reviewer explicitly instructs filing an issue instead of fixing this specific finding right now."

This is **not** a round-based escalation. The old "round 3+ automatically becomes an issue"
behavior no longer exists under this skill's current round-budget design — a round-3 finding
that matches none of the three named exceptions still gets fixed like any other in-budget-round
finding. The only reason this particular finding is being filed is the user's direct
instruction, not the fact that it happens to be round 3. If the user had said nothing about it,
this finding (Minor, in-scope, trivially fixable) would have gone through the normal Fix path
just like any other round-3 finding.

It's also not Exception 2 (out-of-scope component) — the changelog section of `README.md` is
presumably a file this PR is already touching or otherwise legitimately in scope, and nothing in
the finding suggests it's an unrelated component. And it's not Exception 3 (too large for this
session) — inconsistent list formatting in a changelog is a trivial, same-session fix by any
reasonable measure; the only reason it isn't being fixed now is the user's explicit request to
batch it, not any capability or scope limitation. Exception 1 is the only exception that applies
here, and it applies purely because of the direct instruction — regardless of round.

## 2. How this commit should be labeled/described

The only file being committed this round is the issue-draft file under `issues/`
(`YYYY-MM-DD-short-description.md`, per `github-issue-creator`'s naming convention, with the
required traceability fields — PR URL, head SHA, thread/comment reference, reviewer, severity —
added as its own `## Review Finding Source` section).

This commit must be labeled/described plainly as **documentation-only**, not as a fix. There is
no code change and no behavior change in this commit — it exists solely to add a tracked issue
draft to the repo. The commit message and any report to the user should say so explicitly (e.g.
"docs: file issue for changelog formatting inconsistency — no code change"), so nobody reading
the PR history later mistakes this commit for an actual fix to the finding it references.

## 3. Whether committing it opens a new round window for this PR

**No.** Even though committing the issue-draft file changes the PR's head SHA, it does **not**
open a new round window and does **not** advance the round counter.

A round's boundary is defined specifically by *fix-driven* pushes — "round *N* opens at the push
that applied round *N-1*'s accepted fixes, and stays open until the next fix-driven push." An
issue-draft-only commit is explicitly called out as one of the causes of a SHA change that does
**not** itself open a new round: "A SHA change from an unrelated cause — a rebase onto `main`, an
unrelated commit landing on the same branch, or an issue-draft-only commit (see the Issue path) —
does not itself open a new window; the next reviewer pass against that new SHA still belongs to
whichever round's window the PR was already in."

So after this commit lands, the PR remains in round 3's window (or, if round 3 is otherwise fully
triaged, whatever round-completion state round 3 was already in) — nothing about filing this
issue starts a round 4. If another reviewer re-reviews the new head SHA later, that pass still
belongs to round 3, not a newly opened round, because this commit was never a fix-driven push.

## Thread handling

Per the Issue path: check for an existing issue against this PR/head-SHA for the same finding
first (dedup); since none exists, draft and file the issue with the full traceability payload,
using a plain non-closing reference ("Found in PR #150" — never "Fixes #150"/"Closes #150").
Then reply to the finding's own review thread pointing at the new issue number, and **leave the
thread unresolved** — a deferred finding is redirected, not handled, so resolving it would
misrepresent the state to anyone reading the PR later.

## Summary

| Question | Answer |
|---|---|
| Exception that applies | Exception 1 — direct instruction (not a round-3 escalation, and not Exceptions 2 or 3) |
| Commit label | Documentation-only (issue-draft file only; no fix) |
| Opens a new round? | No — an issue-draft-only commit is explicitly not a fix-driven push, so it never advances the round counter or opens a new window, regardless of the SHA change |
