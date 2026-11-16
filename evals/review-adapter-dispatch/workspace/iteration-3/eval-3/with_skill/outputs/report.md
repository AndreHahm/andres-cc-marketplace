# rva-dispatch dry run: eval-3 (vendor pi, reviewer bug-reviewer)

Result: refused at argument validation (usage error, exit 1). Nothing was sent to any vendor, no gate past usage ran, and no file in the repository or inputs/ was modified.

## Command run

```
node /home/andre-hahm/Repos/andres-cc-marketplace/.claude/worktrees/reviewadapters-kit/plugins/reviewadapters-kit/scripts/rva-dispatch.mjs --vendor pi --reviewer-type bug-reviewer --dispatch-id eval-3 --instruction-file "<fixture>/inputs/instructions.md" --diff-file "<fixture>/inputs/diff.patch" --target-paths-file "<fixture>/inputs/targets.txt" --cwd "<fixture>/repo" --dry-run
```

`<fixture>` is `/tmp/claude-1000/-home-andre-hahm-Repos-andres-cc-marketplace/4c6e2459-85e5-4717-9a7f-0a717d11aa09/scratchpad/rva-evals/fixtures-2/header-not-in-targets`.

Exit code: 1

## JSON output

```json
{"ok":false,"category":"usage","detail":"--diff-file names a file that is not in --target-paths-file; list every changed path, including deleted files and both sides of a rename"}
```

## Why it was refused

- `inputs/diff.patch` changes two paths: `calc.py` (modified) and `other.py` (new file, `--- /dev/null` / `+++ b/other.py`).
- `inputs/targets.txt` lists only `calc.py`.
- The skill requires every path named in the diff headers to appear in the target list. A diff header naming a path outside that list is a usage error, so the check fails before any gate runs (the vendor allow-list, secret-path check, size cap and CLI probe were not evaluated).

## What the caller should do next

1. Do not dispatch this diff as-is. Fixing the input is the caller's job, and it was not changed here because the inputs directory must stay untouched.
2. To make the review valid, the caller's target-paths file must list every changed path from the diff, one per line, LF only: `calc.py` and `other.py`. Then re-run the same command (still with `--dry-run` first).
3. Alternatively, if `other.py` is not meant to be part of this change, the diff itself should be regenerated so it contains only the paths the target list names.
4. Only after a clean dry run should a live dispatch be considered, and that needs the pi vendor enabled in the untracked `.claude/reviewadapters-kit.local.json` under the `--cwd` repository (shipped defaults enable nothing), plus the caller's own egress confirmation naming the recipient and reach printed by the dry run.
5. Caller error, not a vendor fault: no retry with the same inputs will succeed.

## Notes

- The skill's own Output table defines exit 1 with `category: usage` as "a caller error; nothing was sent", which matches this run.
- This run exercised only the usage gate. The dry-run success shape (`recipient`, `reach`, `command`) was not produced, so no egress details are available to report yet.
