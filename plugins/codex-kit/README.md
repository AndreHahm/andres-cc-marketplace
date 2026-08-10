# codex-kit

Delegate work to OpenAI's Codex CLI from Claude Code, with independent verification instead of blind trust: native and adversarial code review, task rescue with diff double-check, document/plan verification, cross-model research, job/session management, an optional stop-time quality gate, and a generic reviewer-agnostic bridge for CI/audit use cases (its integration into this repository's own PR pipeline is not yet operational — see the Skills table below). Bundles its own Codex engine — replaces OpenAI's official `codex` plugin rather than depending on it.

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

Run `/codex-kit:review` to run a native Codex code review against your working tree, with an independent double-check pass that reads only the files/lines Codex cited and classifies each finding as Agreed/Disagreed/Nuanced/False Positive/Uncited before presenting anything to you. Every finding is saved to `${CLAUDE_PLUGIN_DATA}/reviews/` on both success and failure. All commands except `/codex-kit:setup` are deliberately not model-invocable (`disable-model-invocation: true`) — they must be typed as a slash command, never triggered by natural-language phrasing.

## Commands

| Name | Purpose |
|---|---|
| `/codex-kit:setup` | Check Codex CLI readiness, sandbox viability, and config; optionally toggle the stop-time review gate |
| `/codex-kit:review` | Run a Codex code review against local git state, with independent double-check verification |
| `/codex-kit:adversarial-review` | Run a Codex review that challenges the implementation approach and design choices, with independent double-check verification |
| `/codex-kit:status` | Show active and recent Codex jobs for this repository, including review-gate status |
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
| `plugin-marketplace-review` | Thin CI orchestration skill for this repository's own marketplace PR pipeline. **Not yet operational** — its required input (`ReviewScope`, produced by `scripts/marketplace_ci/review.py`) doesn't exist in this repository yet, so it currently has no way to run. |
| `codex-session-lookup` | Look up or inspect Codex CLI's own session/history files |
| `codex-prompt-protocol` | Internal reference for codex-kit's own components — not user-invocable |

## Hooks

`SessionStart`/`SessionEnd` spawn and tear down the internal Codex broker process. An optional `Stop` hook (enable via `/codex-kit:setup --enable-review-gate`) runs a Codex-side check on the prior turn before the session is allowed to stop.

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md).

## License

Apache-2.0. The engine (`scripts/app-server-broker.mjs`, `scripts/codex-companion.mjs`, `scripts/session-lifecycle-hook.mjs`, `scripts/stop-review-gate-hook.mjs`, `scripts/lib/*`) is a derivative work of OpenAI's official `codex` plugin — see [NOTICE](./NOTICE) for the full attribution and list of modifications.
