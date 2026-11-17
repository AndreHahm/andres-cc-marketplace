# Dry-run dispatch of pi as a bug-reviewer (dispatch id eval-1)

(Saved by the coordinating session from the agent's returned text; the harness blocked the agent's own write.)

Fixture root, shortened below as `$F`: `<scratchpad>/rva-evals/fixtures-2/vendor-not-enabled`

## Dispatcher command run (the only one)

```bash
node <repo>/plugins/reviewadapters-kit/scripts/rva-dispatch.mjs \
  --vendor pi --reviewer-type bug-reviewer --dispatch-id eval-1 \
  --instruction-file "$F/inputs/instructions.md" \
  --diff-file "$F/inputs/diff.patch" \
  --target-paths-file "$F/inputs/targets.txt" \
  --cwd "$F/repo" --dry-run
```
It ran with the absolute paths written out in full. `--cwd` is the same path `git rev-parse --show-toplevel` printed for the repo.

## JSON output (stdout), exit code 2
```json
{"ok":false,"category":"vendor_not_allowed","detail":"pi: not enabled in the untracked local file"}
```

## What it means
- Exit 2 with `ok: false` is a typed failure, not a dry-run success. The run never got far enough to print the success shape `{"ok":true,"dryRun":true,vendor,recipient,model,reach,command}`.
- The failure comes from gate 2, the vendor allow-list. `$F/repo/.claude/reviewadapters-kit.local.json` contains only `{ "dev_sibling_codex_kit": true }`, with no `vendors.pi.enabled: true`. The shipped defaults enable no vendor.
- Nothing was sent to any vendor. Data is never sent for this category (per `references/typed-failures.md`), and `--dry-run` starts no vendor process. No vendor CLI was run directly.
- Gate 1 (codex-kit present) passed. The run never reached gates 3–5 (secret-named paths, size, pi on PATH), so it says nothing about them.

## What the caller should do next
1. Record "pi: vendor_not_allowed" for this reviewer slot and don't count it as a review or as an empty findings list. Keep the other reviewers' results and continue.
2. If pi should review in this pipeline, the repository owner enables it in the untracked local file `<repo top level>/.claude/reviewadapters-kit.local.json`, for example `{ "dev_sibling_codex_kit": true, "vendors": { "pi": { "enabled": true } } }`.
   - Pinning a pi `model` is optional, but it is an egress choice: its first segment picks the provider that receives the data.
   - Never commit this file, because the dispatcher refuses a tracked copy. In CI, write the file when the job runs.
   - An interactive caller must still confirm egress with the user for each vendor; the allow-list is only a second, mechanical gate.
   - I did not edit the file, because the task forbids changes to the fixture.
3. After enabling pi, run the same command again with `--dry-run`. Expect `ok: true, dryRun: true`, and quote its `recipient` and `reach` in the egress confirmation. That run also checks gates 3–5, so it can still fail, for example with `cli_unavailable`.
4. Run without `--dry-run` to get the findings envelope only after that dry run passes and egress is confirmed.

## Notes
- Nothing under the fixture directory was created, edited, deleted or staged. The fixture repo's `git status` shows `M calc.py`. That change was already in the fixture and is the one the diff describes (`return a + b` becomes `return a - b`); this run did not make it.
