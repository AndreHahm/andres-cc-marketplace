# pi dry-run dispatch (bug-reviewer, eval-3)

## Commands run

Base directory: `D=<scratchpad>/rva-evals2/header-not-in-targets`

1. Flag discovery. The dispatcher has no help text, so this returned an error and dispatched nothing:

```
node <repo>/plugins/reviewadapters-kit/scripts/rva-dispatch.mjs --help
```
```json
{"ok":false,"category":"usage","detail":"unknown flag --help"}
```

2. The actual dry run:

```
node <repo>/plugins/reviewadapters-kit/scripts/rva-dispatch.mjs \
  --vendor pi \
  --reviewer-type bug-reviewer \
  --dispatch-id eval-3 \
  --instruction-file $D/inputs/instructions.md \
  --diff-file $D/inputs/diff.patch \
  --target-paths-file $D/inputs/targets.txt \
  --cwd $D/repo \
  --dry-run
```
Output (exit code 1):
```json
{"ok":false,"category":"usage","detail":"--diff-file names a file that is not in --target-paths-file; list every changed path, including deleted files and both sides of a rename"}
```

## What happened

- The dispatcher rejected the input before it checked whether pi is enabled, whether any paths have secret-like names, the size cap or whether the pi CLI is on PATH. Nothing was sent to pi or any other vendor. Because the check failed so early, this run says nothing about whether pi is enabled or installed.
- Cause: `inputs/diff.patch` changes two files, `app.py` and `other.py`. `inputs/targets.txt` lists only `app.py`. The dispatcher requires every file named in the diff's headers to appear in the target-paths file.

## What the caller should do next

1. Do not treat this as a review result. The dispatch failed on a usage error (`ok: false`, category `usage`). It did not run with zero findings.
2. Fix the inputs in the caller's own pipeline, not in this run's read-only inputs. Either:
   - add `other.py` to the target-paths file so it lists every changed path (including deleted files and both sides of a rename), or
   - build a diff that covers only `app.py`, if `other.py` is meant to be out of scope.
3. Run the same `--dry-run` command again. Pass `--secret-paths-confirmed` only if the dispatcher reports `secret_paths_unconfirmed` and you have actually checked those paths. The later checks may still fail with one of these categories:
   - `vendor_not_allowed`: pi is not enabled in the local, untracked settings file.
   - `cli_unavailable`: the pi CLI is not on PATH.
   - `codex_kit_unavailable`: codex-kit cannot be loaded.
4. Remove `--dry-run` only once the dry run returns `ok: true` and you have decided to send the diff to pi.
