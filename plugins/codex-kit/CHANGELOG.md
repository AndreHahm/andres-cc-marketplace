# Changelog

All notable changes to this plugin are documented here.

## [Unreleased]

- None yet.

## [1.0.0-alpha.1] - 2026-08-08

### Added

- Initial release: 20 components (7 commands, 10 skills, 3 hooks) for delegating work to OpenAI's Codex CLI from Claude Code with independent verification.
- Bundled Codex engine (broker process, job/session tracking), forked from OpenAI's official `codex` plugin under Apache-2.0 — see [NOTICE](./NOTICE).
- Native and adversarial code review (`/codex-kit:review`, `/codex-kit:adversarial-review`) with an always-on independent double-check layer (Agreed/Disagreed/Nuanced/False Positive/Uncited classification).
- Task delegation with diff double-check (`codex-rescue`), document/plan verification (`codex-verify`), and cross-model research (`codex-research`).
- Job and session management (`/codex-kit:status`, `/codex-kit:result`, `/codex-kit:cancel`, `/codex-kit:transfer`).
- Optional stop-time review gate (`/codex-kit:setup --enable-review-gate`).
- A generic, reviewer-agnostic bridge (`codex-review-bridge`) and a thin CI orchestration skill for this repository's own marketplace PR pipeline (`plugin-marketplace-review`).
- Sandbox-mode viability check in `/codex-kit:setup`, with explicit (never silent) fallback reporting if `danger-full-access` is required.
