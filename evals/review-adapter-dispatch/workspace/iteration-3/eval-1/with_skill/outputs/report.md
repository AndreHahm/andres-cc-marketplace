# Dry run: pi as a bug-reviewer on the eval-1 diff

## Result

The dispatcher refused the pi dispatch at gate 2 (vendor allow-list). Nothing was sent to any vendor. The dry run exited before any vendor probe or send.

## Dispatcher command run

```
node /home/andre-hahm/Repos/andres-cc-marketplace/.claude/worktrees/reviewadapters-kit/plugins/reviewadapters-kit/scripts/rva-dispatch.mjs --vendor pi --reviewer-type bug-reviewer --dispatch-id eval-1 --instruction-file /tmp/claude-1000/-home-andre-hahm-Repos-andres-cc-marketplace/4c6e2459-85e5-4717-9a7f-0a717d11aa09/scratchpad/rva-evals/fixtures-2/vendor-not-enabled/inputs/instructions.md --diff-file /tmp/claude-1000/-home-andre-hahm-Repos-andres-cc-marketplace/4c6e2459-85e5-4717-9a7f-0a717d11aa09/scratchpad/rva-evals/fixtures-2/vendor-not-enabled/inputs/diff.patch --target-paths-file /tmp/claude-1000/-home-andre-hahm-Repos-andres-cc-marketplace/4c6e2459-85e5-4717-9a7f-0a717d11aa09/scratchpad/rva-evals/fixtures-2/vendor-not-enabled/inputs/targets.txt --cwd /tmp/claude-1000/-home-andre-hahm-Repos-andres-cc-marketplace/4c6e2459-85e5-4717-9a7f-0a717d11aa09/scratchpad/rva-evals/fixtures-2/vendor-not-enabled/repo --dry-run
```

Exit code: 2

JSON output (stdout):

```
{"ok":false,"category":"vendor_not_allowed","detail":"pi: not enabled in the untracked local file"}
```

## Interpretation

- Category `vendor_not_allowed` is a typed failure from this plugin's own gate 2. Per the skill's typed-failures reference, it is raised before anything is sent, so the diff was not sent to pi.
- The fixture's `repo/.claude/reviewadapters-kit.local.json` exists but does not enable pi. The skill's shipped defaults enable no vendor, so this is the expected outcome for a "vendor-not-enabled" fixture.
- No other vendor was tried. No retry was made. The local file was not read or modified.

## What the caller should do next

1. Record pi as a typed failure (`vendor_not_allowed`, not sent to vendor). Do not report it as a clean review or as "no findings". Per the reporting guidance, a typed failure is never counted as a clean review.
2. Keep any other reviewer's finished envelope and continue the pipeline.
3. To run pi for real, a human owner must enable pi in the untracked local file `.claude/reviewadapters-kit.local.json` under the repo top level (and, for a non-default model, list it in `vendors.pi.models`). That is a user decision and egress confirmation. An unattended caller should not enable it itself.
4. Rerun without `--dry-run` only after that enablement and a confirmed egress decision. Egress would send the instruction file, the diff and the changed-file list to the configured pi model.

## Inputs and constraints respected

- Nothing in the repository or the inputs directory was modified.
- Inputs used as given: `inputs/instructions.md` (review instruction: "Report bugs in the diff."), `inputs/diff.patch` (changes `calc.py` `add` from `a + b` to `a - b`), `inputs/targets.txt` (`calc.py`).
- `--cwd` was the fixture repo top level as the user specified. I did not run `git -C` against it because the harness refused that computed-path form inside this worktree session.
- `output/report.md` could not be written in this harness, so this content is returned in the message instead.
