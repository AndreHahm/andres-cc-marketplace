# Workflow 1: Create a New Issue

## Step 1: Check for Existing Issues

Before drafting anything, search for a duplicate: `gh issue list --search "<keywords>"` and
`gh api search/issues -f q="repo:<owner>/<repo> is:issue <keywords>"`. If a real duplicate is found,
stop here and point at it instead of filing a new issue — reuses `github-issue-creator`'s own dedup
framing for the create-time case.

## Step 2: Delegate Drafting

Invoke `Skill(git-kit:github-issue-creator)` with the raw notes/logs/screenshots. That skill produces a
local markdown draft under `issues/` — it has no `gh` access and does not file anything live itself.

## Step 3: File It Live

Once the draft is approved, file it for real: `gh issue create --title "<title>" --body-file
<draft-path>`. This is this skill's own responsibility, not `github-issue-creator`'s (see that skill's
own "Not for filing directly on GitHub" note).

## Step 4: Verify

Real verification, not just checking the template's fields are filled in: reproduce the reported bug if
feasible, or re-check the claim against the current code/docs it references. A template with every
field filled in is not the same as a confirmed report — this step exists specifically because template
completeness alone was rejected as sufficient during this skill's own design (see the Concept Card's
task #8 disposition).

## Step 5: Initial Impact Analysis

A first-pass severity/impact read, using whatever the filed issue's own template fields already
capture. This is explicitly re-run (not one-shot) once the issue moves into Workflow 2 — see that
workflow's own impact-analysis step, which can escalate severity on reconfirmation.

## Step 6: Link to Originating PR (If Applicable)

If this issue originates from work on an open PR, invoke `Skill(git-kit:collaborating-on-a-pr)` to
create the PR↔issue relationship — never re-implement that linking here.
