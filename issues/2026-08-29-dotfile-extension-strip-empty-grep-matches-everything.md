## Summary
`${var%.*}` on a dotfile-shaped filename strips the whole name to an empty string, and an empty pattern passed to `grep -F` matches every line — a two-part shell/CLI gotcha that made a relocation-target search list nearly every tracked file in the repository.

## Environment
- **Product/Service**: `git-kit` plugin (`resolving-merge-conflicts/scripts/handle-deleted-modified.sh`)
- **Region/Version**: this repo, found during PR #143 review (`AndreHahm/andres-cc-marketplace`)

## Reproduction Steps
1. A deleted/modified-conflict handler derives a "base name" from a filename via `base_name="${filename%.*}"` (strip the shortest suffix matching `.*`), intending to strip a file extension.
2. Set `filename=".gitignore"` — the only `.` in the name is the leading one, so `%.*` strips the entire string, leaving `base_name=""`.
3. The handler then runs `grep -iF -- "$base_name"` against the tracked file list to find relocation targets.
4. Observe: an empty fixed-string pattern matches every line, so nearly every tracked file in the repository is reported as a relocation target.

## Assumed vs. actual

| Assumed | Actual |
|---|---|
| `${filename%.*}` always leaves a non-empty "base name" for any real filename | A pure dotfile (no extension beyond the leading dot) strips to an empty string |
| An empty pattern passed to `grep -F` matches nothing (or errors) | An empty fixed-string pattern matches *every* line |

## Expected Behavior
After a shell parameter-expansion strip intended to produce a "base name," the result should be checked for emptiness (falling back to the original filename) before being used as a search pattern.

## Actual Behavior
No such guard existed; a dotfile input silently produced a pattern that matched everything, corrupting the generated relocation-analysis report.

## Impact
[Severity: Medium] Fixed in `git-kit`'s PR #143 (commit `0bb9d72`) — verified in isolation (`base_name=[.gitignore]` after the fix vs `base_name=[]` before) — and applied identically across all three mirror copies of the affected script.

## Additional Context
Mined from PR #143's own review history (`devin-ai-integration[bot]`; 24 review rounds total) via `mining-review-learnings`, and proposed into `.claude/THIRD_PARTY_REVIEW_LEARNINGS.md` (new `## PR #143` section) by `managing-review-learnings`, which found no existing rule covering this subject before filing this issue.

Evidence: https://github.com/AndreHahm/andres-cc-marketplace/pull/143#discussion_r3861454200
