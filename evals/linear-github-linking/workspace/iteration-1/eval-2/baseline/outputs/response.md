# Linear ↔ GitHub Drift Check: ENG-451

## What I did

1. **Linear lookup** — Queried the Linear MCP connector directly:
   - `get_issue(id="ENG-451")` → returned an error: `"Could not find referenced Issue."` (HTTP 400)
   - `list_issues(query="ENG-451")` → 0 results
   - `list_issues(query="auth")` → 0 results
   - `list_teams()` → the only team in this Linear workspace is **"AndreHahm"**, whose issues use the identifier prefix **`AND-`** (e.g. `AND-1` … `AND-9`). There is no `ENG` team in this workspace.
   - `list_issues(limit=20)` → confirmed the full current issue list is `AND-1` through `AND-9`; no `ENG-451` exists anywhere in it.

2. **GitHub lookup** — Determined the repo from the local git remote (`origin` → `https://github.com/AndreHahm/andres-cc-marketplace.git`), then used `gh`/`git`:
   - `gh pr view 201 --repo AndreHahm/andres-cc-marketplace` → `GraphQL: Could not resolve to a PullRequest with the number of 201.`
   - `gh pr view 205 --repo AndreHahm/andres-cc-marketplace` → `GraphQL: Could not resolve to a PullRequest with the number of 205.`
   - `git ls-remote --heads origin | grep -i "fix/eng-451"` → no match (exit 1, empty result)
   - For context: `gh pr list --state all --limit 5` shows this repo's real PRs are currently numbered in the **300s** (e.g. #311, #310, #308, #306, #304) — PR numbers #201/#205 are far outside the repo's actual PR range.
   - `git ls-remote --heads origin | grep -iE "eng|auth"` → no match; the repo currently has only **4** remote branches total, none related to "eng" or "auth".

## Findings

| Evidence entry | Claimed reference | Checked against | Result |
|---|---|---|---|
| Linear issue | `ENG-451` | Linear workspace (`AndreHahm`, team prefix `AND-`) | **Not found.** No `ENG` team exists in this Linear workspace; no issue `ENG-451` exists anywhere in it (full issue list is `AND-1`–`AND-9`). |
| GitHub evidence #1 | PR #201 | `AndreHahm/andres-cc-marketplace` on GitHub | **Not found.** GitHub API cannot resolve a PR numbered 201 in this repo. |
| GitHub evidence #2 | PR #205 | `AndreHahm/andres-cc-marketplace` on GitHub | **Not found.** GitHub API cannot resolve a PR numbered 205 in this repo. |
| GitHub evidence #3 | branch `fix/eng-451-auth` | `AndreHahm/andres-cc-marketplace` remote heads | **Not found.** No matching branch on `origin`. |

## Assessment / Conclusion

I could not perform a meaningful "drift" comparison, because the premise of the request doesn't hold up against what's actually reachable from this session:

- **The Linear issue ENG-451 itself does not exist** in the only Linear workspace this session has access to. That workspace uses a completely different team/identifier scheme (`AND-` prefix, team "AndreHahm"), not `ENG`. So there is no live Linear record to read "three recorded Git/GitHub evidence entries" from in the first place — I was not able to independently confirm the issue even carries those three evidence entries, since I never located the issue to inspect.
- **None of the three GitHub artifacts exist either**, in the one GitHub repository this session is rooted in (`AndreHahm/andres-cc-marketplace`): PR #201, PR #205, and branch `fix/eng-451-auth` all come back as not found, and the repo's real PR numbering (currently in the 300s) and branch list (4 total remote branches, none auth/eng-related) make it clear these were never live artifacts in this repo.

**Bottom line:** This isn't a case of "evidence has drifted from current state" (e.g., a PR that merged, or a branch that was deleted after merge, in a way that changed the recorded state) — it's that neither side of the comparison is reachable at all from this session. Possible explanations, none of which I can verify further with the tools available here:
- `ENG-451` and the associated PRs/branch belong to a different Linear workspace and/or a different GitHub organization/repo than the ones this session is authenticated against.
- The issue/PRs/branch are fictional or were used only as an illustrative example in the request.
- They existed at some point but have since been deleted/purged from both systems (unlikely to explain the Linear side, since Linear doesn't even have a matching team prefix).

**Recommendation:** If `ENG-451` is expected to be real, confirm (a) which Linear workspace it lives in (this session only has access to the "AndreHahm" / `AND-` workspace) and (b) which GitHub org/repo hosts PR #201, PR #205, and branch `fix/eng-451-auth`, then re-run this check against the correct workspace/repo. As it stands, no drift can be assessed because none of the four referenced artifacts (the issue, both PRs, and the branch) could be located in the systems reachable from this session.
