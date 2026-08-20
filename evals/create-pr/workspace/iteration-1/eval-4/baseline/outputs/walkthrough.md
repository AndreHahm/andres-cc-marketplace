BASELINE WALKTHROUGH (DRY RUN — no Bash/git/gh/Skill/Agent tools invoked)
Context: on branch feat/example-widget, everything committed and pushed, no PR open, no issue mentioned.
No special skill or methodology used — standard git/GitHub knowledge only.

================================================================================
PART A — create a PR with --bypass-codex-review "tested manually, urgent hotfix"
================================================================================

Step 1: Pre-flight checks (would run, narrated only)
  - `git status` -> confirm working tree is clean (already stated).
  - `git rev-parse --abbrev-ref HEAD` -> confirm current branch is feat/example-widget.
  - `git log origin/main..HEAD --oneline` -> gather the commits that will make up the PR
    title/body.
  - `git rev-parse HEAD` -> capture the current head SHA. This SHA matters later because
    the bypass attestation should be bound to a specific commit, not to the branch name in
    general — if the branch is pushed to again after the bypass is granted, the bypass
    should not silently continue to apply to the new SHA.
  - `gh pr list --head feat/example-widget --state open` -> re-verify no PR is already open
    right before creating one (state may have changed since the user described it; don't
    trust a description of state from earlier in the conversation as still current).

Step 2: Create the PR
  - `gh pr create --base main --head feat/example-widget --title "<derived from commit
    log>" --body "<template-filled body>"`
  - `--bypass-codex-review "<reason>"` is not a native `gh` flag — it must be a
    repo-specific convention layered on top of PR creation (e.g. this marketplace's own
    tooling/CI gate around a required "Codex review" status check). Its purpose is to let
    an authorized human explicitly override that automated review requirement, with a
    recorded justification, rather than silently skipping it.

Step 3: The attestation flow after the PR is created
  What gets RESOLVED:
  - The acting user's identity: `gh api user --jq .login` (the authenticated GitHub
    identity making the bypass request) — this is who the bypass gets attributed to, not
    whatever name might appear in local `git config user.name`, since the latter is
    unauthenticated and self-reported.
  - The exact head SHA of the PR at the moment of attestation: re-run `git rev-parse HEAD`
    (or read the PR's `headRefOid` via `gh pr view --json headRefOid`) immediately before
    posting anything — not reused from Step 1's earlier read. State can change between
    "I checked" and "I acted," so the SHA the bypass is bound to must be the freshest one
    available at the point of the side-effecting action (posting the attestation), not an
    earlier snapshot.

  What gets CHECKED:
  - The actor's permission level on the repository: `gh api
    repos/{owner}/{repo}/collaborators/{login}/permission --jq .permission`. A
    security-relevant override like "skip required review" should only be honorable by
    someone with at least `write` permission — `maintain` and `admin` also qualify;
    `read` or `triage` should not be able to self-authorize a bypass of a required check.
  - Whether a Codex-review-required branch protection rule is actually in effect for the
    base branch (so the bypass has something meaningful to override) — otherwise the
    bypass action would be a no-op worth flagging back to the user.

  What gets POSTED:
  - A structured record of the bypass: PR comment (`gh pr comment <number> --body-file
    <tempfile>`) and/or a label such as `codex-review-bypassed` applied via `gh pr edit
    <number> --add-label`. The posted content includes: actor login, UTC timestamp, the
    resolved head SHA, and the reason text verbatim ("tested manually, urgent hotfix").
    This is the audit trail — a bypass with no recorded reason or actor is not
    distinguishable later from a check that was simply never configured.
  - Applying the label (rather than just leaving a comment) is what's likely to actually
    satisfy or re-evaluate the branch-protection status check, similar to a
    label-triggers-workflow pattern.

  How the reason text is SAFELY EMBEDDED:
  - The reason string is written to a temporary file (in a scratch/tmp location, never
    interpolated directly into a shell command string) using a structured file-write, then
    referenced via `gh pr comment --body-file <path>` (or `gh api ... --input <path>` for
    a JSON payload via the REST/GraphQL API). This avoids the classic shell-injection /
    quoting failure mode where a reason containing quotes, backticks, `$( )`, or embedded
    newlines would otherwise corrupt or break out of an inline `--body "..."` argument.
  - If posted through `gh api` as JSON, the reason is placed in a JSON field value using a
    file-based payload rather than string-concatenated JSON, so no manual escaping of
    special characters is required.

Step 4: Report back to the user
  - PR URL, confirmation that the bypass attestation was recorded (actor, SHA, reason,
    timestamp) and that this overrides — rather than silently skips — the Codex-review
    requirement. This is disclosed explicitly, not left implicit, since it's a deviation
    from normal review process on a "hotfix" framed as urgent.

================================================================================
PART B — create a PR with --bypass-codex-review "" (empty reason)
================================================================================

An empty reason provides no audit value — "why was review skipped" would resolve to
nothing. Standard defensive behavior for a security-relevant override:

  - Validate the reason argument (after trimming whitespace) BEFORE creating the PR or
    posting any attestation. An empty/whitespace-only string should be rejected outright.
  - Do NOT silently proceed by posting an attestation comment with empty content, and do
    NOT treat the bypass as granted. Posting an empty justification would satisfy the
    mechanical "a comment was posted" check while defeating the entire point of the
    attestation (accountability).
  - Correct behavior: stop and ask the user to supply an actual justification (or fall
    back to normal required review if the user doesn't want to supply one). This should be
    surfaced as an explicit question/error, not a guess at what "urgent" might mean, and
    not a silent pass-through.
  - The PR itself can still be created normally (PR creation and the bypass attestation are
    two separate actions) — but it would remain subject to the normal, non-bypassed
    Codex-review requirement, since no valid attestation exists to override it.

================================================================================
PART C — actor from Part A lacks write/maintain/admin permission
================================================================================

What is reported:
  - The permission check (`gh api repos/{owner}/{repo}/collaborators/{login}/permission`)
    returns a level below the required threshold (e.g. `read` or `triage`), or a
    403/404 if the actor isn't a collaborator on the repo at all.
  - This is reported to the user clearly and explicitly, e.g.: "The bypass could not be
    authorized — actor <login> has '<level>' permission on this repository, which does not
    meet the write/maintain/admin threshold required to self-authorize a Codex-review
    bypass. The bypass was NOT applied."
  - No bypass comment/label is posted on the actor's behalf, since posting one would create
    a misleading audit record suggesting an authorized override occurred when it did not.

Is the PR itself affected:
  - No. PR creation and the bypass attestation are independent actions. The PR (from Step
    2 in Part A) still exists / would still be created normally — the failure is scoped
    only to the bypass authorization step, not to PR creation itself.
  - The PR remains open and unaffected, but the required Codex-review status check stays
    in force (not overridden) — it would still need either an actual completed Codex
    review, or a bypass attempt from a user who does meet the permission threshold, before
    the PR could merge.
  - This distinction — "PR is fine, only the override failed" — is reported explicitly
    rather than left ambiguous, so the user doesn't mistakenly believe the PR is blocked
    outright or, conversely, that it was bypassed anyway.
