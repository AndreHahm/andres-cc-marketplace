# Triage: PR #150, Round 3 — README.md changelog formatting (Minor)

## Finding

**Minor** — inconsistent list formatting in `README.md`'s changelog section.

## 1. Which named exception justifies filing instead of fixing

**Direct instruction from the user.** The user reviewing this triage explicitly said: "don't fix
that one now, just file it as an issue, I want to batch changelog cleanup separately." That is an
explicit, in-the-moment instruction to divert this specific finding away from the default
fix-in-round behavior and into the Issue path instead.

This is not a case of the finding being out of scope for the PR (README.md's changelog section is
presumably part of what this PR could reasonably touch, and nothing in the prompt says the PR never
touches this file), and it is not a case of the fix being too large or complex for the session — a
list-formatting inconsistency is a trivial, mechanical fix. The only reason it isn't being fixed
right now is that the user asked for it to be deferred and batched with other changelog cleanup
work. So the justification is the user's direct request, not a property of the finding itself
(severity, file scope, or size).

Being round 3 does not change this. Round 3 is still well within `review_findings_max_rounds: 3`,
and nothing about "round 3" on its own routes a finding to filing — the routing here is entirely a
consequence of the explicit user instruction, applied independent of which round we're in.

## 2. How this commit should be labeled/described

The only thing being committed is the issue-draft file under `issues/` — no code or content in
`README.md` itself is being touched. That means this commit does not fix anything; it only records
and files a piece of documentation/tracking work. It should be labeled and described as a
**documentation/chore commit, not a fix**:

- Suggested commit type/prefix: `docs:` or `chore:` (e.g. `docs: file issue for README changelog
  formatting cleanup`), explicitly **not** `fix:`.
- Commit message body should note that this documents/tracks a deferred cleanup item rather than
  resolving it, and should reference the finding/PR context (e.g. which review round and file the
  finding came from) so the issue's provenance is traceable later.
- The issue draft's own content should carry the actual traceability details (source PR, the
  reviewer/finding text, severity, and file/line reference) so the standalone commit message doesn't
  need to duplicate all of it.

## 3. Whether committing it opens a new round window for this PR

**No.** Even though this commit changes the PR's head SHA (any commit does), it is not a
**fix-driven** push — it contains only an issue-draft file and makes no change to the actual code or
content that was reviewed. A new round is meaningfully defined by a push that is intended to address
review feedback (a fix), which then invites re-review of that fix. Pushing a documentation/tracking
artifact that explicitly defers the underlying work does not fall into that category.

Therefore:
- This commit does **not** advance the round counter — the PR remains conceptually "in round 3" for
  purposes of the fix/file/decline budget.
- It does **not** open a new round window (i.e., it should not trigger a fresh review request or be
  treated as consuming/resetting the `max_rounds` budget).
- The changed head SHA is an incidental side effect of committing the issue-draft file, not a signal
  that new review-worthy changes have been introduced.

## Summary

| Question | Answer |
|---|---|
| Exception invoked | Direct user instruction (user explicitly asked to file, not fix, this specific finding) |
| Fix / File / Decline | File (as a GitHub issue, via the issue-draft file under `issues/`) |
| Commit label | Documentation-only / chore — not a fix commit |
| Opens new round? | No — a non-fix (documentation-only) push does not advance or reset the round counter, even though it changes the head SHA |
