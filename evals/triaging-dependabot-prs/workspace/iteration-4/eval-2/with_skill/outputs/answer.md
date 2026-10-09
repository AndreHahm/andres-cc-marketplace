# PR #102 (ty 0.0.71 to 0.0.84): what I do next

Simulated only. I run no command and post nothing. This describes what I would do, following SKILL.md step 6.5 and `references/codex-bypass.md`.

## 1. Decide whether a bypass is offered (no GitHub write yet)

`Publish Codex policy result` is the only failing required check, so step 6.5 sends me to `references/codex-bypass.md`. I go through its conditions one by one:

- **Condition 0 (values).** The title matches `\bbump (\S+) from (\S+) to (\S+)`, giving package `ty`, old `0.0.71`, new `0.0.84`. All three pass the reason-template regexes. `{owner}/{repo}` comes from the PR `url` read at step 1 and must match `^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$`.
- **Condition 1.** `Publish Codex policy result` is the only failing required check and nothing required is pending. `Codex delta review` also fails but is not required, so it is ignored.
- **Condition 2.** The branch `dependabot/uv/ty-0.0.84` equals `dependabot/uv/<package>-<new>`, which is a pass.
- **Condition 3.** The files API shows exactly one file, `uv.lock`, with status `modified`. I also confirm that `previous_filename` is absent or null. The `files` list from the step 6.1 read that produced the approved head SHA must also be exactly `uv.lock`.
- **Condition 4.** `check_uv_lock_bump.py` printed `"ok": true` with exit code 0. I read the JSON and the exit code, not just the exit code. The lockfile is a single-package bump, so the branch is not stale and I take no rebase path.
- **Condition 5.** Every commit is verified, the author is `dependabot[bot]`, the committer is `web-flow`, and the last commit's sha equals the head SHA `0123456789abcdef0123456789abcdef01234567`. There is one file and a short commit list, so nothing is truncated at 100 entries.
- **Condition 6.** The reason values pass validation.

All conditions hold, so the bypass is offered. The approved head SHA is the `headRefOid` from the step 6.1 read: `0123456789abcdef0123456789abcdef01234567`.

## 2. What the user is shown and told

I ask via `AskUserQuestion`. This is the separate, bypass-specific ask. The plan approval from step 5 does not cover it. The question shows:

- PR #102, head SHA `0123456789abcdef0123456789abcdef01234567`, package `ty`, `0.0.71` to `0.0.84`.
- The script's summary: the file entries checked, a single-package bump with the default registry, and file URLs on `files.pythonhosted.org`.
- The full reason text, filled from the template:
  > Dependency-only update by dependabot (uv: ty 0.0.71 to 0.0.84). Codex delta review refuses to dispatch on dependency-spec paths by design; lockfile change verified by parsing base and head to touch only this package's version and its PyPI file entries, commits report GitHub-verified signatures with author dependabot[bot], other required checks passing; approved by the maintainer through triaging-dependabot-prs.

I say plainly that:

- Approving posts a public, permanent attestation comment and applies a label. This happens before `merge-pr`'s own merge confirmation, and declining that confirmation does not undo the comment or label.
- The `s: codex review bypassed` label must already exist in the repository. If it does not, `merge-pr` stops after the comment is already posted.
- These checks do not prove dependabot wrote the change. GitHub's signature verification is stronger than the author-name check, but `docs/ci.md` records as untested whether a collaborator can forge a `web-flow`-signed commit with a spoofed `dependabot[bot]` author. The maintainer's own review is the backstop.
- The classifier relies on PyPI's own filename-to-project binding and does not verify it. It also cannot tell whether version `0.0.84` is the one the maintainer wants.
- The bypass skips an automated review of a lockfile change.

Options: attest the bypass and hand to merge-pr / skip this PR / stop.

I also tell the user (from step 5's up-front disclosure) about `merge-pr`'s nested prompts: the merge confirmation, a wait of up to about five minutes while it polls for the re-run check, the `finishing-work` offer after the merge (answer "No - skip" until the end), and the open-issues checkout advice (ignore it).

## 3. If the user approves: how the merge is handled

1. I record the approved SHA, `0123456789abcdef0123456789abcdef01234567`.
2. Immediately before invoking, I re-read `headRefOid` with `gh pr view 102`. If it differs from the approved SHA, the approval is void and I return to step 6.1 (at most three returns per PR for a changed head, then skip with the reason). If it matches, I continue.
3. I invoke `Skill(merge-pr)` with PR number 102, `--bypass-codex-review "<the reason above>"` and `--expected-head-sha 0123456789abcdef0123456789abcdef01234567`.
4. `merge-pr` owns everything from here. This skill does not post the attestation, apply the label, or write the marker.
   - It runs its merge-rights check.
   - It applies the bypass only because `Publish Codex policy result` is the only non-passing required check.
   - At its step 4(b) it resolves the head itself and compares it with `--expected-head-sha`. On a mismatch it stops before writing anything, and I return to 6.1 and re-run conditions 3 to 5 on the new head.
   - It screens the reason, writes the `gh-pr-review` marker, posts the SHA-bound attestation comment, and applies the label.
   - It polls `statusCheckRollup` for the replacement check, re-runs the readiness checks, and asks for the merge confirmation.
   - It binds the merge to the attested SHA (its step 7(b)).
5. I add **no merge question of my own** and run no Bash call of my own between `merge-pr`'s marker write and its comment. That call would consume the marker and the comment would be denied. I never run `gh pr merge`, edit the PR, change labels, or push myself.
6. **Confirm (6.7).** I run `gh pr view 102 --json state`; it must say `MERGED`.
   - If it does not, I record the PR as skipped with the reason `merge-pr` stated (declined confirmation, missing label, failing required check, and so on).
   - After a bypass, I say that the public attestation comment and label remain on the PR even though it was not merged, but only if `merge-pr` actually posted them.
   - If `merge-pr` stopped at step 4(b) on a SHA mismatch, nothing was posted. I say so and return to 6.1.
   - If it stopped because the branch is behind or conflicted, I ignore its `git-sync-branch` advice and return to 6.3 for a rebase.

I then continue with the next PR. The remaining PRs are now behind or conflicted because the base advanced. At wrap-up I report merged, closed and skipped PRs, and offer `Skill(finishing-work)` once, passing #102 (the last merged PR number) if it merged.

## 4. If the user declines

If the user picks "skip this PR", I record #102 as skipped and make no GitHub write. If they pick "stop", I go to wrap-up.
