# Ordering and Checks

## Expected files and blockers per ecosystem

A dependabot PR whose changed paths fall outside its ecosystem's set is suspicious (skip it, report it, and continue with the other PRs; do not rebase or merge it).

| Branch segment | Expected changed paths | Expected blockers |
|---|---|---|
| `uv` | root `pyproject.toml`, `uv.lock` | None by design: `Publish Codex policy result` passes a verified Dependabot PR without review; when it fails anyway, `codex-bypass.md` explains why and when a bypass is offered. All uv PRs share `uv.lock` |
| `npm_and_yarn` | `package.json`, `pnpm-lock.yaml` (this repository's root pnpm lockfile) | None by design: `Publish Codex policy result` passes a verified Dependabot PR without review (otherwise see `codex-bypass.md`); `Python quality` is skipped for these PRs and counts as passed only together with that verified check or the bypass attestation. A PR that also changes any other lockfile (`package-lock.json`, `yarn.lock`) is suspicious per the rule above; it would also fall outside the CI merge-privilege exemption in `docs/ci.md` and fail `Hygiene (PR contract)` |
| `github_actions` | `.github/workflows/*.yml` or `*.yaml`, `.github/actions/<name>/action.yml` or `action.yaml` | None for a pin-only bump: `Hygiene (PR contract)` passes a verified Dependabot PR whose every changed line swaps a ratchet-pinned `uses:` SHA for the commit its tag names in the action's own repository (`docs/ci.md`, the actions pin exemption), and `Publish Codex policy result` then passes it without review. `Hygiene` fails, and `Publish Codex policy result` with it, on any other change in the diff, an added or deleted file or a failed tag lookup, and also on a title, template or commit-verification failure, so read its `check-pr` reason before saying which; no Codex bypass is offered for this ecosystem, so recommend skip, and if the user wants it merged, that is manual handling outside this skill, because step 6.4 reports and skips a PR with a failing required check. A rebase onto a base that predates the exemption does not help until the exemption is on the base. Read the change for permission edits |

## Merge order

Earlier merges make every later PR behind or conflicted, so order to minimize rebases and risk:

1. Security fixes first (a vulnerability section in the PR body). A security-fix major bump goes first but still needs the breaking-change confirmation.
2. Patch and minor bumps, runtime before dev tools.
3. Major bumps, each after the user confirmed the breaking changes do not apply.
4. Related packages adjacent (a tool and its CLI wrapper, for example), so a conflict shows up immediately.
5. Ties: oldest PR first.

PRs touching only workflow files cannot conflict with lockfiles, but they still go behind their base after every other merge and need `@dependabot rebase` before `merge-pr` accepts them; two PRs editing the same workflow file can also conflict.

## Advisories, compatibility and the newest compatible version

Step 3 runs `dependabot_advisory_read.py assess` for the dependency's old, new and newest compatible version, with the base branch's lockfile for `uv` and `npm_and_yarn`, and with the PR head's lockfile to find the package versions the PR adds. A version is riskier than another when its worst advisory severity is higher, or equal with more advisories; two non-empty advisory lists are not ranked at all (the signal is `null`) when any advisory in them has no recognized severity, because an unknown severity is not the lowest one. Four rules use the result, each only on the exact signal named:

- The new version has advisories and is not less risky than the old one (`new_vulnerable_not_safer_than_old` true): recommend close, and say that a plain close may let Dependabot propose the same update again.
- The new version's own declared constraints conflict with the versions in the lock (`new_compatible` false): recommend skip (hold) and quote the violated constraints. Closing is left to the user: the constraints are declared by the package's publisher, the conflict can come from this repository's own lock as much as from the release, and Dependabot's resolution in the PR may already have bumped the conflicting dependency, so the base lock can show a conflict the PR itself resolves.
- The new version is not the newest compatible version (`new_is_newest_compatible` false) but is less risky than it (`new_safer_than_newest_compatible` true): recommend rebase and merge, naming the newest compatible version and why it is not preferred.
- The PR's head lockfile adds a package version with a known advisory (`adds_vulnerable_package` true), whatever the second and third rules say, unless the first already recommends close: recommend skip (hold), naming the package, version, advisory and fixed version. The bumped package can be clean while a dependency it pins is not (issue #741: markdownlint-cli2 0.24.0 pinned re2js 2.8.6, a high-severity advisory, and only 0.24.1 pulls a fixed re2js). Step 6.4 also reads the `Dependency review` check, required or not, and skips a PR on which it fails.

`null` or an `unknown` status means no data, never "safe" and never "compatible". Compatibility is a partial check, not a resolver: it covers PyPI `requires-python` and `requires_dist` and npm `peerDependencies` against the base lock, counts every constraint it could not parse or decide as `unevaluated`, and reports `unknown` when a dependency is locked at several versions and only some satisfy the constraint, because the lock does not say which copy the candidate would use. npm `engines` is reported separately (`engines_not_checked`) and does not make a version `unknown`; only pnpm lockfile versions 6 and 9 are read. A newer release that conflicts with the lock is not "the newest" for rule three; it is listed as information. The newest version is whatever the publisher marks as latest or lists as released, so it is upstream-controlled data, not an independent fact, and it can be ahead of what Dependabot has proposed. Risk comparisons between two versions answered by different databases are approximate (OSV can list one vulnerability under several aliases), and identical advisory sets on the old and new version count as not safer, so the first rule recommends close; a newer open PR for the same dependency is still handled below.

## Duplicates and supersession

Two open PRs for the same package: the higher target version supersedes the other. Recommend closing the older only after the newer is confirmed open and healthy, and re-check its state first, because dependabot usually closes it itself.
