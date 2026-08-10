# Changelog

All notable changes to this plugin are documented here.

## [Unreleased]

- Scoped `codex-review-bridge`'s and `codex-session-lookup`'s `allowed-tools` grants to match their stated read-only/no-write claims (`codex-session-lookup`'s 2 backing scripts also renamed to kebab-case); removed `codex-audit-loop`'s raw `Bash(codex:*)` grant and added rollback/failure-handling guidance to its Mode C fix-and-merge loop.
- `/codex-kit:review` and `/codex-kit:adversarial-review` now validate `$ARGUMENTS` against a whitelist (no more raw-blob interpolation) and save a report to `${CLAUDE_PLUGIN_DATA}/reviews/` on every run, success or failure.
- `/codex-kit:transfer`'s `--source` path validation switched from a denylist to an allowlist.
- Restructured the Stop hook's review-gate prompt so the previous turn's assistant message is framed as evidence in its own delimited block, never as part of the task instructions.

## [1.0.0-alpha.1] - 2026-08-08

### Added

- Initial release: 20 components (7 commands, 10 skills, 3 hooks) for delegating work to OpenAI's Codex CLI from Claude Code with independent verification.
- Bundled Codex engine (broker process, job/session tracking), forked from OpenAI's official `codex` plugin under Apache-2.0 — see [NOTICE](./NOTICE).
- Native and adversarial code review (`/codex-kit:review`, `/codex-kit:adversarial-review`) with an always-on independent double-check layer (Agreed/Disagreed/Nuanced/False Positive/Uncited classification).
- Task delegation with diff double-check (`codex-rescue`), document/plan verification (`codex-verify`), and cross-model research (`codex-research`).
- Job and session management (`/codex-kit:status`, `/codex-kit:result`, `/codex-kit:cancel`, `/codex-kit:transfer`).
- Optional stop-time review gate (`/codex-kit:setup --enable-review-gate`).
- A generic, reviewer-agnostic bridge (`codex-review-bridge`) and a thin CI orchestration skill for this repository's own marketplace PR pipeline (`plugin-marketplace-review`, **not yet operational** — its required `ReviewScope` input doesn't exist in this repository yet).
- Sandbox-mode viability check in `/codex-kit:setup`, with explicit (never silent) fallback reporting if `danger-full-access` is required.
- Dual-AI plan-validate-implement-review loop (`codex-plan-loop`), lightweight design/analysis peer review (`codex-peer-review`), whole-project multi-lens audit with an optional independently-verified fix loop (`codex-audit-loop`), Codex CLI session lookup/inspection (`codex-session-lookup`), and the shared internal reference hub for this plugin's own prompt-assembly and invocation conventions (`codex-prompt-protocol`, not user-invocable).
