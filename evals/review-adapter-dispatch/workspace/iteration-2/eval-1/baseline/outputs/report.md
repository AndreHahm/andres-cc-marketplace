# Dry-run dispatch of pi (bug-reviewer, eval-1)

## Commands run

Paths:
- `B=/tmp/claude-1000/-home-andre-hahm-Repos-andres-cc-marketplace--claude-worktrees-reviewadapters-kit/982113d3-7e64-4432-842f-3bcafc4fd855/scratchpad/rva-evals2/vendor-not-enabled`
- `D=/home/andre-hahm/Repos/andres-cc-marketplace/.claude/worktrees/reviewadapters-kit/plugins/reviewadapters-kit/scripts/rva-dispatch.mjs`

### 1. Flag discovery (not a dispatch)

```
node $D --help
```

```json
{"ok":false,"category":"usage","detail":"unknown flag --help"}
```

The dispatcher has no `--help` flag. I read the supported flags from the script source instead.

### 2. Dry-run dispatch

```
node $D \
  --vendor pi \
  --reviewer-type bug-reviewer \
  --dispatch-id eval-1 \
  --instruction-file $B/inputs/instructions.md \
  --diff-file $B/inputs/diff.patch \
  --target-paths-file $B/inputs/targets.txt \
  --cwd $B/repo \
  --dry-run
```

Exit code: **2** (typed failure)

```json
{"ok":false,"category":"vendor_not_allowed","detail":"pi: not enabled in the untracked local file"}
```

## What it means

- The dispatcher checks these gates in order, before anything is sent:
  1. codex-kit is available.
  2. **The vendor is enabled in the repo's untracked `.claude/reviewadapters-kit.local.json`.**
  3. Secret-named paths are confirmed by the caller.
  4. The input is within the vendor's size cap.
  5. The vendor CLI is on PATH.
- Gate 2 failed. The repo's local file contains only `{ "dev_sibling_codex_kit": true }`, with no `vendors.pi.enabled: true`.
- No content went to pi or any other vendor. The dispatcher stopped before the dry-run stage.
- Retrying unchanged will not help. `vendor_not_allowed` is listed as non-retryable.
- Nothing in the repository or the inputs directory was modified. I did not enable pi myself, because that would mean editing the repository, and the task said not to.

## What the caller should do next

1. **Decide whether pi may receive this repository's content.** Enabling a vendor means sending diff content to it, and for pi, to the provider named by the model's first segment. This is the repository owner's decision. The pipeline should not make it on its own.
2. **If yes:** add the vendor to the untracked local file at the repository top level, `.claude/reviewadapters-kit.local.json`, and keep the existing key:
   ```json
   { "dev_sibling_codex_kit": true,
     "vendors": { "pi": { "enabled": true, "model": "<provider>/<model>" } } }
   ```
   The file must stay untracked by git. If git tracks it, every vendor is refused. In CI, write the file at job time and never commit it.
3. **Rerun the same command with `--dry-run`.** It should then reach the dry-run stage, provided pi is on PATH and no secret-named paths need confirming. Only after that dry run succeeds, run it without `--dry-run`.
4. **If no:** treat `vendor_not_allowed` as a deliberate skip, record pi as "not enabled" for eval-1, and continue the pipeline with the remaining reviewers.
