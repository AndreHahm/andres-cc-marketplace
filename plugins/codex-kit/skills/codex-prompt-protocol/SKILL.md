---
name: codex-prompt-protocol
description: >-
  Internal reference for codex-kit's own components — prompt-composition
  vocabulary, companion invocation protocol, the double-check evaluation
  framework, and Codex CLI/model reference. Not user-invocable; other
  codex-kit components Read these files directly rather than duplicating
  their content.
disable-model-invocation: true
allowed-tools: ["Read"]
---

# codex-kit prompt & invocation protocol

This skill has no user-facing trigger. It exists so every other codex-kit component reads one canonical source instead of each maintaining its own copy of the same knowledge.

## Quick Start

No Quick Start in the usual sense — `disable-model-invocation: true`, this skill is never itself invoked. The "quick start" for a caller is: `Read` the specific reference row below that matches the question at hand, rather than reading this whole table.

| Reference | Covers |
|---|---|
| `references/prompt-blocks.md` | The full 14-tag XML vocabulary — `task`, `structured_output_contract`, `compact_output_contract`, `default_follow_through_policy`, `completeness_contract`, `verification_loop`, `missing_context_gating`, `grounding_rules`, `citation_rules`, `action_safety`, `tool_persistence_rules`, `research_mode`, `dig_deeper_nudge`, `progress_updates` — used across `codex-rescue`, `codex-verify`, `codex-research`, and the Stop-gate prompt — `content_trust_boundary` is defined separately in `references/shared-skill-conventions.md` §1 |
| `references/invocation-protocol.md` | How to call `codex-companion.mjs` correctly: flag whitelists per subcommand, Pattern A (background+poll, for review/adversarial-review) vs. Pattern B (stdin pipe to `task --background`, for rescue/verify/research), job ID capture |
| `references/evaluation-framework.md` | The double-check taxonomy (Agree/Disagree/Nuance/False Positive (hallucination)/Uncited — verification deferred), self-bias awareness, agreement-level summary format |
| `references/cli-reference.md` | Internal engineering reference for codex-kit's own bundled scripts: model/effort resolution mechanics (never a hardcoded model list), sandbox-mode flags, the stdin-non-TTY hang gotcha, timeout/crash recovery |
| `references/error-taxonomy.md` | The `runCodexExec`-side error/failure category table (`codex-review-bridge` and anything else calling `runCodexExec` directly) and the basis for its typed-failure object — a separate category set from `codex-companion.mjs`'s own error surface, documented in `invocation-protocol.md` §6 instead |
| `references/shared-skill-conventions.md` | Conventions specific to `codex-rescue`/`codex-verify`/`codex-research`'s shared 5-phase shape: the `content_trust_boundary` block's required invariants, the double-check taxonomy applied to that trio, the session-level first-send confirmation gate, and delimiter neutralization for untrusted content appended into shell-assembled prompts |

Any codex-kit component needing prompt-composition guidance, invocation mechanics, evaluation vocabulary, or CLI/model details should `Read` the relevant reference file directly rather than re-deriving or duplicating this content.

---

## Testing & Validation

**Verify this skill activates on:**
- Nothing conversational — `disable-model-invocation: true`, and it has no user-facing trigger by design. Other codex-kit components `Read` its reference files directly; this skill itself is never invoked.

**Concrete scenarios to check:**
1. Every reference file listed in the table above actually exists at the stated path.
2. Each reference file's content matches what the table's "Covers" column claims (no stale description after an edit to the underlying file).
3. A cited symbol/function name (e.g. `handleReviewCommand`, `readTaskPrompt`) in `invocation-protocol.md` resolves to something that actually exists in `scripts/codex-companion.mjs`/`scripts/lib/*.mjs`.

**Current test coverage:**
- `evals/codex-prompt-protocol/evals.json` — 1 defined scenario (locating the XML tag vocabulary and error taxonomy without claiming to be user-invocable). Structurally graded 2026-08-12 (PASS — the reference table correctly points to `prompt-blocks.md` and `error-taxonomy.md`, and `disable-model-invocation: true` plus the "no user-facing trigger" prose both hold); this skill has no independent runtime behavior beyond "is it read correctly," so a live empirical run would add limited value here.
- `scripts/smoke-tests/codex-prompt-protocol-references.mjs` — mechanically verifies all three concrete scenarios above: every reference-table row's file exists, `disable-model-invocation`/`Read`-only stay set, and a representative set of symbol names cited in `invocation-protocol.md` resolve to real functions in `codex-companion.mjs`/`scripts/lib/*.mjs`.

**Quality gates:**
- [ ] Every table row's reference file exists at the stated path
- [ ] `invocation-protocol.md`'s citations use symbol names, not line numbers, so they don't drift when the cited file is edited
- [ ] `disable-model-invocation: true` stays set — this skill should never be model-selected
