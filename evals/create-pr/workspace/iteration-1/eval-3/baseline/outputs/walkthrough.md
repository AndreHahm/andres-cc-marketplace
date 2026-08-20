BASELINE WALKTHROUGH — /create-pr 123
(No specialized skill/methodology used. Standard Claude capabilities + general git/GitHub knowledge only. DRY RUN — no Bash/git/gh/Skill/Agent tools actually invoked.)

=====================================================================
PART A: /create-pr 123
=====================================================================

Starting state: branch feat/example-widget, all changes committed and pushed to origin,
no PR currently open for this branch, issue #123 exists and should be closed by this PR.

Assumptions I'm making explicit up front (since I have no repo-specific skill telling me
otherwise):
- "/create-pr" is a thin wrapper whose job is ultimately to run `gh pr create` with a
  well-formed title/body.
- GitHub auto-closes an issue on PR merge only when the PR body contains one of GitHub's
  recognized closing keywords immediately followed by the issue reference, e.g.
  "Closes #123", "Fixes #123", or "Resolves #123" — and only when the PR targets the
  repository's default branch.
- I have no dedicated "issue-linking" tool in this baseline, so I'll build that line into
  the PR body myself, by hand, as part of composing the body text.

Step-by-step sequence:

1. Confirm local state matches assumptions.
   - `git status` → expect "nothing to commit, working tree clean".
   - `git branch --show-current` → expect `feat/example-widget`.
   - `git log origin/feat/example-widget..HEAD` and the reverse → expect both empty,
     confirming local and remote are in sync (already pushed).

2. Confirm no PR is already open for this branch (avoid creating a duplicate).
   - `gh pr list --head feat/example-widget --state open`
   - Expect zero results, per the stated starting state.

3. Pull issue #123's details so the PR title/body can reference it meaningfully.
   - `gh issue view 123 --json title,number,body`
   - Use the issue title to help write a sensible PR title/summary (not strictly required,
     but good practice), and to sanity-check that #123 is really the issue meant here.

4. Compose the PR title and body.
   - Title: short, descriptive of the change (e.g. "Add example widget component"),
     independent of the issue-closing mechanism.
   - Body: a normal description of the change (what/why, test notes), PLUS a dedicated
     line using GitHub's closing-keyword syntax:

         Closes #123

     This line must be on its own (or otherwise unambiguous) and must reference the issue
     number exactly — GitHub only recognizes the keyword+"#"+number pattern, not e.g.
     "issue 123" or "see #123".

5. Decide draft vs. ready-for-review.
   - No instruction was given either way. Baseline behavior: ask the user (or default to
     "ready for review" if this repo has no stated draft convention) before creating.
     I'd surface this as a confirmation rather than silently picking one.

