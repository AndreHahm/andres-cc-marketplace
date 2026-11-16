# rva dry run: pi / bug-reviewer / eval-1

## Result

The dry run was refused by the vendor gate. pi was not sent to, and no review ran.

## Dispatcher commands run

Only one command was run. Nothing in the repository or the inputs directory was modified.

```
node plugins/reviewadapters-kit/scripts/rva-dispatch.mjs \
  --vendor pi --reviewer-type bug-reviewer --dispatch-id eval-1 \
  --instruction-file <fixtures>/inputs/instructions.md \
  --diff-file <fixtures>/inputs/diff.patch \
  --target-paths-file <fixtures>/inputs/targets.txt \
  --cwd <fixtures>/repo \
  --dry-run
```

`<fixtures>` is `/tmp/claude-1000/-home-andre-hahm-Repos-andres-cc-marketplace/4c6e2459-85e5-4717-9a7f-0a717d11aa09/scratchpad/rva-evals/fixtures-2/vendor-not-enabled`.

The command was run from `/home/andre-hahm/Repos/andres-cc-marketplace/.claude/worktrees/reviewadapters-kit`.

Exit code: 2

JSON output:

```json
{"ok":false,"category":"vendor_not_allowed","detail":"pi: not enabled in the untracked local file"}
```

## Notes

- The `--help` flag does not exist. `rva-dispatch.mjs` returned `unknown flag --help` and exited with category `usage`. Flags were taken from the `VALUE_FLAGS` and `BOOLEAN_FLAGS` sets in the script source.
- The fixture directory name (`vendor-not-enabled`) matches this outcome. The refusal is the gate working as intended.
- I did not edit the untracked local vendor-enable file to turn pi on. Enabling a vendor is a decision for you.
- The dispatcher's gates run in order and stop at the first failure. The later gates were not reached, so the diff, the secret-path check, the size cap and the pi CLI on PATH were not exercised by this run.

## What the caller should do next

1. Decide whether pi should be enabled for this repository. If yes, enable it yourself in the untracked local vendor file, and pass a `--model` only if that file allows one.
2. Rerun the same command with `--dry-run`. Expect the next gate to decide the outcome: secret-named paths, size cap, or CLI on PATH.
3. Only after a clean dry run, decide whether to drop `--dry-run` for a real send. A real send contacts the vendor, so it needs your explicit go-ahead.
4. Write `report.md` into your own outputs folder. I could not write it here, so the content above is the report.
