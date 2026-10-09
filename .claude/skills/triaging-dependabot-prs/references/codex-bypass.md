# Codex Bypass for Dependency-Spec PRs

## Why it comes up

The `Codex delta review` job (`codex-review` in `.github/workflows/marketplace-ci.yml`) refuses to run when a PR changes root `pyproject.toml` or `uv.lock` among other review-dispatch-critical paths, and exits with an error. That check therefore shows as failing on a uv dependabot PR, and the required `Publish Codex policy result` fails with it. `Codex delta review` is deliberately not a required check (`docs/ci.md`), so only the required list decides. A maintainer must attest a SHA-bound bypass (`docs/ci.md`, "Manual SHA-bound bypass protocol"); re-read both files if this one looks out of date.

## This skill does not implement the attestation

`merge-pr` does. Invoked as `Skill(merge-pr)` with a PR number, `--bypass-codex-review "<reason>"` and `--expected-head-sha <approved SHA>`, it runs its merge-rights check, applies the bypass only when `Publish Codex policy result` is the only non-passing required check, screens the reason, posts the SHA-bound attestation comment (writing the `gh-pr-review` marker first, as the shared protocol's step 3(c) requires), applies the label, waits for the replacement check by polling `statusCheckRollup`, re-runs every readiness check, and asks for the merge confirmation. This skill only decides whether to pass the flag, and gets the user's approval first.

The bypass skips an automated review of a dependency lockfile change, so the conditions below are deliberately strict and fail closed: when in doubt, report the PR for manual review instead.

## When the bypass is offered

All of these, evaluated just before asking for approval (checks from step 6.4, the rest from fresh calls). The approved head SHA is the `headRefOid` from the step 6.1 read made before conditions 3 to 5.

0. **Values.** Parse `<package>`, `<old>` and `<new>` from the PR title with the case-insensitive pattern `\bbump (\S+) from (\S+) to (\S+)`; it matches `chore(deps-dev): bump ty from 0.0.71 to 0.0.84` and `Bump x from A to B in /dir`, while a group-update title does not match, which means no bypass. Validate them as described under "Reason template", and check that `{owner}/{repo}` matches `^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$` (SKILL.md step 1).
1. `Publish Codex policy result` is the only failing required check in `gh pr checks <n> --required`, and nothing required is pending. If `merge-pr`'s branch-protection check disagrees (a required check that never ran may be absent from that output), it refuses before attesting.
2. The branch is exactly `dependabot/uv/<package>-<new>`, comparing names lowercase with `_` read as `-`. This also excludes grouped-update PRs.
3. `python3 -I "${CLAUDE_PLUGIN_ROOT}/skills/triaging-dependabot-prs/scripts/dependabot_pr_read.py" files <n>` (JSON with `items`, and `truncated` true on a full page of 100, which means no bypass) returns exactly one file: `uv.lock` at the repository root, `status` `modified`, `previous_filename` absent or null; the `files` list from the step 6.1 read that produced the approved head SHA must be exactly `uv.lock` too, so the list and the SHA describe the same head. Any other file, including `pyproject.toml`, means no bypass: a manifest change needs a human reviewer.
4. The lockfile change is nothing but this package's version bump. Fetch the base branch's and the PR head's lockfile into the session scratchpad:
   - `python3 -I "${CLAUDE_PLUGIN_ROOT}/skills/triaging-dependabot-prs/scripts/dependabot_pr_read.py" uv-lock --role base --ref <baseRefName> --dir "<scratchpad>"` (writes `<scratchpad>/base-uv.lock`)
   - `python3 -I "${CLAUDE_PLUGIN_ROOT}/skills/triaging-dependabot-prs/scripts/dependabot_pr_read.py" uv-lock --role head --ref <approved-head-sha> --dir "<scratchpad>"` (writes `<scratchpad>/head-uv.lock`)

   then run `python3 -I "${CLAUDE_PLUGIN_ROOT}/skills/triaging-dependabot-prs/scripts/check_uv_lock_bump.py" --base "<scratchpad>/base-uv.lock" --head "<scratchpad>/head-uv.lock" --package <package> --old <old> --new <new>`, in exactly this shape (the pre-approved grant is a prefix match, so nothing but `-I` may sit between `python3` and the script path). The script parses both lockfiles and passes only when exactly one package entry was replaced, that entry is `<package>` going from `<old>` to `<new>` with the default registry source and unchanged dependency edges, and every file URL is a `files.pythonhosted.org` path named for `<package>` and `<new>`. Read its JSON, not just the exit code: `"ok": true` with exit code 0 is required. Any other result means no bypass, and the reasons it prints go in the report. If it exits 1 with an `expected exactly one package entry replaced` or a `top-level key ... changed` reason, the branch may simply be behind its base: when no `@dependabot rebase` has been posted for this head SHA yet, take step 6.3's rebase path (the cap applies) and run these conditions again on the new head; otherwise report the PR for manual review.
5. `python3 -I "${CLAUDE_PLUGIN_ROOT}/skills/triaging-dependabot-prs/scripts/dependabot_pr_read.py" commits <n>` (summaries with `sha`, `verified`, `author`, `committer`): every commit has `verified` true, `author` `dependabot[bot]` and `committer` `web-flow` (the committer CI's own privilege check requires), and the last commit's `sha` equals the approved head SHA. `truncated` true means no bypass.
6. The reason values pass validation.

Otherwise the failure is unexplained: report it and skip the PR. A non-uv PR failing the same check needs investigation, not an attestation.

### What these checks do and do not prove

Condition 5 uses GitHub's signature verification, which is stronger than the author-name pre-filter in step 2, but it does not prove dependabot wrote the change: `docs/ci.md` records as untested whether a collaborator with write access can create a `web-flow`-signed commit that carries a spoofed `dependabot[bot]` author. Condition 4 bounds what such a commit could do to this package's version bump and its file entries, each a `files.pythonhosted.org` path whose filename carries this package's name and the new version. It relies on PyPI's own binding of a filename to its project and does not check it, and on uv rejecting a download whose hash does not match; it cannot tell whether the version itself is the one the maintainer wants. It also allows the wheel list to shrink as long as the sdist is not dropped and, if the old entry had wheels, at least one wheel remains (real bumps change the set), so a change could drop some platforms' wheels and make uv build from source there, which fetches build dependencies that the lockfile does not pin. The maintainer's own review before approving is the backstop. Do not describe the checks as proof of authorship.

## Approval and SHA checks

Ask via `AskUserQuestion`, showing the PR number, the head SHA, the package with its old and new version, the script's summary (file entries checked), and the full reason text. Say plainly that approving posts a public, permanent attestation comment and applies a label before `merge-pr`'s own merge confirmation, and that declining that confirmation does not undo them; also that the `s: codex review bypassed` label must already exist in the repository (`docs/ci.md`), or `merge-pr` stops after the comment is posted. Options: attest the bypass and hand to merge-pr / skip this PR / stop. `merge-pr` asks for the merge separately.

1. Record the approved SHA. Re-read `headRefOid` immediately before invoking `Skill(merge-pr)`; if it differs, the approval is void: return to step 6.1. At most three returns to 6.1 per PR for a changed head; then skip it with the reason.
2. Invoke `Skill(merge-pr)` with `--expected-head-sha <approved SHA>` next to `--bypass-codex-review`. `merge-pr` resolves the head itself at its step 4(b), after its own steps 1 to 3, which include prompts to the user, and compares it with that value (and with the head its own step 2 classified against) before it writes anything. On a mismatch of either it stops without writing the reason file, the marker, the comment or the label, and reports both SHAs; return to step 6.1, where conditions 3 to 5 are re-run against the new head. This replaces any checkpoint of your own: do not try to interrupt `merge-pr` between its calls, and never add a Bash call of your own between its marker write and its comment; it would consume the marker and the comment would be denied.
3. After 4(b), `merge-pr` binds its merge to the SHA it attested (its step 7(b)), so a later push voids the attestation.

## Reason template

```
Dependency-only update by dependabot (uv: <package> <old> to <new>). Codex delta review refuses to dispatch on dependency-spec paths by design; lockfile change verified by parsing base and head to touch only this package's version and its PyPI file entries, commits report GitHub-verified signatures with author dependabot[bot], other required checks passing; approved by the maintainer through triaging-dependabot-prs.
```

Fill `<package>`, `<old>` and `<new>` from condition 0 and validate before use: package `^[A-Za-z0-9]([A-Za-z0-9._-]{0,98}[A-Za-z0-9])?$` and equal to the branch's package segment (condition 2), each version `^[A-Za-z0-9][A-Za-z0-9.+_-]{0,39}$`. If any value fails, do not offer the bypass; report the PR as suspicious. The script re-validates them. The text is posted publicly and permanently, so add nothing else: no bot-trigger mentions, ticket detail, names or credentials. `merge-pr`'s screen of these is a judgment check, not a guarantee.
