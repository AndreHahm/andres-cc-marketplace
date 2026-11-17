# rva-dispatch dry run: pi, bug-reviewer, dispatch eval-3

## Result

The dispatch was refused before anything was sent. The run was a dry run (`--dry-run`), so no vendor was contacted in any case. The refusal is the dispatcher's own gate, and it is the expected outcome for this fixture (`header-not-in-targets`).

Cause: `diff.patch` names two files, `calc.py` and `other.py`, but `targets.txt` lists only `calc.py`. The dispatcher refuses any diff whose headers name a file missing from the target list, so that a file could not be sent past the secret-name gate.

## Commands run

Command 1 (usage check, read-only): `node .../plugins/reviewadapters-kit/scripts/rva-dispatch.mjs --help`
JSON output:
```
{"ok":false,"category":"usage","detail":"unknown flag --help"}
```
I then read the dispatcher source (`rva-dispatch.mjs`) to get the flag set. It has no `--help`.

Command 2 (the dry run):
```
node <repo>/plugins/reviewadapters-kit/scripts/rva-dispatch.mjs \
  --vendor pi --reviewer-type bug-reviewer --dispatch-id eval-3 \
  --instruction-file "<fixtures>/header-not-in-targets/inputs/instructions.md" \
  --diff-file "<fixtures>/header-not-in-targets/inputs/diff.patch" \
  --target-paths-file "<fixtures>/header-not-in-targets/inputs/targets.txt" \
  --cwd "<fixtures>/header-not-in-targets/repo" \
  --dry-run
```
(`<fixtures>` is `<scratchpad>/rva-evals/fixtures-2`.)

JSON output (exit code 1):
```
{"ok":false,"category":"usage","detail":"--diff-file names a file that is not in --target-paths-file; list every changed path, including deleted files and both sides of a rename"}
```

Also read, not modified: `inputs/instructions.md` ("You are a code reviewer. Report bugs in the diff."), `inputs/diff.patch` (changes `calc.py` `add` from `+` to `-`, and adds `other.py` with `sub` returning `a + b`), `inputs/targets.txt` (`calc.py`).

## What the caller should do next

1. Do not treat this as a passing dry run. The dispatcher's own gate refused it, and it never reached the vendor gates (vendor config, CLI on PATH, version probe).
2. If the goal is the `header-not-in-targets` eval, this refusal is the intended result. Record it as the pass condition.
3. If the goal is a real pi dry run of this diff, the target list must list every changed path, so `other.py` needs to be added to `targets.txt`. I did not make that change, because you asked me not to modify the inputs. Re-run the same command after the fix. The flag set and paths above are unchanged.
4. Nothing was sent to any vendor. Every run was a dry run, and the refusal happened before the vendor step. The dispatcher's temp run directory is removed in its `finally` block.
5. No file was written to the repository or to `inputs/`. I could not write `report.md`, so this text is its content.

Absolute paths used: `<repo>/plugins/reviewadapters-kit/scripts/rva-dispatch.mjs`, `<scratchpad>/rva-evals/fixtures-2/header-not-in-targets/inputs/targets.txt`.
