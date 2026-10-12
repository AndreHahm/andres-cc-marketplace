## Summary
`run-codex-review` always writes per-reviewer instruction files to `<cwd>/.codex-review-instructions/`; its CLI has no option to redirect that directory, so the local parity wrapper cannot keep scratch out of the repository root.

## Environment
- **Product/Service**: `scripts/marketplace_ci` (`review.py`, `__main__.py`), `plugins/git-kit/scripts/git-codex-parity-review.py`
- **Region/Version**: main at `8ef5d419`, PR #542 (head `b52ee15c`)
- **Browser/OS**: Linux (any POSIX)

## Reproduction Steps
1. Run `uv run python .claude/scripts/git-codex-parity-review.py --output <scratchpad>/codex-parity-1.json` from the repo root.
2. Interrupt the run (Ctrl-C or kill) while reviewers are dispatching.
3. Look at the repo root.

## Expected Behavior
No scratch content lands in a shippable location (`.claude/rules/require-gitignored-scratch-locations.md`).

## Actual Behavior
`.codex-review-instructions/` remains at the repo root after an interrupted run, or on a machine where deletion at the root is denied. It is gitignored, and the wrapper removes it after a normal run, but not after an interruption.

## Error Details
~~~
review.py: instructions_dir = instructions_dir or (repo / ".codex-review-instructions")
__main__.py: run-codex-review exposes no instructions-dir option
~~~

## Visual Evidence
None.

## Impact
Low. The directory is gitignored and cleaned on a normal exit. The fix touches review-dispatch-critical files (`scripts/marketplace_ci/review.py`, `__main__.py`, listed in `trust_boundary.py`), so CI hard-refuses automated Codex dispatch on any PR that changes them. It therefore needs its own PR planned around the trust-boundary gate (see #351), and could not be done inside PR #542.

## Additional Context
Found in PR #542 (Codex connector review on head `b52ee15c`, inline comment on `plugins/git-kit/scripts/git-codex-parity-review.py` line 41, P2). Proposed fix: add an `--instructions-dir` option to `run-codex-review` (the Python function already takes `instructions_dir`) and have the wrapper pass a directory under `--output`'s scratch directory. Related: #540.
