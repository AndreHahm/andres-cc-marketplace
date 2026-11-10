# Changelog

All notable changes to this plugin are documented here.

## [Unreleased]

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