6. Create the pull request.
   - `gh pr create --title "<title>" --body "<body with Closes #123>" --base main --head feat/example-widget`
     (or `--draft` depending on step 5's answer).
   - This is the ONLY tool/mechanism involved in making the issue-closing line land in the
     PR — there is no separate skill or delegated call in this baseline; the closing
     keyword is simply text I put into the `--body` argument of the same `gh pr create`
     invocation that creates the PR. Nothing else needs to run for the link to exist.

7. Capture the resulting PR number/URL.
   - `gh pr view --json number,url` (on the now-current branch) to get the PR number for
     the next verification step.

8. Verify the "Closes #123" line actually landed in the PR body (don't just trust the
   command succeeded).
   - Primary check: `gh pr view <number> --json body --jq .body` and confirm the string
     "Closes #123" (or whichever keyword was used) is present verbatim.
   - Stronger check: `gh pr view <number> --json closingIssuesReferences` — GitHub CLI
     exposes the issues GitHub itself has parsed out of the body as "will be closed by
     this PR" via this field. Confirming `123` appears in that list is better evidence
     than a body-text grep, since it reflects GitHub's own interpretation of the keyword,
     not just that the substring exists somewhere in the text.
   - Optional belt-and-suspenders: `gh issue view 123 --json body,timelineItems` or simply
     opening the issue in the UI — a correctly-linked issue shows a "Development" sidebar
     entry pointing at the new PR.

9. Report the PR URL and confirmation of the issue link back to the user.

=====================================================================
PART B: /create-pr 123 --bypass-cross-model-review "already reviewed manually"
=====================================================================

Same starting state as Part A, but the invocation now also carries a bypass flag with a
justification string.

Baseline caveat: I have no specific knowledge of a "cross-model-review" mechanism in this
repo (that would be skill-specific knowledge I don't have access to here). I'm treating
`--bypass-cross-model-review "<reason>"` generically, as a flag that tells the /create-pr
command to skip some kind of automated pre-PR review/gate step, recording the supplied
reason as justification for the skip. I'm flagging this explicitly as an assumption rather
than asserting it as fact.

Sequence:

1-4. Identical to Part A steps 1-4: verify clean/pushed state, verify no open PR, pull
     issue #123 context, compose title and body (including the "Closes #123" line). The
     presence of the bypass flag has no bearing on any of this — it's still the same repo
     state and the same issue being linked.

5. Detect and handle the bypass flag.
   - Before whatever pre-PR review/check step would normally run (e.g., a review gate,
     lint/test gate, or similar), check for `--bypass-cross-model-review`.
   - Since it's present with a reason string, skip that review step rather than running it,
     and record the justification — most plausibly as a note appended to the PR body (e.g.
     an HTML comment or a "Review bypassed: already reviewed manually" line) or as a PR
     comment posted right after creation, so there's an audit trail. Exactly where this
     justification is recorded is implementation-specific and not something I can verify
     without seeing the actual bypass mechanism's code — I'd surface this uncertainty to
     the user rather than guess confidently.
   - I would NOT silently drop the justification string; per general good practice, a
     bypass of a safety/review gate should leave some visible trace.

6. Decide draft vs. ready-for-review — same as Part A step 5, unaffected by the bypass flag.

7. Create the pull request.
   - `gh pr create --title "<title>" --body "<body with Closes #123 [+ bypass note if applicable]>" --base main --head feat/example-widget`
   - Same single command as Part A; the bypass flag does not change what goes into the
     issue-closing line itself, and does not add any extra step between "compose body" and
     "run gh pr create" other than the review-skip decision made in step 5.

8. Capture PR number/URL — same as Part A step 7.

9. Verify "Closes #123" landed — same as Part A step 8 (`gh pr view --json body` grep, and
   `closingIssuesReferences` check). The bypass flag has no effect on this verification;
   it's checking GitHub's parsing of the body text, which is unrelated to whether a review
   step ran beforehand.

10. Report back: PR URL, confirmation of the issue link, AND an explicit note that the
    cross-model review step was bypassed with the given reason, so the user isn't left
    unaware that a normal gate was skipped.

Do the two mechanisms interact?

- Does the bypass flag change how issue #123 gets linked? No. Issue-linking is purely a
  matter of what text goes into the PR body passed to `gh pr create`; the bypass flag
  governs an unrelated pre-PR review/gate step and never touches body composition for the
  "Closes #123" line.
- Does the issue-linking step change how the bypass is handled? No. Nothing about closing
  an issue requires or affects a review step, and nothing in step 5's bypass handling reads
  or depends on the issue number.
- Conclusion: under this baseline's generic understanding, the two mechanisms run fully
  independently and are composed only by both happening to be arguments/behaviors of the
  same overall /create-pr invocation and the same single `gh pr create` call at the end.
  I can't rule out that a more specific, repo-aware implementation makes them interact
  (e.g., a bypass justification being required to also reference the issue, or the review
  step itself checking for issue linkage) — I don't have visibility into that without the
  actual command/skill definition, so I'd flag that as an open question rather than assert
  independence with full confidence.
