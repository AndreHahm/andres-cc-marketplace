# Changelog

All notable changes to this plugin are documented here.

## [Unreleased]

- Added `codex-exec-live-roundtrip.mjs`, a new persisted smoke test that calls `runCodexExec` against the real, authenticated `codex` binary and asserts a schema-conformant response — every prior smoke test proved codex-kit's own scaffolding without ever completing a live `codex exec` round-trip (`running-a-full-retrospective:M7`). SKIPs cleanly via `runCodexExec`'s own `CLI_UNAVAILABLE`/`AUTH_UNAVAILABLE` categories in an environment with no live, logged-in `codex` CLI.
- Added `codex-windows-guardrails`, a new skill providing best-effort guardrails (pre-flight
  repository-boundary/secret-file/instruction-containment checks plus an instructed, not enforced,
  dangerous-command allowlist) so a caller (`plugin-auditor`'s optional Codex backend) can attempt
  `danger-full-access` locally on Windows, where no working sandbox exists. Disabled by default.
  Bypasses `codex-review-bridge`'s own CLI entirely (which unconditionally, correctly refuses that
  execution profile for every other caller) by importing its exported reusable pieces
  (`ENVELOPE_SCHEMA`, `semanticallyValidate`, `isValidToken`, `neutralizeClosingTags`) directly instead —
  additive exports on `bridge-invoke.mjs`, no behavior change for any existing caller.
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
- Narrowed `Bash(node:*)` to the actual invoked script path (`Bash(node */scripts/codex-companion.mjs:*)`) across 11 components; single-sourced `MODEL_ALIASES`/`resolveModelAlias` in `scripts/lib/codex-config.mjs` (the companion script no longer keeps its own duplicate, case-sensitive copy); removed the dead `incomplete_inspection` failure category from both the taxonomy docs and `FAILURE_CATEGORIES`; de-duplicated the 5-way evaluation taxonomy and the failure-category table across their formerly independent copies; and added a persisted smoke test for `session-lifecycle-hook.mjs`'s session-start env wiring and job cleanup.
- Structurally graded all 10 `evals/<skill>/evals.json` suites against each skill's current documented behavior (verdict recorded in each skill's own "Testing & Validation" section), which surfaced and corrected 2 stale eval expectations (`codex-audit-loop`'s cost figure, `codex-review-bridge`'s now-incorrect allowlist claim); declared this plugin's preferred scripting language in `CONTRIBUTING.md` and updated its eval-status description to match.
- Closed a second prompt-injection Critical: `codex-verify`'s blind document-append never received the closing-tag defense `codex-research` already had — both now neutralize untrusted content the same way, documented once in a new shared convention (`shared-skill-conventions.md` §4) rather than three independently-written defenses.
- Removed `Bash(node -e:*)` (an arbitrary-code grant, not a scoped one) from `codex-rescue`/`codex-verify`/`codex-research` by adding a `--print-job-id` mode to the companion's `task` command; narrowed `codex-audit-loop`'s `Bash(git:*)` to 6 specific subcommands, `/codex-kit:setup`'s `Bash(npm:*)` to the literal install command, and `plugin-marketplace-review`'s previously un-narrowed `Bash(node:*)` down to nothing (it has no execution grant to narrow yet); wrapped the Stop hook's relayed Codex text as length-capped, quoted evidence instead of an unbounded directive-channel string; and added redaction/truncation notes to `/codex-kit:transfer` and all 5 review-report save paths.
- Fixed a real reliability gap in backgrounded `/codex-kit:review`: it previously told the user to check `/codex-kit:status` instead of polling, silently skipping the "always on" double-check this plugin's own description promises — it now polls via `BashOutput` and completes Phase 4 in the same turn, and `codex-audit-loop`/the review commands gained the `BashOutput`/`KillShell` grants that polling actually needs.
- Closed the last unresolved first-send-gate gap (the Stop review-gate hook now records its own named exception) and 2 real activation-trigger overlaps (`codex-plan-loop`↔`codex-peer-review`, `codex-rescue`↔`codex-audit-loop`) with mutual-exclusion text in each pair's description.
- Raised the `SessionEnd` hook's timeout from 5s to 12s (its own internal cleanup budget could already exceed 5s, risking a mid-cleanup kill); added a fast-fail timeout to the Stop hook's Codex-availability probe; and switched `state.json`/`broker.json`/job-file writes to atomic temp-file-then-rename.
- Added a `## Known Limitations` section to `README.md` and a clarifying note to `codex-review-bridge/references/envelope-schema.md` for 2 previously-undocumented gaps (`executionProfile` not threaded into the returned envelope, 6 semantic-validation checks defined but not yet enforced).
- Corrected `README.md`/`plugin.json`/`marketplace.json`'s stale "not yet operational" claim about `plugin-marketplace-review` (its `ReviewScope` input now exists; the skill is documentation-only by design, never CI-executed — see `[1.0.0-alpha.1]`'s original claim below, now superseded); removed the destructive `Bash(rm -f */tmp/*:*)` grant from `codex-rescue`/`codex-verify`/`codex-research` (illusory path scoping — `${CLAUDE_PLUGIN_DATA}` can't be expanded inside `allowed-tools`); narrowed all 13 `Bash(node */scripts/codex-companion.mjs:*)` grants to the plugin-qualified path; added rollback instructions to `codex-rescue`'s Phase 5; closed a stale prompt-injection vector surviving in `invocation-protocol.md` §8 (raw `cat` append, superseded by the `sed` neutralization pattern elsewhere); finished the `--json`→`--print-job-id` job-ID-capture conversion across the remaining `invocation-protocol.md` sites that still described the superseded form; and narrowed `codex-audit-loop`'s `Bash(git push:*)` to `Bash(git push origin:*)` plus an exact non-force command form, matching its own no-force-push policy.
- Fixed all 3 Critical findings from the Phase 5 audit — a prompt-injection gap in the
  unsandboxed `codex-windows-guardrails` dispatch path, and the Stop hook failing open
  (instead of closed) on an uncaught exception — plus 3 Major runtime-breaking
  permission-scope bugs (`codex-rescue`'s missing rollback grants, `codex-plan-loop`'s
  missing Pattern B grants, a reverted over-removal on `codex-audit-loop`).
- Closed the remaining security-relevant Major findings from the Phase 5 audit: a TOML
  key-injection risk in `--persist-model`/`--persist-effort`, untracked secret files
  reaching Codex via `/codex-kit:review` (closed by extracting a shared
  `scripts/lib/secret-filenames.mjs` module), a non-constant-time broker-token comparison
  (now timing-safe), and several file/dir permission and redaction gaps; plus a
  doc-accuracy sweep (stale export counts, eval coverage math, charset claims, test counts).
- Added the missing bidirectional activation exclusion between `codex-research` and
  `codex-peer-review`; fixed a falsy-0 timeout bug (`--timeout-ms 0` was silently
  discarded); added a missing branch-restore step to `codex-audit-loop`'s Mode B;
  corrected a dangling reference to a nonexistent `WINDOWS_GUARDRAILS.md` planning
  document; and documented `guarded-dispatch.mjs`'s own pre-flight error-category
  vocabulary.
- `codex-audit-loop` and `codex-peer-review` each gained a real live `skill-tester`
  baseline-comparison run (both clearly beat baseline), upgrading this plugin's
  live-eval-coverage count from 2 to 4 of its 11 skills.
- Added a `dryRun` option to the shared `runCodexExec` primitive (`scripts/lib/codex-exec.mjs`),
  exposed as `--dry-run true` on both of its current callers (`codex-review-bridge`'s
  `bridge-invoke.mjs`, `codex-windows-guardrails`' `guarded-dispatch.mjs`). Every pre-flight guard
  still runs for real and can still reject the call; only the final `codex` invocation is
  short-circuited after resolving it (Windows shim resolution, or a new POSIX PATH/executable check),
  so a caller can validate its arguments, containment checks, and exact assembled prompt without
  spending a real Codex call or, for guardrails' `danger-full-access` path, granting any real
  unsandboxed execution. Live PR review (Devin/Codex/CodeRabbit) found and fixed three issues before
  merge: the POSIX PATH resolution didn't match real `spawn`'s own semantics for relative/empty PATH
  entries or reject a directory named `codex`; and `--dry-run` given a malformed value (a typo, or a
  bare flag with no value) silently fell through to a real dispatch instead of failing closed — the
  most serious of the three, since for guardrails that means real unsandboxed execution on a typo. A
  round-2 review pass then found the PATH-resolution fix itself introduced a regression: omitting
  `cwd` entirely (a documented, legitimate `runCodexExec` call shape) crashed with a `TypeError`
  outside any cleanup path, instead of defaulting to `process.cwd()` the way a real dispatch already
  does.
- Fixed `bridge-invoke.mjs`'s `semanticallyValidate` discarding an entire returned envelope
  over a single out-of-scope/nonexistent `location`/`components[]` citation (issues
  #236/#111) — it now drops just the affected finding (or, for a `components`-only miss,
  just that citation) and records the drop in `inspection_limits`, so `cross-model-review`'s
  resolver no longer falls back to single-model mode over one plausible, otherwise-valid
  finding. A `dispatch.id`/`dispatch.reviewer` mismatch or a duplicate finding id still
  reject the whole envelope, unchanged.
- Fixed the above fix: the dropped-finding note recorded in `inspection_limits` echoed the raw,
  model-controlled `location`/`component` text verbatim, which could let a crafted citation
  (e.g. containing `"CreateProcessAsUserW"`) misclassify as a total sandbox failure via
  `isTotalInspectionFailure()` once `findings` was empty, triggering an unwarranted
  `danger-full-access` fallback (found by `cross-model-review`, live-verified against the
  actual call order in `main()`). The note is now a fixed, static string with no
  citation text embedded.
- Fixed the above fix's own residual gap: the "fixed, static" note still interpolated
  `finding.id`, which is just as model-controlled and unconstrained (`type: "string"`,
  no pattern) as the `location`/`component` text the first fix removed — a crafted `id`
  containing the same process-start-failure phrasing reopened the identical
  `isTotalInspectionFailure` misclassification path. Found by a second round of
  `cross-model-review` against the first fix; the note is now fully static with zero
  interpolated values.
- Fixed two more issues in the same graceful-degradation path, both found by this PR's own
  GitHub-side automated review (Devin + Codex): (1) a finding's `components` field was
  unconditionally coerced from `null` to `[]`, erasing the distinction between a legitimate
  single-file finding and a multi-file finding whose components all got dropped — it's now
  only reassigned when it started as an array; (2) if *every* returned finding got dropped as
  out-of-scope/nonexistent, the envelope still returned `ok: true` with an empty `findings`
  array — indistinguishable from a genuine clean pass to `scripts/marketplace_ci`'s
  `validate_review_output`/`run-codex-review`, which derive `blocking` purely from `findings`
  and never read `inspection_limits`. An all-hallucinated Codex response could silently pass
  CI with zero real review coverage. `semanticallyValidate` now fails the whole envelope
  closed when the original findings list was non-empty but nothing survived filtering — a
  response that never had findings to begin with is unaffected.

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
