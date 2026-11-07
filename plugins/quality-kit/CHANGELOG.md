# Changelog

All notable changes to this plugin are documented here.

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
