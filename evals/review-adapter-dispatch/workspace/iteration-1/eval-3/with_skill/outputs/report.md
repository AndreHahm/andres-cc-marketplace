# review-adapter-dispatch dry run: pi, bug-reviewer, eval-3

## Command run (the only dispatcher invocation)

F=/tmp/claude-1000/-home-andre-hahm-Repos-andres-cc-marketplace/4c6e2459-85e5-4717-9a7f-0a717d11aa09/scratchpad/rva-evals/fixtures-2/header-not-in-targets

```
node /home/andre-hahm/Repos/andres-cc-marketplace/.claude/worktrees/reviewadapters-kit/plugins/reviewadapters-kit/scripts/rva-dispatch.mjs \
  --vendor pi --reviewer-type bug-reviewer --dispatch-id eval-3 \
  --instruction-file $F/inputs/instructions.md \
  --diff-file $F/inputs/diff.patch \
  --target-paths-file $F/inputs/targets.txt \
  --cwd $F/repo \
  --dry-run
```

## Output (exit code 1)

```json
{"ok":false,"category":"usage","detail":"--diff-file names a file that is not in --target-paths-file; list every changed path, including deleted files and both sides of a rename"}
```

## What it means

Exit 1 with `category: "usage"` is a caller error. Nothing was sent to any vendor, and pi was not started.
The dispatcher rejected the input before it reached the dry-run summary (recipient, model, reach, command).

The cause: `diff.patch` has two file sections. One is `calc.py` (modified). The other is `other.py`, a new
file with headers `--- /dev/null` and `+++ b/other.py`. `targets.txt` lists only `calc.py`. The skill
requires every path named in a diff header to be in the target list.

## What the caller should do next

1. Rebuild the target-paths file from the same diff so it lists every changed path: here `calc.py` and
   `other.py`. Deleted files and both sides of a rename also belong in it. Use one path per line with LF
   line endings. Write the file to the caller's own private directory, and do not edit the shared inputs
   in place unless you own them. If `other.py` was not meant to be reviewed, you can remove its section
   from the diff instead. Do not remove it just to get past the check.
2. Run the same command again with `--dry-run`. Expect exit 0 and
   `{ "ok": true, "dryRun": true, "vendor", "recipient", "model", "reach", "command" }`.
3. Confirm data egress using the `recipient` and `reach` values from that output, either interactively or
   from the unattended configuration. Only then run the command without `--dry-run`.
4. Do not retry the identical command, because a usage error will repeat. Do not treat it as an empty
   findings list. If the pipeline continues without pi, report pi as a skipped reviewer.

## Notes

- The repo's untracked `.claude/reviewadapters-kit.local.json` enables `pi` (and `dev_sibling_codex_kit`),
  so the vendor allow-list gate will most likely pass once the input is fixed. This is not verified,
  because the dry run stopped at the input check.
- No vendor CLI was run. Nothing under fixtures-2 was created, changed or staged. The repo's working-tree
  status (`M calc.py`, `A other.py`) is the fixture's own state as found.
