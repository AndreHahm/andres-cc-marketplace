# Ordering and Checks

## Expected files and blockers per ecosystem

A dependabot PR whose changed paths fall outside its ecosystem's set is suspicious (skip it, report it, and continue with the other PRs; do not rebase or merge it).

| Branch segment | Expected changed paths | Expected blockers |
|---|---|---|
| `uv` | root `pyproject.toml`, `uv.lock` | `Publish Codex policy result` fails by design; see `codex-bypass.md`, which offers a bypass only when `uv.lock` is the sole changed file. All uv PRs share `uv.lock` |
| `npm_and_yarn` | `package.json`, `pnpm-lock.yaml` (this repository's root pnpm lockfile) | None expected. A PR that also changes any other lockfile (`package-lock.json`, `yarn.lock`) is suspicious per the rule above; it would also fall outside the CI merge-privilege exemption in `docs/ci.md` and fail `Hygiene (PR contract)` |
| `github_actions` | `.github/workflows/*` | Expected: the merge-privilege exemption covers only root manifests and lockfiles, so `Hygiene (PR contract)` is expected to fail; `.github/` is also not eligible for the automatic Codex scope bypass, and `Codex delta review` needs `Hygiene` to pass first (`docs/ci.md`), so `Publish Codex policy result` will fail too, and no Codex bypass is offered for this ecosystem. Recommend skip; if the user wants it merged, that is manual handling outside this skill, because step 6.4 reports and skips a PR with a failing required check. Read the change for permission edits |

## Merge order

Earlier merges make every later PR behind or conflicted, so order to minimize rebases and risk:

1. Security fixes first (a vulnerability section in the PR body). A security-fix major bump goes first but still needs the breaking-change confirmation.
2. Patch and minor bumps, runtime before dev tools.
3. Major bumps, each after the user confirmed the breaking changes do not apply.
4. Related packages adjacent (a tool and its CLI wrapper, for example), so a conflict shows up immediately.
5. Ties: oldest PR first.

PRs touching only workflow files cannot conflict with lockfiles, but they still go behind their base after every other merge and need `@dependabot rebase` before `merge-pr` accepts them; two PRs editing the same workflow file can also conflict.

## Advisories and the newest version

Step 3 runs `dependabot_advisory_read.py assess` for the dependency's old, new and newest version. A version is riskier than another when its worst advisory severity is higher, or equal with more advisories. Two rules use the result, each only on an exact `true` signal:

- The new version has advisories and is not less risky than the old one (`new_vulnerable_not_safer_than_old`): recommend close, and say that a plain close may let Dependabot propose the same update again.
- The new version is not the newest (`new_is_latest` false) but is less risky than the newest (`new_safer_than_latest`): recommend rebase and merge, naming the newest version and why it is not preferred.

`null` or an `unknown` status means no data, never "safe". The newest version is whatever the publisher marks as latest (PyPI's current release, npm's `latest` dist-tag, a repository's latest GitHub release), so it is upstream-controlled data, not an independent fact, and it can be ahead of what Dependabot has proposed. Risk comparisons between two versions answered by different databases are approximate (OSV can list one vulnerability under several aliases), and identical advisory sets on the old and new version count as not safer, so the rule recommends close; a newer open PR for the same dependency is still handled below.

## Duplicates and supersession

Two open PRs for the same package: the higher target version supersedes the other. Recommend closing the older only after the newer is confirmed open and healthy, and re-check its state first, because dependabot usually closes it itself.
