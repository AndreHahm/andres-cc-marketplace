# Changelog

All notable changes to this plugin are documented here.

## [Unreleased]

### Changed
- `resolving-analysis-findings` classifies a name a framework requires as `AcceptedUse` on Sonar findings, so
  its rung 3 fallback is `accept`.
- Both adapters exit 1 when stdout closes before the output is read, and exit 2 when stdin is closed, instead
  of a traceback.
- `collect_sonar.py` accepts only JSON whitespace between pages.
- `using-sonarqube-cloud` checks a PR number before it reaches a command line.

## [1.0.0-alpha.2] - 2026-11-07

### Added
- SonarQube Cloud as a second verified provider: `collect_sonar.py` writes the same findings record, with a
  `pr-status` read for the head commit and quality gate, and fails closed on partial pages.
- `using-sonarqube-cloud`, for ad hoc Sonar questions and setup. It writes nothing.
- Sonar mechanisms and decision rights in `resolving-analysis-findings`, with one provider per run.

### Changed
- The findings record is schema `1.1.0` for Sonar, with an optional `source.quality_gate` and per-finding `impacts`. Codacy records stay
  `1.0.0`.
- The resolver's description no longer lists adding a script as a trigger, to stay within its size limit. The
  author checklist is unchanged.
