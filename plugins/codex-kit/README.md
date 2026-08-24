# codex-kit

Delegate work to OpenAI's Codex CLI from Claude Code, with independent verification instead of blind trust: native and adversarial code review, task rescue with diff double-check, document/plan verification, cross-model research, job/session management, an optional stop-time quality gate, and a generic reviewer-agnostic bridge wired into this repository's own marketplace PR pipeline — repository-owned Python (`scripts/marketplace_ci/review.py`) is the sole CI orchestrator, calling the bridge directly rather than executing any codex-kit skill (see the Skills table below). Bundles its own Codex engine — replaces OpenAI's official `codex` plugin rather than depending on it.

## Installation

```bash
/plugin install codex-kit@andres-cc-marketplace
```

Or for local development:

```bash
cc --plugin-dir /path/to/plugins/codex-kit
```

**Prerequisite:** if OpenAI's official `codex` plugin is installed, deactivate it first — codex-kit bundles its own fork of that plugin's engine and is meant to replace it, not run alongside it. See [INSTALLATION.md](./INSTALLATION.md) for the full setup walkthrough, including the sandbox-viability check.

## Usage

Run `/codex-kit:review` to run a native Codex code review against your working tree, with an independent double-check pass that reads only the files/lines Codex cited and classifies each finding using the canonical Agree/Disagree/Nuance/False Positive (hallucination)/Uncited — verification deferred taxonomy before presenting anything to you. Every finding is saved to `${CLAUDE_PLUGIN_DATA}/reviews/` on both success and failure. All 7 commands are deliberately not model-invocable (`disable-model-invocation: true`) — they must be typed as a slash command, never triggered by natural-language phrasing.

## Commands

| Name | Purpose |
|---|---|
| `/codex-kit:setup` | Check Codex CLI readiness, sandbox viability, and config; optionally toggle the stop-time review gate |
| `/codex-kit:review` | Run a Codex code review against local git state, with independent double-check verification |
| `/codex-kit:adversarial-review` | Run a Codex review that challenges the implementation approach and design choices, with independent double-check verification |
| `/codex-kit:status` | Show active and recent Codex jobs for this repository |
| `/codex-kit:result` | Show the stored final output for a finished Codex job in this repository |
| `/codex-kit:cancel` | Cancel an active background Codex job in this repository |
| `/codex-kit:transfer` | Transfer the current Claude Code session into a resumable Codex thread |

## Skills

| Name | Purpose |
|---|---|
| `codex-rescue` | Delegate an implementation task to Codex, then Claude reviews the result |
| `codex-verify` | Verify a plan or document using Codex as independent reviewer with PASS/FAIL verdict |
| `codex-research` | Deep-dive research using Codex with Claude's cross-model synthesis |
| `codex-plan-loop` | Dual-AI plan-validate-implement-review loop with Codex |
| `codex-peer-review` | Validate Claude's own analysis, design, or recommendation against Codex before presenting it to the user |
| `codex-audit-loop` | Whole-project multi-lens Codex audit, optionally with independently-verified autonomous fixing (explicitly opt-in) |
| `codex-review-bridge` | Generic, reviewer-agnostic bridge to Codex — invoked by other components, not directly by end users |
| `codex-windows-guardrails` | Best-effort guardrails (pre-flight scope checks + an instructed command allowlist, not a real sandbox) so a caller can attempt `danger-full-access` locally on Windows, where no working sandbox exists — invoked by other components, disabled by default, not directly by end users |
| `plugin-marketplace-review` | Canonical policy documentation for this repository's own marketplace PR review pipeline. **Documentation-only by design, never CI-executed** — repository-owned Python (`scripts/marketplace_ci/review.py`'s `dispatch_reviewers`) is the sole orchestrator and implements this same policy directly in code, calling `codex-review-bridge` itself rather than executing this skill. |
| `codex-session-lookup` | Look up or inspect Codex CLI's own session/history files |
| `codex-prompt-protocol` | Internal reference for codex-kit's own components — not user-invocable |

## Hooks

`SessionStart`/`SessionEnd` spawn and tear down the internal Codex broker process. An optional `Stop` hook (enable via `/codex-kit:setup --enable-review-gate`) runs a Codex-side check on the prior turn before the session is allowed to stop.

## Known Limitations

- **9 of codex-kit's 11 skills have no live, empirical `skill-tester` run** — graded structurally against their eval's `expected_output` instead (recorded in each skill's own "Testing & Validation" section). See [CONTRIBUTING.md](./CONTRIBUTING.md) for why (several of these skills shell out to the real Codex CLI, so a live run has real external side effects). Two skills have real live coverage: `codex-windows-guardrails` (the 11th, newest skill) has all 3 of its `evals/codex-windows-guardrails/` evals run live, with `grading.json` on disk for each — plus its own persisted, executable smoke test (`scripts/smoke-tests/codex-windows-guardrails-preflight.mjs`, 20 scenarios); `codex-review-bridge` has 3 of its 4 evals (`eval-2`, `eval-3`, `eval-4`) run live, with its original `eval-1` still structural-only.
- **`codex-review-bridge`'s `executionProfile` isn't threaded into the returned envelope** — `provenance.execution_profile` is Codex's own self-report, not an echo of the caller's validated request; a caller auditing which isolation profile actually ran can't yet trust this field. See `codex-review-bridge/SKILL.md`'s "Inputs" section.
- **Six of `codex-review-bridge`'s semantic-validation checks are defined but not yet enforced** — `contract_version` support, full `target_paths` cross-checking, cited line-number validity, `axis`/`severity` allowlist-checking, `verdict` pass/fail-rule consistency, and undeclared-inspection-limit detection. See `codex-review-bridge/references/semantic-validation.md`'s "Not yet implemented" list.
- **The `Stop` review-gate hook can block for up to 9 minutes** — an accepted, disclosed deviation from the platform's own "hooks should complete in under 5 seconds" performance guidance, since the gate's entire job is running a real Codex review before the session may stop. It's opt-in only (`config.stopReviewGate` defaults to `false`), the duration is disclosed to the user via `AskUserQuestion` at `/codex-kit:setup --enable-review-gate` time, and `hooks/hooks.json`'s own 600s timeout stays safely under the platform's hard-kill ceiling. If Claude Code begins throttling or auto-disabling a hook that "regularly" runs this long, this is the tradeoff to revisit.

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md).

## License

Apache-2.0. The engine (`scripts/app-server-broker.mjs`, `scripts/codex-companion.mjs`, `scripts/session-lifecycle-hook.mjs`, `scripts/stop-review-gate-hook.mjs`, `scripts/lib/*`) is a derivative work of OpenAI's official `codex` plugin — see [NOTICE](./NOTICE) for the full attribution and list of modifications.
