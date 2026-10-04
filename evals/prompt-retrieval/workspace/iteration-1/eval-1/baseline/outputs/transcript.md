# Transcript (baseline)

## Commands
1. `cd <proj>/src/deep && pwd && ls -la && ls -la .. ../.. && find ../.. -ipath '*prompt*' -not -path '*/.git/*' | head -50`
   - src/deep is empty; project root has .claude, docs, src. Found .claude/promptlibrary-kit.local.json, docs/prompt-catalog/{catalog.yaml, docs__changelog-entry/active.md, review__missing-tests/active.md, review__old-style/p000000000003.md}
2. `cd <proj>/src/deep && cd ../.. && cat .claude/promptlibrary-kit.local.json; cat docs/prompt-catalog/catalog.yaml; cat <the three prompt files>`
   - config: {"catalog_root": "docs/prompt-catalog"}
   - catalog.yaml lists 3 records; statuses: changelog-entry active, missing-tests active, old-style inactive.
   - missing-tests body: "Review the diff for missing tests.\nList each gap with a file and line."

## Questions
None.

## Final reply
The prompt catalog is at `docs/prompt-catalog` (project root, found via `.claude/promptlibrary-kit.local.json`; your src/deep folder has no catalog of its own). It contains 3 prompts:

| Slug | Name | Area | Status |
|---|---|---|---|
| docs__changelog-entry | Changelog entry | docs | active |
| review__missing-tests | Missing tests review | review | active |
| review__old-style | Old style review | review | inactive |

The one for reviewing missing tests (`review__missing-tests`, v1, active, id p000000000001):

```
Review the diff for missing tests.
List each gap with a file and line.
```
