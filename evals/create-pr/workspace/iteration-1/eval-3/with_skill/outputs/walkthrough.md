DRY RUN — narrated walkthrough only. No Bash/git/gh/Skill/Agent tool was actually invoked.

Scenario: `/create-pr 123` invoked directly (top-level, not delegated from
`collaborating-on-a-pr`). Branch `feat/example-widget`. Everything already committed and
pushed. No PR open yet. Issue #123 should be closed by this PR.

## Pre-flight Checks

1. Check for uncommitted changes: `git status`.
   - Scenario states everything is already committed, so this is a no-op — the `commit`
     skill is NOT invoked (its "skip Auto-PR step" hand-off only matters when there
     actually are uncommitted changes to commit first).

2. Mandatory cross-model-review gate, run before ever reaching `git push`:
   - Invoke `Skill(git-kit:cross-model-review)` against the full diff between
     `feat/example-widget` and its base branch (e.g. `main`).
   - Instruction I'd give it: "Run a full cross-model review of the diff on
     `feat/example-widget` against `main` before this branch's PR is opened. No bypass
     flags were supplied, so this gate is mandatory — do not skip it."
   - This runs Claude's native review plus an independent Codex review via codex-kit,
     then a two-phase cross-examination (fresh-eyes, then challenger), producing a
     ranked, confidence-scored findings table. It is report-only: it surfaces findings
     and asks which to act on, it does not touch GitHub state and does not auto-fix.
   - In this dry run I'd wait for that gate to resolve (findings addressed or explicitly
     accepted) before proceeding to PR creation. Since no bypass flag
     (`--bypass-cross-model-review "<reason>"`) was passed in `$ARGUMENTS`, this step
     cannot be skipped.
   - Note: the skill's push-ordering language ("before ever reaching `git push`") is
     already moot here since the scenario states the branch is already pushed — but the
     gate itself still must run before PR creation regardless of push timing.

## Creating the Pull Request

1. Push the current branch to remote if not already there:
   - `git branch -vv` / `git status` to confirm `feat/example-widget` is up to date with
     its remote tracking branch. Scenario says it's already pushed, so no `git push`
     call is needed here.

2. Prepare the PR description:
   - Read `.github/pull_request_template.md` if it exists in this repo; otherwise fall
     back to the skill's bundled fallback template asset.
   - Because `$ARGUMENTS` names issue `123` as an issue this PR should close, the
     description I draft includes a literal closing line, e.g.:
       `Closes #123`
     placed in the body per the template's own convention (usually near the top or in a
     "Related issue" section).

3. Ask draft vs. ready-to-merge:
   - `AskUserQuestion`: "Should this PR be created as a draft, or ready for review/merge
     immediately?" — wait for the user's answer before proceeding.

3.5. Validate the PR title:
   - `uv run python "${CLAUDE_PLUGIN_ROOT}/scripts/check-pr-title.py" "<proposed title>"`
     against this repo's CI title-policy script. If it fails, revise the title and
     re-check before continuing.

3.75. Resolve the PR assignee:
   - `gh api user --jq '.login'` to get the current authenticated GitHub user.
   - Falls back to the repo owner if that call fails or returns nothing usable.

4. Create the PR:
   - Write the git-kit marker via
     `Bash(${CLAUDE_PLUGIN_ROOT}/scripts/write-git-kit-marker.sh ...)` — this is the
     handshake `git-kit`'s `PreToolUse` hook checks for before allowing the guarded
     `gh pr create` call to proceed.
   - `gh pr create --title "<validated title>" --body-file <prepared body with "Closes
     #123"> [--draft, if the user chose draft] --assignee <resolved login> --base main
     --head feat/example-widget`.
   - At this point the PR exists and its body already contains `Closes #123`, because I
     wrote that line into the description in step 2, before creation.

5. Optional Codex-review bypass attestation:
   - Not applicable — no `--bypass-codex-review "<reason>"` flag was supplied in
     `$ARGUMENTS`, so this step is skipped entirely (nothing to attest).

6. Issue-linking hand-off (this is the second, independent mechanism that makes the
   `Closes #123` line's presence certain, not just intended):
   - This run is a direct top-level invocation of `create-pr` — it was NOT invoked as a
     nested dependency from `collaborating-on-a-pr`'s Path A, and no instruction telling
     me to skip this step is present. So the skip condition does not apply, and this step
     runs.
   - Because `$ARGUMENTS` named issue `123`, I invoke
     `Skill(git-kit:collaborating-on-a-pr)` with this explicit instruction:
       "A PR was just created on branch `feat/example-widget` (PR #<N>, the number
       returned by the `gh pr create` call above) that should close issue #123. Run only
       your Path A step 2: verify that the PR body actually contains a `Closes #123` (or
       `Refs #123`) line. Do not run any other path or step. Do not re-invoke
       `create-pr` under any circumstance — the PR already exists."
   - How `collaborating-on-a-pr` would confirm the line landed: it re-reads the PR's
     actual current body from GitHub (e.g. `gh pr view <N> --json body --jq .body`) —
     not the locally-drafted string from step 2 — because the template resolution,
     `gh pr create --body-file` encoding, or any server-side processing could have
     altered or stripped it. It checks that re-fetched body text for a `Closes #123` /
     `Refs #123` pattern.
   - If present: nothing further to do, hand-off is confirmed complete.
   - If missing: `collaborating-on-a-pr` patches it by writing a corrected body (original
     body plus the `Closes #123` line) to a temp file and running
     `gh pr edit <N> --body-file <corrected-body-file>`, then re-reads the body once more
     to confirm the patch took.
   - This two-layer approach (write it proactively in step 2, then independently verify
     and self-heal in step 6) is what the skill file itself describes as reusing
     `collaborating-on-a-pr`'s "verify-and-patch logic instead of re-deriving it here" —
     it avoids relying solely on the hope that the template/`gh pr create` round-trip
     preserved the line exactly as drafted.

## Summary of tools/skills involved in the "Closes #123" outcome

- `create-pr` (this skill, top-level): drafts the `Closes #123` line into the PR body
  before `gh pr create` runs.
- `Bash(gh pr create:*)`: creates the PR carrying that body.
- `Skill(git-kit:collaborating-on-a-pr)` (nested hand-off, step 6): re-fetches the live
  PR body via `gh pr view`, confirms the `Closes #123` line is actually present
  server-side, and — only if it's missing — patches it via `gh pr edit --body-file`. It
  is explicitly instructed to run only its Path A step 2 and never re-invoke `create-pr`,
  preventing a loop between the two skills.
