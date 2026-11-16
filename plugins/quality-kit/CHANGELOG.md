# Changelog

All notable changes to this plugin are documented here.

## [1.0.0-alpha.4] - 2026-11-15

### Added
- `running-mutation-tests`, for measuring a module's test strength with mutmut 3.8.1: scope with a per-module
  test selection, an isolated run, the score explained, and a proposed test or `# pragma: no mutate  # reason: ...`
  for each survivor, written only after the user approves it. A mutant that no selected test ran is reported as
  not measured, never as a survivor.
- `agents/mutation-tester.md`, the plugin's first agent: copies the working tree (tracked and untracked files) to
  a scratch directory outside the repository, runs the runner and parser there, and confirms the repository is
  unchanged.
- `scripts/qlty-mutation-run.py`: checks a green baseline, writes mutmut's configuration to a temporary
  `setup.cfg` in the run tree, runs mutmut and exits with mutmut's own status; `--show` prints survivor diffs and
  `--list-modules` reads a `.github/mutation-modules.yml` list. It refuses a module or test path that resolves
  outside the run tree, such as a package symlinked in from a sibling checkout, and a run in a tree that already
  holds `mutants/`, whose old verdicts mutmut would keep. It starts pytest and mutmut as
  the `python3` in the running interpreter's own folder, and stops when that folder has none (run it from a venv).
  Those processes get an allowlisted environment, so a credential held in an environment variable does not reach
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
