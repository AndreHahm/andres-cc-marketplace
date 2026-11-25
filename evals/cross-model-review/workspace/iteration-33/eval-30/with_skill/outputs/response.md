Nothing was run or dispatched. This describes what the skill prescribes.

## (1) Commands

Locator, after the Preflight chain, as its own Bash call (`PATH_FILTERED=1`, so it begins with its own `export PATH` statement, never a prefix assignment). It is offered only if `PLANNER_TOUCHED` is not 1:

```bash
export PATH='/usr/local/bin:/usr/bin:/bin'
python3 -I "/opt/plugins/git-kit/scripts/git-review-locate-rva.py" --repo "/home/u/app"
```

Check the result (exit 0; both paths absolute, outside /home/u/app, only `[A-Za-z0-9._/-]`; dispatcher ends in `/scripts/rva-dispatch.mjs`). Then pi's dry run for batch 1:

```bash
export PATH='/usr/local/bin:/usr/bin:/bin'
/usr/bin/env -u NODE_OPTIONS -u NODE_PATH -u NODE_COMPILE_CACHE -u NODE_EXTRA_CA_CERTS -u NODE_TLS_REJECT_UNAUTHORIZED -u NODE_V8_COVERAGE -u NODE_REDIRECT_WARNINGS -u NODE_ICU_DATA "/usr/bin/node" "/opt/plugins/reviewadapters-kit/1.0.0/scripts/rva-dispatch.mjs" --vendor pi --reviewer-type fresh-eyes-reviewer --dispatch-id cross-model-review-$(date +%s)-dry-pi-1 --instruction-file "/tmp/tmp.abc/rva_review.1.md" --diff-file "/tmp/tmp.abc/rva_diff.1.diff" --target-paths-file "/tmp/tmp.abc/rva_paths.1.txt" --cwd "/home/u/app" --dry-run
```

The `export PATH` and the `env` call are not in `allowed-tools`, so they prompt; approve each call once and add no allow rule. (After `EnterWorktree`, if the statement form is refused: one simple command with a `PATH=` prefix, and a literal epoch instead of `$(date +%s)`.) A dry run sends nothing.

## (2) What reaches pi

Only `app.py`, through:
- `rva_diff.1.diff`: the batch's `.codex.diff` files (eligible files only, never a `.diff` file).
- `rva_paths.1.txt`: one line, `app.py`.

The third Phase 1 file, `rva_review.1.md`, is instructions: the no-tools line plus the `$BASE`-verified `review.md`. Phase 2 uses `rva_challenger.pi.1.md` in its place. There is no `<untracked_files>` block (eligible untracked files are already in the diff) and pi is told it has no tools. `deploy-credentials.txt` reaches pi nowhere: not in the diff, target paths, untracked entries or a quoted finding. It stays in Claude's native review.

## (3) Egress question: the two disclosures

In pi's own `AskUserQuestion` (separate from Codex's First-Send Confirmation):
- `deploy-credentials.txt` is named, as a `sensitive_paths` entry, as **not sent**, separately from the target paths.
- `INDEX_COPY_FAILED=1`: the index copy failed, so the diff may be incomplete.

## (4) pi's challenger file

| Finding | In the file? | How / why |
|---|---|---|
| F1 | No | Evidence quotes a value from `deploy-credentials.txt` (sensitive, not eligible). |
| F2 | Yes | Located in a target path and does not repeat the issue text. The leading `[tracked #12]` is removed in the embedded copy only; `claude_fresh_eyes.json` keeps it for `match`. |
| M1 | No | Names a sensitive file. The rule applies whoever raised the finding, Codex included. |
| M2 | No | Quotes `.env`, a sensitive name; changed or not makes no difference, and neither does being ignored. |

This assumes F2's `components` also stay inside the target paths. `<other_reviewer_findings>` holds only F2, in a group labeled Claude, with closing tags neutralized, followed by the restated data-only boundary. Codex has no remaining finding for this batch. F1, M1 and M2 stay in the report under the model that raised them, Medium by this rule (unless another model raised the same issue, or it was refuted, under the section 5 tiers).

## (5) Accepted-findings file

Neither. pi gets neither `accepted.md` nor `accepted.codex.md`, in Phase 1 or Phase 2. (Claude gets the first, Codex only the second.)

## (6) Re-running the locator

Run it again immediately before pi's first real dispatch, and again before its first Phase 2 dispatch, with the same command as in (1). `/usr/local/bin/node` differs from the `/usr/bin/node` the egress question was asked against, so every optional vendor still to dispatch is dropped (here pi), with the reason recorded in `inspection_limits`. Nothing is dispatched on the old or the new result. If it happens before Phase 2, pi's returned Phase 1 envelopes are kept. Claude and Codex go on.

## (7) Inherited `NODE_OPTIONS`

Every dry run and every real dispatch begins with the `/usr/bin/env -u NODE_OPTIONS -u NODE_PATH ...` prefix (absolute path, after the `export PATH` statement), which removes it and the other listed `NODE_*` variables before node starts, so it cannot preload code with the vendor login. Other loader variables (`OPENSSL_CONF`, `LD_PRELOAD`) are still inherited, a stated residual risk.

## (8) What is sent besides the diff

The question says the full diff text of the target files leaves the machine, and that **Phase 2 also sends the other reviewers' findings, which may quote code outside the diff**. It also quotes pi's `recipient`, `model` and `reach`, names the target paths (`app.py`) and states the dispatch count (two per batch with eligible paths). Besides the disclosures in (3), it repeats the conditional ones when set (`DISPATCHER_TOUCHED`, `REVIEW_UNVERIFIED`/`REFUTE_UNVERIFIED`) and, for a batch flagged `secret_paths_unconfirmed`, every path of that batch with the dispatcher's count. Options: "Send to pi for this run" / "Skip pi".
