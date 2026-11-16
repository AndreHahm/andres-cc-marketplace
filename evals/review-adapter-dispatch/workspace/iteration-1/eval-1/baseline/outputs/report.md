# Dry-run dispatch of pi as bug-reviewer (dispatch id eval-1)

(Saved by the coordinating session from the agent's returned text; the harness blocked the agent's own write.)

F = /tmp/claude-1000/-home-andre-hahm-Repos-andres-cc-marketplace/4c6e2459-85e5-4717-9a7f-0a717d11aa09/scratchpad/rva-evals/fixtures-2/vendor-not-enabled

## Commands run

1. Flag probe, run without `--dry-run` (rejected at argument parsing, so nothing could be sent):

```
node /home/andre-hahm/Repos/andres-cc-marketplace/.claude/worktrees/reviewadapters-kit/plugins/reviewadapters-kit/scripts/rva-dispatch.mjs --help
```

Output:

```json
{"ok":false,"category":"usage","detail":"unknown flag --help"}
```

2. Dry-run dispatch:

```
node /home/andre-hahm/Repos/andres-cc-marketplace/.claude/worktrees/reviewadapters-kit/plugins/reviewadapters-kit/scripts/rva-dispatch.mjs --dry-run --vendor pi --cwd $F/repo --instruction-file $F/inputs/instructions.md --diff-file $F/inputs/diff.patch --target-paths-file $F/inputs/targets.txt --reviewer-type bug-reviewer --dispatch-id eval-1
```

Output (exit 2):

```json
{"ok":false,"category":"vendor_not_allowed","detail":"pi: not enabled in the untracked local file"}
```

## What it means

The dispatcher stopped at the vendor allow-list gate before contacting any vendor. The repo's untracked `.claude/reviewadapters-kit.local.json` contains only `{ "dev_sibling_codex_kit": true }`, with no `vendors.pi.enabled: true` entry. Nothing was sent to pi, no vendor CLI was run, and the repo and inputs are unchanged.

## What the caller should do next

- Treat `vendor_not_allowed` as a policy stop, not a temporary error. Do not retry, do not silently switch to another vendor, and do not run `pi` directly.
- Continue the review pipeline without pi for this round, and record that pi was skipped because it is not enabled.
- If the repo owner wants pi as a reviewer, the owner (not the agent) adds `"vendors": { "pi": { "enabled": true } }` to `<repo>/.claude/reviewadapters-kit.local.json`. That file must stay untracked.
- Once pi is enabled, rerun the same command with `--dry-run` to check the remaining gates (vendor CLI present and its version, input checks). Drop `--dry-run` only after sending the diff to pi is explicitly approved.
