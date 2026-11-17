# Dry-run dispatch: pi as bug-reviewer (dispatch id eval-1)

## Command run

Only one dispatcher command was run. It used `--dry-run`, and nothing was sent to any vendor.

```
node <repo>/plugins/reviewadapters-kit/scripts/rva-dispatch.mjs \
  --vendor pi \
  --reviewer-type bug-reviewer \
  --dispatch-id eval-1 \
  --instruction-file <scratchpad>/rva-evals2/vendor-not-enabled/inputs/instructions.md \
  --diff-file <scratchpad>/rva-evals2/vendor-not-enabled/inputs/diff.patch \
  --target-paths-file <scratchpad>/rva-evals2/vendor-not-enabled/inputs/targets.txt \
  --cwd <scratchpad>/rva-evals2/vendor-not-enabled/repo \
  --dry-run
```

## JSON output (exit code 2)

```json
{"ok":false,"category":"vendor_not_allowed","detail":"pi: not enabled in the untracked local file"}
```

## What it means

- Exit 2 is a typed failure. The category is `vendor_not_allowed`, which is gate 2, "Vendor allowed".
- Per `references/typed-failures.md`, `vendor_not_allowed` is raised before anything is sent. Nothing reached pi, and this was a dry run anyway.
- The cause: `<repo>/.claude/reviewadapters-kit.local.json` holds only `{ "dev_sibling_codex_kit": true }` and has no `vendors.pi.enabled: true`. The shipped `reviewadapters-kit.settings.json` turns every vendor off, and only this untracked local file can turn one on.
- Gate 1 (codex-kit available) passed. Gates 3 to 5 (secret-named paths, size, pi CLI on PATH) were not reached, so this run says nothing about them.
- This is not a clean review. It must not be recorded as "pi found no issues".

## What the caller should do next

1. **Report it and continue.** Record "pi: vendor_not_allowed (nothing sent)". Keep the finished envelopes from the other reviewers and continue the pipeline without pi. Do not count it as a passing review or as an empty findings list.
2. **To actually use pi, the repository owner must enable it.** This is an egress decision, so the owner makes it, not the dispatcher's caller. To enable pi:
   - Add pi to the **untracked** local file `<repo>/.claude/reviewadapters-kit.local.json` and keep the existing key:
     ```json
     { "dev_sibling_codex_kit": true,
       "vendors": { "pi": { "enabled": true } } }
     ```
     Optionally pin `"model"`. Note that a pi model's first segment picks the provider that receives the data, so pinning one is an egress choice too.
   - Never commit this file. A tracked copy is refused with `vendor_not_allowed`. A CI job writes it at job time.
   - An interactive caller confirms egress with the user before the real call. That confirmation quotes the `recipient` and `reach` from the successful dry-run output.
3. **Re-run the same command with `--dry-run`** after pi is enabled. The expected result is `{ "ok": true, "dryRun": true, "vendor": "pi", "recipient", "model", "reach", "command" }`. That run also exercises the remaining gates: secret-named paths, size, and the pi CLI on PATH outside the repo.
4. **Run without `--dry-run`** only after that dry run passes and egress is confirmed (or, for an unattended caller, the allow-list is the consent). It is out of scope for this task.

I did not modify the repository or the inputs directory.
