# Project Setup

How to set up Codecov and the coverage tier check in a repository. Each file below is written into the target
repository only after the user approves it; Codecov's own settings are changed by the user in its UI. Token
facts are from Codecov's docs (`docs.codecov.com/docs/codecov-tokens` and `/reference/overview`), checked
2026-11-15.

## 1. Codecov and the upload token

1. The user signs in at codecov.io with the Git provider and adds the repository.
2. Upload token: the repository token (the repository's Configuration tab, General) or an organization's global
   upload token (organization settings, Global Upload Token). Stored as the CI secret `CODECOV_TOKEN`, the name
   Codecov's docs use.
3. A public repository can upload without a token in two cases: the organization's admin turned off token
   authentication for public repositories (Settings, Global Upload Token tab; existing organizations default to
   tokens required), or the upload is from a fork's branch. Keep the token anyway for the protected branches.

The token never appears in the conversation: the user pastes it into the CI secret settings directly.

## 2. The vendored tier script

CI runners do not have Claude plugins, so the tier script and its defaults are copied into the repository:

| Source (installed plugin) | Target (repository) |
|---|---|
| `scripts/qlty-coverage-tier.py` | `.github/quality-kit/qlty-coverage-tier.py` |
| `assets/qlty-coverage-tiers.yml` | `.github/quality-kit/qlty-coverage-tiers.yml` |

Both come from the plugin root (`${CLAUDE_PLUGIN_ROOT}`). The copy changes only when setup runs again; to update
it, compare the two files with the plugin's current copies and copy again on the user's approval. In this
marketplace repository the workflow reads `plugins/quality-kit/` directly instead, so nothing is vendored here.

Optional team override, tracked: `.github/coverage-tiers.yml`, any of the three keys:

```yaml
version: 1
tiers:
  green: 85
```

Keys left out keep the defaults. An unknown key, a value outside 0-100, or values not in the order
green ≥ yellow ≥ orange make the script exit 2, which fails the check rather than passing it.

## 3. The report

The tier script reads coverage.py JSON, Cobertura XML or LCOV, detected from the content. Common producers:

| Stack | Report |
|---|---|
| Python, pytest-cov | `--cov-report=json:coverage.json` or `--cov-report=xml:coverage.xml` |
| JavaScript/TypeScript, Jest or Vitest | `coverageReporters: ["lcov"]` (`coverage/lcov.info`) or `cobertura` |
| Go | `go test -coverprofile`, then `gocover-cobertura` |
| Java, JaCoCo | a Cobertura converter, since JaCoCo XML is not Cobertura |
| Rust, `cargo llvm-cov` | `--lcov --output-path lcov.info` |

List every source file, not only the loaded ones (coverage.py `source`, Jest `collectCoverageFrom`): a file the
tests never import is otherwise absent from the report, and its changed lines count as unmeasurable instead of
missed. Report paths must be relative to the repository root or absolute under it; the tier job runs from the
root. Codecov reads the same report.

## 4. The workflow

Copy the plugin's `assets/qlty-coverage-workflow.yml` to `.github/workflows/coverage.yml`, then set `REPORT` to
the report path and `REPORT_NAME` to its file name, and replace the placeholder test step (it fails on purpose
until replaced) with the repository's own test command. The template has three jobs: `coverage` runs the tests
and keeps the report as an artifact; `codecov-upload` uploads that artifact to Codecov (`continue-on-error`), in
its own job so the PR's test code never runs where `CODECOV_TOKEN` is; `coverage-tier`, on pull requests only, restores the vendored script,
the defaults and the override from the base SHA, computes the tier on `git diff HEAD^1 HEAD` (the merge commit
against its base), posts one sticky comment and fails on orange or red. Its action SHAs are the ones this
marketplace pins (checked 2026-11-15); keep them pinned by SHA.

Notes:

- The `Compute the tier` step has no token in its environment: it runs PR-controlled input (the report and the
  diff) through the script.
- Leave both jobs out of the branch protection's required checks unless the team wants orange and red to block
  the merge; quality-kit's default is a failing but not required check.
- The tier job keeps every trusted input, the report and the comment under `$RUNNER_TEMP`, outside the PR's
  checkout, and runs the script with `python -I` and `uv run --no-config`: a PR can commit any file into the
  workspace, including a module, a symlink or a fake override, but none of them is read.
- The limit: only the thresholds and the script are trusted: the PR's own code and configuration still produce the report and decide what is measurable (an `omit` entry, a `pragma: no cover`), and a change with no measurable line is green. Review a PR's coverage configuration like its code. A PR can also edit the workflow file itself, which runs from its merge commit, and drop these protections; that edit shows in its diff, and the check is not required.

## 5. `codecov.yml`

One PR comment, not two, and Codecov statuses that never block:

```yaml
coverage:
  status:
    project:
      default:
        informational: true
    patch:
      default:
        informational: true
comment: false
```

Add `ignore:` entries for generated or vendored paths the report should not count.
