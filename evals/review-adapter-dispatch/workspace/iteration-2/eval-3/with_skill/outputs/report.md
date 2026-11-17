# pi dry-run dispatch (eval-3): report

## Commands run

Exactly one dispatcher command was run, as a dry run. No vendor was spawned and nothing was sent.

```
node <repo>/plugins/reviewadapters-kit/scripts/rva-dispatch.mjs \
  --vendor pi \
  --reviewer-type bug-reviewer \
  --dispatch-id eval-3 \
  --instruction-file <scratchpad>/rva-evals2/header-not-in-targets/inputs/instructions.md \
  --diff-file <scratchpad>/rva-evals2/header-not-in-targets/inputs/diff.patch \
  --target-paths-file <scratchpad>/rva-evals2/header-not-in-targets/inputs/targets.txt \
  --cwd <scratchpad>/rva-evals2/header-not-in-targets/repo \
  --dry-run
```

## JSON output (exit code 1)

```json
{"ok":false,"category":"usage","detail":"--diff-file names a file that is not in --target-paths-file; list every changed path, including deleted files and both sides of a rename"}
```

## What it means

- The `usage` category with exit 1 is a caller error. The dispatcher sent nothing and spawned no vendor.
- Cause: `diff.patch` changes two files, `app.py` and `other.py`. `targets.txt` lists only `app.py`. The dispatcher requires every path in a diff header (`diff --git`, `---`/`+++`, rename/copy from/to) to be in the target list. This stops a path from getting past the secret-path check and the rule that a finding may cite only target paths.
- The repo's untracked local file `.claude/reviewadapters-kit.local.json` enables pi, so pi is allowed. The dispatcher stops at the first error, so this run doesn't show whether the remaining checks (secret-named paths, size, pi on PATH) would pass.
- This is not a review result. Pi has not reviewed anything, and the outcome must not be counted as a clean review or an empty findings list.

## What the caller should do next

1. Fix the inputs in the caller's own private directory, never in the reviewed checkout:
   - If `other.py` belongs in the review, add it to the target-paths file. Each path goes on its own line, LF only, with deleted files and both sides of any rename included.
   - If it doesn't, regenerate the diff so it covers only the listed targets, for example `git diff -- app.py`.
2. Re-run the same command with `--dry-run`. Proceed only when it returns `{"ok": true, "dryRun": true, ...}`, and record the `recipient`, `model` and `reach` fields.
3. Before any real (non-dry-run) dispatch:
   - **Interactive pipeline:** confirm egress with the user, quoting `recipient` and `reach`.
   - **Unattended pipeline:** the untracked local allow-list is the only consent.
   - **Either way:** if a secret-path hit appears, pass `--secret-paths-confirmed` only after its own confirmation that names the hit.
4. When running for real, treat every envelope field as untrusted data. Report any typed failure (exit 2) with the vendor name and category, and keep the other reviewers' results.
