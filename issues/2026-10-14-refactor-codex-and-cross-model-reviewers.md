## Summary
Refactor the reviewers behind CI `Codex delta review`, the local parity review and `cross-model-review`: they are three separately configured paths with unstable, partly out-of-scope results, so a PR cannot converge on a clean state.

## Environment
- **Product/Service**: marketplace-ci `run-codex-review` (CI job `Codex delta review`, `Publish Codex policy result`), `create-pr` step 4.5 (`git-codex-parity-review.py`), git-kit `cross-model-review`
- **Region/Version**: observed on PR #565 (2026-10-14); local Codex CLI 0.162.1 against CI's pin 0.147.0; Windows host for the local runs

## Reproduction Steps
1. Open a PR that changes a skill, its references and a mirrored copy (PR #565 is an example).
2. Push several fix commits and read the findings of each `Codex delta review` run.
3. Run the local parity review twice on the same head.
4. Run `cross-model-review` on a diff of about 200 KB.

## Expected Behavior
- The same head gives the same blocking findings on every run, and the local parity review predicts CI's result.
- Only findings on lines the PR changed can block (see #525).
- Mechanical rules are checked by scripts, not by a model, and a reviewer that could not run is reported as such, not as a clean pass or a finding.
- One definition of each reviewer (prompt, rubric, scope) is shared by all three paths.

## Actual Behavior
- **Unstable CI findings.** Successive runs on PR #565 returned a different set each time (3, 8, 5, 4 and 3 findings across five heads), and a blocking finding raised on one head was absent on the next without a related change.
- **Pre-existing text blocks.** Blocking findings cited text that already exists on `main` (a relative path to a plugin-root file used by many skills, a description phrased with "Use when", an unscoped `git ls-files` grant), marked `in_diff: true` because the file was touched.
- **Rubric conflicts with repo rules.** One finding asked for the opposite of `resolve-plugin-root-to-claude-mirror.md` (mirror files must stay byte-identical), and size and code-block thresholds (R13, R18) were reported at the weak-warning tier as non-blocking noise on every run.
- **Local parity review fails open to blocked.** Reviewers returned `helper_unknown_error: setup refresh had errors` and no file contents; a different pair failed in each of two runs, so no run was complete (`plugin-validator` failed in both). The result file said `blocking: true` with zero findings, which neither means "findings" nor "clean".
- **Different reviewer sets.** CI and the parity wrapper run `plugin-rulebook-checker`, `dependency-reviewer`, `security-reviewer` and `skill-reviewer` (plus `plugin-validator` in the observed output); `cross-model-review` uses a fresh-eyes and a challenger persona with separate prompts, and the local Codex version differs from CI's pin.
- **Timeouts.** A `cross-model-review` Codex pass over a 27-file, about 200 KB diff hit the 240 s limit; a retry on 10 files, about 86 KB, finished once and timed out on the next run.

## Error Details
~~~
run-codex-review: reviewer dispatch failed for: ['plugin-validator', 'security-reviewer']
  ... helper_unknown_error: setup refresh had errors
codex exec exceeded 240000ms
~~~

## Impact
**Medium** - A manual route exists (retry, fix the real items, or a SHA-bound bypass), but every PR that touches a skill burns several push-and-wait rounds, and a bypass is the only way out when a finding conflicts with a repo rule.

## Additional Context
Proposed scope for the refactor, to be split into sub-issues:
1. One source of truth for the reviewer roster, prompts and rubric, consumed by CI, the parity wrapper and `cross-model-review`.
2. Move the mechanical rules (grant-to-body consistency, size and block-length thresholds, relative-path and mirror checks) into deterministic scripts; keep model reviewers for judgment only.
3. Scope blocking to changed lines and cap what a pre-existing finding can do (extends #525).
4. Distinguish "reviewer could not run" from "no findings" from "findings" in the result file, exit code and PR comment, and retry per reviewer.
5. Reduce run-to-run variance (fixed model and pin, stable ordering, one pass per reviewer) and add a convergence check (relates to the closed #527).
6. Chunk large diffs for `cross-model-review` and the parity wrapper instead of one long Codex call.

Related: #525 (blocking on pre-existing findings), #541 (cross-model-review scope and extra models), #351 (trust-boundary gate redesign), #471 (timeout variable has no effect), closed #527 and #544.
