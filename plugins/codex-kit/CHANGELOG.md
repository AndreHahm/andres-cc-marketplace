# Changelog

All notable changes to this plugin are documented here.

## [Unreleased]

- Scoped `codex-review-bridge`'s and `codex-session-lookup`'s `allowed-tools` grants to match their stated read-only/no-write claims (`codex-session-lookup`'s 2 backing scripts also renamed to kebab-case); removed `codex-audit-loop`'s raw `Bash(codex:*)` grant and added rollback/failure-handling guidance to its Mode C fix-and-merge loop.
- `/codex-kit:review` and `/codex-kit:adversarial-review` now validate `$ARGUMENTS` against a whitelist (no more raw-blob interpolation) and save a report to `${CLAUDE_PLUGIN_DATA}/reviews/` on every run, success or failure.
- `/codex-kit:transfer`'s `--source` path validation switched from a denylist to an allowlist.
- Restructured the Stop hook's review-gate prompt so the previous turn's assistant message is framed as evidence in its own delimited block, never as part of the task instructions.
- Fixed a `state.mjs` concurrency race, an unbounded broker shutdown, and a client-leak bug that defeated the broker retry fallback; re-anchored `invocation-protocol.md`'s citations to symbol names, extracted shared `codex-rescue`/`codex-verify`/`codex-research` conventions into `shared-skill-conventions.md`, and added Testing & Validation sections to all 10 skills.
- `/codex-kit:setup` now confirms via `AskUserQuestion` before `--enable-review-gate`/`--disable-review-gate` toggles the persistent Stop hook, and is no longer model-invocable, matching its 6 sibling commands.
- Fixed a missing trust-boundary block in `adversarial-review`'s prompt template, incorrect fail-open/fail-closed hook wording, a missing `disable-model-invocation` on `plugin-marketplace-review`, over-broad `allowed-tools` on `review`/`adversarial-review`, several `invocation-protocol.md` citation bugs, and a 3-gap job-state-lock concurrency bug (no liveness check, TOCTOU race, no ownership check, plus a self-introduced `ReferenceError` that silently leaked every lock) caught via live stress testing.
- Closed a prompt-injection Critical: `interpolateTemplate` now neutralizes any closing-tag-shaped substring in untrusted substituted content (git diffs, session transcripts, user documents) before it reaches a Codex prompt.
- Fixed a real TOML data-corruption risk in `scripts/lib/codex-config.mjs`: reads/writes are now section-aware, so a per-profile `[table]`'s `model` key can no longer be silently misread as, or overwritten as, the root default.
- Wired up `codex-research`'s previously dead `resume`/`--persist` path; added a first-send confirmation to `/codex-kit:transfer` before it ships the full Claude session transcript to Codex; implemented real local schema validation in `codex-exec.mjs` (`schema_validation_failure` was defined but never emitted); and corrected `codex-review-bridge`'s claim of a `reviewerType` allowlist (it only ever charset-validated).
- Defined the session-level first-send confirmation gate's real scope: `codex-plan-loop` now checks it before its first Codex send; `codex-peer-review`, `codex-audit-loop`, `codex-review-bridge`, and the review/adversarial-review/transfer commands each record a named exception in their own SKILL.md instead of silently duplicating or contradicting it.
- Narrowed `Bash(node:*)` to the actual invoked script path (`Bash(node */scripts/codex-companion.mjs:*)`, plus `Bash(node -e:*)` where a skill also parses a job ID inline) across 11 components; single-sourced `MODEL_ALIASES`/`resolveModelAlias` in `scripts/lib/codex-config.mjs` (the companion script no longer keeps its own duplicate, case-sensitive copy); removed the dead `incomplete_inspection` failure category from both the taxonomy docs and `FAILURE_CATEGORIES`; de-duplicated the 5-way evaluation taxonomy and the failure-category table across their formerly independent copies; and added a persisted smoke test for `session-lifecycle-hook.mjs`'s session-start env wiring and job cleanup.

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
