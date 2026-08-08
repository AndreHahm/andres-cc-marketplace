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

This skill has no user-facing trigger. It exists so every other codex-kit component reads one canonical source instead of each maintaining its own copy of the same knowledge — consolidating what would otherwise be 4+ overlapping reference docs (per `codex-kit-component-shortlist.md` component #11).

| Reference | Source | Covers |
|---|---|---|
| `references/prompt-blocks.md` | Wave 1 `gpt-5-4-prompting` | The XML tag vocabulary (`task`, `structured_output_contract`, `grounding_rules`, `completeness_contract`, `verification_loop`, `action_safety`, `dig_deeper_nudge`, `compact_output_contract`, `content_trust_boundary`) used across `codex-rescue`, `codex-verify`, `codex-research`, and the Stop-gate prompt |
| `references/invocation-protocol.md` | Wave 2 `companion-usage.md` | How to call `codex-companion.mjs` correctly: flag whitelists per subcommand, Pattern A (background+poll, for review/adversarial-review) vs. Pattern B (stdin pipe to `task --background`, for rescue/verify/research), job ID capture |
| `references/evaluation-framework.md` | Wave 2 `evaluation.md` | The double-check taxonomy (Agreed/Disagreed/Nuanced/False Positive/Uncited), self-bias awareness, agreement-level summary format |
| `references/cli-reference.md` | Wave 3 `codex-cli`/`codex-cli-2`/`codex-exec` | Codex CLI model list, automation-mode/sandbox-mode flags, the stdin-non-TTY hang gotcha, timeout/crash recovery |
| `references/error-taxonomy.md` | Wave 2 `companion-usage.md` §6 + scope-expansion gap #7 | The full error/failure category table shared by every component's error handling, and the basis for component #18's typed-failure object |

Any codex-kit component needing prompt-composition guidance, invocation mechanics, evaluation vocabulary, or CLI/model details should `Read` the relevant reference file directly rather than re-deriving or duplicating this content.
