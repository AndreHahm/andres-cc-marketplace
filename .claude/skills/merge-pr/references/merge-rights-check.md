# Merge-Rights Check Procedure

Three tiers, checked in order. Stop at the first one that resolves the decision — do not run later tiers once an earlier one has decided the outcome.

## Tier 1: Repo owner

```bash
gh api user --jq '.login'
gh repo view --json owner --jq '.owner.login'
```

If the two match (case-insensitive), the result is `MERGE ALLOWED` — skip Tiers 2-3 entirely.

## Tier 2: CODEOWNERS match

If Tier 1 didn't resolve it:

1. Check whether `.github/CODEOWNERS` exists (`Read` it). If it doesn't exist at all, the result is `MERGE NOT ALLOWED` — reason: "no CODEOWNERS file; ask a repo admin to run `manage-codeowners` to bootstrap one." Skip Tier 3.
2. Get the PR's changed files: `gh pr view $ARGUMENTS --json files --jq '.files[].path'`.
3. Parse CODEOWNERS: each non-comment, non-blank line is `<path-pattern> <@owner-or-team>...`. Match path patterns against the changed files using the same left-to-right, most-specific-pattern-wins precedence GitHub itself uses (a later matching line overrides an earlier one for the same path).
4. For each changed file, check whether the current user (`gh api user --jq .login`) appears as a direct `@username` owner of at least one matching pattern. **Known limitation, state this to the user if it matters:** this check only matches direct `@username` entries, not `@org/team` entries — verifying team membership would need an additional API call this skill deliberately doesn't make, to keep the check fast and simple. A user who is only covered via a team entry will read as not matching, even if GitHub itself would grant them review/merge standing through that team.
5. If the user matches at least one changed file's owner (not necessarily all of them — a deliberate choice to keep CODEOWNERS files short) → continue to Tier 3. If none match → `MERGE NOT ALLOWED`, reason: "not listed as a CODEOWNER for any file in this PR." Skip Tier 3.

## Tier 3: Collaborator permission

If Tier 2 matched:

```bash
gh api repos/{owner}/{repo}/collaborators/{username}/permission --jq '.permission'
```

(Get `{owner}/{repo}` from `gh repo view --json nameWithOwner --jq .nameWithOwner`; `{username}` from `gh api user --jq .login`.)

If the result is `admin`, `maintain`, or `write` → `MERGE ALLOWED`. Anything else (`read`, `triage`, or the call failing because the user isn't a collaborator at all) → `MERGE NOT ALLOWED`, reason: "matched CODEOWNERS but doesn't have write/maintain/admin permission on this repo."

This is always a live call — never cache or locally store a permission result. GitHub is the source of truth for collaborator permissions; a cached copy would go stale the moment someone's access changes.
