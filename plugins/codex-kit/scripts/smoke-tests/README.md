# Smoke Tests

Persistent, dependency-free Node scripts verifying specific behavior fixes in codex-kit. Each file targets one component and exits `0` on all-pass, `1` on any failure — no test framework required.

Run from `plugins/codex-kit/`:

```bash
node scripts/smoke-tests/commands-arg-handling.mjs
node scripts/smoke-tests/codex-review-bridge-trust-boundary.mjs
node scripts/smoke-tests/broker-rpc-auth.mjs
node scripts/smoke-tests/codex-rescue-prompt-assembly.mjs
node scripts/smoke-tests/codex-verify-prompt-assembly.mjs
node scripts/smoke-tests/codex-research-prompt-assembly.mjs
```

Or all at once:

```bash
for f in scripts/smoke-tests/*.mjs; do node "$f" || echo "FAILED: $f"; done
```

## What each one covers

| File | Component | What it verifies |
|---|---|---|
| `commands-arg-handling.mjs` | `commands/status.md`, `result.md`, `transfer.md`, `cancel.md` | The underlying `codex-companion.mjs` subcommands still work when invoked as separate, individually-quoted arguments (the pattern these commands now instruct the model to use, instead of interpolating a raw `$ARGUMENTS` blob). |
| `codex-review-bridge-trust-boundary.mjs` | `skills/codex-review-bridge/scripts/bridge-invoke.mjs` | The containment check rejects an `--instruction-file` that resolves inside `--target-paths` (the self-referential-reviewer-instructions case), and does not false-positive on a legitimately trusted, outside-scope instruction file. |
| `broker-rpc-auth.mjs` | `scripts/app-server-broker.mjs`, `scripts/lib/broker-lifecycle.mjs` | The broker's token-based RPC authentication: rejects no token, rejects a wrong token, accepts the correct token, rejects any request on a never-authenticated socket, and shuts down cleanly with the correct token. Spawns a real broker process. |
| `codex-rescue-prompt-assembly.mjs` | `skills/codex-rescue/SKILL.md`'s Phase 2 heredoc | The condensed prompt-assembly template still produces valid, parseable output and the `JOB_ID`-extraction one-liner still works against a representative job JSON payload. |
| `codex-verify-prompt-assembly.mjs` | `skills/codex-verify/SKILL.md`'s payload-assembly heredoc | The condensed `<content_trust_boundary>`/`<task>`/`<structured_output_contract>`/`<grounding_rules>`/`<completeness_contract>`/`<document>` heredoc still produces well-formed, balanced XML with the document body correctly appended. |
| `codex-research-prompt-assembly.mjs` | `skills/codex-research/SKILL.md`'s payload-assembly heredoc | Same as above, for research's tag set (`<content_trust_boundary>`/`<task>`/`<structured_output_contract>`/`<research_mode>`/`<citation_rules>`/`<grounding_rules>`). |

## When to re-run

- After any further edit to the SKILL.md/command files listed above.
- As part of `plugin-lifecycle-upstream`'s Phase 5 (Test) bounded smoke check for this plugin, or `plugin-lifecycle-downstream`'s Deep Test step for deterministic-script coverage.
- These are static/mechanical checks (bash template correctness, RPC auth logic, XML well-formedness) — they do **not** call the real Codex CLI or consume API quota, except where noted (`broker-rpc-auth.mjs` spawns a real broker process, which in turn spawns a real `codex app-server` process, but never sends it a review/task request).
