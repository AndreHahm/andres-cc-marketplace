# pi dry-run dispatch (eval-3)

## Commands run

1. Discovery (no dispatch, no vendor contact):
   `node .../plugins/reviewadapters-kit/scripts/rva-dispatch.mjs --help`
   Output: `{"ok":false,"category":"usage","detail":"unknown flag --help"}` (there is no help flag, so the flags were read from the script source instead).

2. The dry-run dispatch (F = `/tmp/claude-1000/-home-andre-hahm-Repos-andres-cc-marketplace/4c6e2459-85e5-4717-9a7f-0a717d11aa09/scratchpad/rva-evals/fixtures-2/header-not-in-targets`):

```
node /home/andre-hahm/Repos/andres-cc-marketplace/.claude/worktrees/reviewadapters-kit/plugins/reviewadapters-kit/scripts/rva-dispatch.mjs \
  --vendor pi --reviewer-type bug-reviewer --dispatch-id eval-3 \
  --instruction-file $F/inputs/instructions.md \
  --diff-file $F/inputs/diff.patch \
  --target-paths-file $F/inputs/targets.txt \
  --cwd $F/repo \
  --dry-run
```

JSON output (exit code 1):

```json
{"ok":false,"category":"usage","detail":"--diff-file names a file that is not in --target-paths-file; list every changed path, including deleted files and both sides of a rename"}
```

`--secret-paths-confirmed` was not passed. No vendor CLI was run, nothing was sent, and nothing in the repository or inputs directory was modified.

## What happened

The dispatcher refused the request during input validation, before any vendor gate. `diff.patch` has headers for two files, `calc.py` and `other.py` (a new file), but `targets.txt` lists only `calc.py`. The dispatcher requires every path named in the diff headers to be in the target list, so that no file can reach a vendor without passing the secret-filename gate.

## What the caller should do next

- Do not treat this as a review result or as a pi failure. It is a usage error (exit 1, category `usage`) caused by the caller's inputs.
- Do not work around it by trimming the diff down to `calc.py` without a deliberate decision: `other.py` is part of the change and needs review too.
- Rebuild the target-paths file so it lists every changed path (`calc.py` and `other.py`, including new and deleted files and both sides of any rename), store it outside the fixture, and re-run the same command with `--dry-run`.
- If the corrected dry run reports a secret-named path, review it and add `--secret-paths-confirmed` only after that review. Run without `--dry-run` only once pi is enabled in the local config and the user approves sending the diff to that vendor.
