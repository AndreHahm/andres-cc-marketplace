# Ordering and Checks

## Expected files and blockers per ecosystem

A dependabot PR whose changed paths fall outside its ecosystem's set is suspicious (stop and report; do not rebase or merge it).

| Branch segment | Expected changed paths | Expected blockers |
|---|---|---|
| `uv` | root `pyproject.toml`, `uv.lock` | `Publish Codex policy result` fails by design; see `codex-bypass.md`, which offers a bypass only when `uv.lock` is the sole changed file. All uv PRs share `uv.lock` |
| `npm_and_yarn` | `package.json`, `pnpm-lock.yaml` (this repository's root pnpm lockfile) | None expected. A PR that also changes any other lockfile (`package-lock.json`, `yarn.lock`) is suspicious per the rule above; it would also fall outside the CI merge-privilege exemption in `docs/ci.md` and fail `Hygiene (PR contract)` |
| `github_actions` | `.github/workflows/*` | Expected: the merge-privilege exemption covers only root manifests and lockfiles, so `Hygiene (PR contract)` is expected to fail; `.github/` is also not eligible for the automatic Codex scope bypass, and `Codex delta review` needs `Hygiene` to pass first (`docs/ci.md`), so `Publish Codex policy result` will fail too, and no Codex bypass is offered for this ecosystem. Recommend skip or manual handling unless the user says otherwise. Read the change for permission edits |

## Merge order

Earlier merges make every later PR behind or conflicted, so order to minimize rebases and risk:

1. Security fixes first (a vulnerability section in the PR body). A security-fix major bump goes first but still needs the breaking-change confirmation.
2. Patch and minor bumps, runtime before dev tools.
3. Major bumps, each after the user confirmed the breaking changes do not apply.
4. Related packages adjacent (a tool and its CLI wrapper, for example), so a conflict shows up immediately.
5. Ties: oldest PR first.

PRs touching only workflow files cannot conflict with lockfiles, but they still go behind their base after every other merge and need `@dependabot rebase` before `merge-pr` accepts them; two PRs editing the same workflow file can also conflict.

## Duplicates and supersession

Two open PRs for the same package: the higher target version supersedes the other. Recommend closing the older only after the newer is confirmed open and healthy, and re-check its state first, because dependabot usually closes it itself.
