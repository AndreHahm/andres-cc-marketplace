# Changelog

All notable changes to this plugin are documented here.

## [Unreleased]

### Added
- `qlty-sonar-read.py rule --organization <org> --rule <key>`: one rule's name, type, impacts and description, so
  `using-sonarqube-cloud` can answer what a rule checks without an unprojected `sonar api get`.

### Changed
- The coverage tier installs PyYAML and defusedxml from `assets/qlty-coverage-tier-requirements.txt` with
  `uv pip install --require-hashes --no-build`, taken from the base SHA like the tier script. `uv run --with` and
  `--with-requirements` do not check hashes (a wrong hash installed anyway with uv 0.12.21). The weekly mutation job
  takes mutmut from a locked `mutation` dependency group. A test now runs the tier's trusted-restore step for each
  state of the base branch.
- The weekly mutation job's timeout is 15 minutes, set from its first run (each module took 0.4 to 3.1 minutes).
- `resolving-analysis-findings` keeps its Sonar rungs and decision rights in `references/sonar-mechanisms.md`, which a
  `sonar` record reads first; the text moved unchanged.

### Fixed
- Codacy ignores used the hex `issueId`, which `--ignore-issue` rejects, or, when it starts with digits, reads by
  that numeric prefix as a different issue (issue #760). The Codacy findings record (schema `2.0.0`) now carries
  the numeric `resultDataId` as `issue_id` and the hex id as `issue_key`, for matching only.
  `resolving-analysis-findings` checks a Codacy `issue_id` against `^[1-9][0-9]{0,19}$` before building a command.
- `collect_codacy.py` gave no warning when `codacy pull-request` returned fewer issues than its own
  `pullRequest.newIssues` count (100 of 150 on PR #759). The record now has `source.reported_new_issues` and
  `source.possibly_truncated`, the adapter warns on stderr, and the report says so.
- `running-mutation-tests` Step 3 now stops first when the repository changed, handles a finished run with no
  parser score, and says a module is not added to the weekly run when it stops; Step 1 states how a stem matches
  the module list. `mutation-tester` names a red baseline's failing tests.
- `mutation-tester`'s repository fingerprint used GNU-only `sha256sum`; it now uses `git hash-object`, so it runs
  the same on macOS. Mutant keys with control characters are rejected by the runner and escaped in error text.
- `qlty-sonar-read.py` read PATH twice, once to pick `sonar` and once for each child's PATH; it now reads it once.
- `collect_sonar.py` caps `--branch` at 255 characters, like `qlty-sonar-read.py`, and the skill states the same
  bounded branch and file patterns as the wrapper.
- `codacy-adapter.md`'s exit-1 row had no Output cell (issue #766); the Sonar fixtures row now names each file.
- The weekly mutation job no longer adds a redundant unlocked `pyyaml` on top of the locked environment.

## [1.0.0-alpha.4] - 2026-11-15

### Added
- `running-mutation-tests`, for measuring a module's test strength with mutmut 3.8.1: scope with a per-module
  test selection, an isolated run, the score explained, and a proposed test or `# pragma: no mutate  # reason: ...`
  for each survivor, written only after the user approves it. A mutant that no selected test ran is reported as
  not measured, never as a survivor. After a finished run of a module not yet in `.github/mutation-modules.yml`,
  it offers to append that module with the selection that ran (or to update a listed module's entry after a
  widened selection), after the user approves the exact entry.
- `agents/mutation-tester.md`, the plugin's first agent: copies the working tree (tracked and untracked files) to
  a scratch directory outside the repository, runs the runner and parser there, and confirms the repository is
  unchanged.
- `scripts/qlty-mutation-run.py`: checks a green baseline, writes mutmut's configuration to a temporary
  `setup.cfg` in the run tree, runs mutmut and exits with mutmut's own status; `--show` prints survivor diffs and
  `--list-modules` reads a `.github/mutation-modules.yml` list. It refuses a module or test path that resolves
  outside the run tree, such as a package symlinked in from a sibling checkout, and a run in a tree that already
  holds `mutants/`, whose old verdicts mutmut would keep. It starts pytest and mutmut as
  the `python3` in the running interpreter's own folder, and stops when that folder has none (run it from a venv).
  Those processes get an allowlisted environment of exact variable names (no `PYTHON*` or `LC_*` prefix, no `PYTHONPATH`), so a credential held in an environment variable does not reach
  the selected tests (files the user can read still can). The dependency install before the run is not covered:
  it keeps the full environment, so the skill recommends a build-free install command.
- `scripts/qlty-mutation-parse.py`: summarizes a run from mutmut's `.meta` files and refuses one whose counts
  disagree with `mutmut-cicd-stats.json` or that holds an exit code outside mutmut 3.8.1's table.

## [1.0.0-alpha.3] - 2026-11-15

### Added
- `using-codecov`, for ad hoc coverage and Codecov questions, a local coverage tier run, and setting up Codecov and
  the tier check in any repository (a vendored copy of the tier script, the workflow template
  `assets/qlty-coverage-workflow.yml`, `codecov.yml`).
- `scripts/qlty-coverage-tier.py`: a tier (green, yellow, orange, red) on patch coverage from a coverage.py JSON,
  Cobertura XML or LCOV report and a diff, with defaults in `assets/qlty-coverage-tiers.yml` and a per-repository
  `.github/coverage-tiers.yml` override. Needs PyYAML. Cobertura reports with a DTD are refused.
- `tests/test_quality_kit_smoke.py`: runs the three skill smoke tests under pytest, so this repository's coverage
  workflow measures quality-kit's own scripts.
- `scripts/qlty-codecov-read.py`: three fixed Codecov API v2 reads (`repo`, `totals`, `pull`) that drop author and
  title fields, refuse redirects and take an optional `CODECOV_API_TOKEN`.

### Changed
- Sonar reads go through `scripts/qlty-sonar-read.py` (plugin root), which runs fixed reads with validated
  values, fetches every page, and drops identity fields. It replaces the `sonar list issues` grant, which also
  admitted a bare run printing `author` and `assignee`, the prompting `sonar api get | jq` reads, and
  `using-sonarqube-cloud`'s direct `sonar quality-gate status` grant, which ran from the checkout.
- The wrapper finds `sonar` itself on `PATH`, skipping relative entries and folders inside the repository (`sonar.exe`
  only on Windows), and drops the CLI's server-override environment variables, after codex-kit's `gitExecutable`.
  A failing gate's verdict (CLI exit 51) is reported, not treated as a failed lookup.
- The resolver re-collects and verifies a Sonar record with the Sonar arguments, and its Verify step checks
  `snapshot_consistent` for Sonar; `S1309` skips the inline-suppression rung.

## [1.0.0-alpha.2] - 2026-11-07

### Added
- SonarQube Cloud as a second verified provider: `collect_sonar.py` writes the same findings record, with a
  `pr-status` read for the head commit and quality gate, and fails closed on partial pages.
- `using-sonarqube-cloud`, for ad hoc Sonar questions and setup. It writes nothing.
- Sonar mechanisms and decision rights in `resolving-analysis-findings`, with one provider per run.

### Changed
- The findings record is schema `1.1.0` for Sonar, with an optional `source.quality_gate` and per-finding `impacts`. Codacy records stay
  `1.0.0`.
- `collect_codacy.py` exits 1 when stdout cannot be written, and exits 2 when stdin is closed, instead of a traceback.
- The read skills pre-approve `sonar list issues`, and `using-sonarqube-cloud` also `sonar quality-gate status`.
  `sonar api` still prompts every time, and the resolver grants no `sonar` command.
- The resolver's description no longer lists adding a script as a trigger, to stay within its size limit. The
  author checklist is unchanged.
