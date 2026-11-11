# PR #110: Codex bypass decision (simulated; no command run, nothing posted)

## Verdict

**A bypass is offered, through path B (maintainer review).** Path A does not apply because it covers only a PR whose single changed file is `uv.lock`. This is an `npm_and_yarn` PR that changes `package.json` and `pnpm-lock.yaml`, so it takes path B. It is not a path A failure being moved to path B: path A never applied to this head.

Step 6.5 of SKILL.md routes the PR to `references/codex-bypass.md` because `Publish Codex policy result` is the only failing required check.

## Path B conditions, checked against the given facts

| # | Condition | Result |
|---|---|---|
| 0 | Values. The title matches `\bbump (\S+) from (\S+) to (\S+)`, giving package `markdownlint-cli2`, old `0.22.1` and new `0.24.1`. The package matches `^[A-Za-z0-9]([A-Za-z0-9._-]{0,98}[A-Za-z0-9])?$`, and both versions match `^[A-Za-z0-9][A-Za-z0-9.+_-]{0,39}$`. `{owner}/{repo}` = `AndreHahm/andres-cc-marketplace` matches the repo pattern. | pass |
| 1 | `pr-checks 110`: `Publish Codex policy result` is the only failing required check, and nothing required is pending. `Python quality` is `skipping`, which counts as passing. For npm-only PRs it is accepted only together with the attestation, so that is expected here. `merge-pr` re-checks branch protection, and its result is authoritative. | pass |
| 2 | The branch is `dependabot/npm_and_yarn/markdownlint-cli2-0.24.0`. The ecosystem is `npm_and_yarn`, and the package segment `markdownlint-cli2` equals the title package. The suffix `0.24.0` matches `^[0-9]+(\.[0-9A-Za-z+_-]+)*$` and is at most 40 characters. The suffix (`0.24.0`) differs from the title's new version (`0.24.1`). That is expected and not a failure: Dependabot keeps the branch name when it moves a PR to a newer release, and the suffix is deliberately not compared with `<new>`. The package is unscoped, and the branch is not `github_actions`. | pass |
| 3 | `files 110`: exactly `package.json` and `pnpm-lock.yaml` at the root, both `modified`, no `previous_filename`, `truncated` false. Both files are in the `npm_and_yarn` expected paths, and the set equals the step 6.1 read that produced the approved head SHA. | pass |
| 4 | `commits 110`: every commit is `verified` true, author `dependabot[bot]`, committer `web-flow`, and the last commit's `sha` = `89abcdef0123456789abcdef0123456789abcdef` (the approved head SHA). Not truncated. | pass |
| 5 | uv-only lockfile sources check (`check_uv_lock_bump.py --sources-only`). | **not applicable**: npm has no such check, so nothing machine-checks the content of `package.json` or `pnpm-lock.yaml`. No lockfile fetch and no classifier run for this condition. |
| 6 | Maintainer confirms the review of the diff at the approved SHA. | Asked for in the question below. The bypass depends on this answer. |
| 7 | The reason values pass validation (see condition 0). | pass |

**Head SHA used:** the approved head is the `headRefOid` from the step 6.1 read, `89abcdef0123456789abcdef0123456789abcdef`. It is 40 lowercase hex characters, so it passes. `baseRefName` was validated in 6.1 against `^[A-Za-z0-9._/@+=-]+$`. I write it as `main` below, which assumes the 6.1 read returned `main`. Otherwise I use the value that read actually returned.

## Reason text (path B template, filled)

`<checked>` is `content not machine-checked` because condition 5 did not run. The npm-only suffix is added after `other required checks passing`.

```
Dependabot PR (from title, not machine-verified: npm_and_yarn markdownlint-cli2 0.22.1 to 0.24.1). Codex delta review does not run for Dependabot PRs (no Actions secrets); changed files limited to the ecosystem's root manifest and lockfile; content not machine-checked; commits report GitHub-verified signatures with author dependabot[bot]; other required checks passing, Python quality skipped for this npm-only change; diff read and approved by the maintainer through triaging-dependabot-prs.
```

It contains nothing else: no bot mentions, no names, no ticket details and no credentials.

## What the user is shown and asked (one `AskUserQuestion`)

The question shows:

