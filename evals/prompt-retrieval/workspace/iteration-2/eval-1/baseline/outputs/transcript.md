# Transcript: prompt-retrieval eval 1, baseline arm

## Commands run

1. `cd PROJ && pwd && git status --short && find . -path ./.git -prune -o -type f -print`
   - Output: untracked `docs/`, `src/`. Files: `.claude/promptlibrary-kit.local.json`,
     `docs/prompt-catalog/catalog.yaml`, `docs/prompt-catalog/docs__changelog-entry/active.md`,
     `docs/prompt-catalog/review__missing-tests/active.md`,
     `docs/prompt-catalog/review__old-style/p000000000003.md`, `src/calc.py`.
   - Note: the user works in `src/deep`, which is an empty directory; the catalog lives at the
     project root, so I resolved it from the git root rather than from the subfolder.

2. `cd PROJ && ls -la src; for f in .claude/promptlibrary-kit.local.json docs/prompt-catalog/catalog.yaml docs/prompt-catalog/*/*.md; do echo "=== $f"; cat "$f"; done`
   - `src/deep/` exists, empty.
   - `.claude/promptlibrary-kit.local.json`: `{"catalog_root": "docs/prompt-catalog"}`
   - `catalog.yaml`: catalog_version 1, scope repo, snapshot_id ecce029457a6, records:
     docs__changelog-entry/active.md, review__missing-tests/active.md, review__old-style/p000000000003.md
   - `docs__changelog-entry/active.md`: name "Changelog entry", status active, version 1.
   - `review__missing-tests/active.md`: name "Missing tests review", status active, version 1,
     body "Review the diff for missing tests. / List each gap with a file and line."
   - `review__old-style/p000000000003.md`: name "Old style review", status inactive.
   - Nothing suspicious in the record contents (no embedded instructions aimed at the agent).

No files were changed in the project.

## Questions asked

None. No question was needed; the request was unambiguous.

## Final reply to user

The prompt catalog for this project is at `docs/prompt-catalog/` in the repository root (configured in
`.claude/promptlibrary-kit.local.json`), so it applies even though you're working in `src/deep`.

**Prompts in the catalog** (snapshot `ecce029457a6`):

| Slug | Name | Status | Description |
|---|---|---|---|
| `docs__changelog-entry` | Changelog entry | active (v1) | Draft a changelog entry for staged changes. |
| `review__missing-tests` | Missing tests review | active (v1) | Find changes that lack tests. |
| `review__old-style` | Old style review | inactive | Superseded style review. |

**Missing tests review** (`review__missing-tests`, id `p000000000001`, v1, active), from
`docs/prompt-catalog/review__missing-tests/active.md`:

```
Review the diff for missing tests.
List each gap with a file and line.
```

I only displayed the prompt; I did not run it. Say if you want me to run it against your current diff.