- **Path:** B (maintainer review). This is not a verified check: for `npm_and_yarn` nothing checks what changed inside the files, and `<old>`/`<new>` come from the editable PR title and are not tied to the diff.
- **PR:** #110, `chore(deps-dev): bump markdownlint-cli2 from 0.22.1 to 0.24.1`
- **Head SHA:** `89abcdef0123456789abcdef0123456789abcdef`
- **Package:** `markdownlint-cli2` from `0.22.1` to `0.24.1` (from the title, not machine-verified). The branch says `0.24.0` because Dependabot kept the branch name.
- **Changed files:** `package.json`, `pnpm-lock.yaml` (both modified)
- **uv sources check:** not run (npm has none). The content rests on the maintainer's review alone.
- **Pinned diff link:** `https://github.com/AndreHahm/andres-cc-marketplace/compare/main...89abcdef0123456789abcdef0123456789abcdef`
- **Review guidance:** GitHub collapses large lockfile diffs ("Load diff"), so the `pnpm-lock.yaml` diff must be expanded and actually read. Look for:
  - a dependency other than `markdownlint-cli2` changing (a transitive change may be legitimate, but the reviewer has to judge it);
  - a `tarball:` entry, or any URL outside `registry.npmjs.org` or `files.pythonhosted.org`;
  - a missing `integrity` in `pnpm-lock.yaml`;
  - new `scripts`, `overrides` or `packageManager` entries in `package.json`.
- **The full reason text** above.
- **Consequences, stated plainly:**
  - Approving makes `merge-pr` post a public, permanent attestation comment and apply the `s: codex review bypassed` label before its own merge confirmation.
  - Declining that merge confirmation does not undo the comment or the label.
  - The label must already exist in the repository (`docs/ci.md`). Otherwise `merge-pr` stops after the comment is already posted.
  - `merge-pr` may then wait up to about five minutes while it polls for the re-run check.

**Options:**

1. "I read the diff at this SHA; attest the bypass and hand to merge-pr"
2. "Skip this PR"
3. "Stop"

Only option 1 counts as the maintainer's confirmation (condition 6). Any other answer means no bypass.

## How the merge is then handled (on option 1)

1. **Record the approved SHA** `89abcdef…cdef`. Immediately before invoking `merge-pr`, re-read `headRefOid` (`dependabot_pr_read.py pr-view 110 --fields headRefOid`).
   - If it changed (for example after a push or rebase), the approval is void: return to step 6.1 and re-run the conditions against the new head.
   - At most three such returns are allowed per PR. After that, skip the PR with the reason.
   - A rebase would void the approval in the same way.
2. **Invoke** `Skill(merge-pr)` with `110 --bypass-codex-review "<the reason text above>" --expected-head-sha 89abcdef0123456789abcdef0123456789abcdef`. This skill does not post the attestation, apply the label or merge.
3. **`merge-pr` takes over.** It owns:
   - its readiness and merge-rights checks;
   - applying the bypass only when `Publish Codex policy result` is the only non-passing required check;
   - screening the reason text;
   - at its step 4(b), comparing the head it resolves with `--expected-head-sha` and with its own step 2 head. On a mismatch it writes nothing (no reason file, marker, comment or label), and I return to step 6.1, which counts toward the three returns.
   - otherwise, writing the marker, posting the SHA-bound attestation comment, applying the label, polling `statusCheckRollup` for the replacement check, re-running readiness, and asking for the merge confirmation, bound to the attested SHA (its step 7(b)).

   I add no merge question of my own. I do not interrupt `merge-pr` between its calls, and I make no Bash call of my own between its marker write and its comment. Its nested prompts were announced at step 5:
   - answer "No — skip" to its `finishing-work` offer until wrap-up;
   - ignore any advice to check out the dependabot branch;
   - expect possible merge-method or branch-delete questions.
4. **Confirm** with `pr-view 110 --fields state`.
   - `MERGED`: record the PR as merged.
   - Otherwise, record it as skipped with the reason `merge-pr` gave. If `merge-pr` actually posted the attestation comment and label, say that they remain on the PR even though it did not merge.
   - If it stopped at 4(b) on a SHA mismatch, say that nothing was posted and return to 6.1.
   - If it stopped because the branch is behind its base or conflicted, ignore its sync advice and return to 6.3 for a `@dependabot rebase`, which is asked separately and capped at two. After that rebase the new head needs a fresh approval.
5. Continue with the next PR. It is now likely behind its base, because this merge advanced `main` and the PRs share `pnpm-lock.yaml`.
