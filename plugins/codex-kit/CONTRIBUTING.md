# Contributing

## Preferred Language

This plugin's preferred scripting language is **JavaScript (Node.js, `.mjs`)** — `scripts/*.mjs` and `scripts/lib/*.mjs` are the engine and carry no build step. The two Python scripts under `skills/codex-session-lookup/scripts/` (`find-session-id.py`, `inspect-session-file.py`) are a named exception, ported from an earlier design wave; new scripts should default to `.mjs` unless there's a specific reason to add another Python one.

## Development Setup

No package manager config is bundled with this plugin — `scripts/*.mjs` and `scripts/lib/*.mjs` run on Node.js directly (no build step), and the two Python scripts under `skills/codex-session-lookup/scripts/` run on Python 3 directly. Nothing to install beyond Node.js, Python 3, and the Codex CLI itself (see [INSTALLATION.md](./INSTALLATION.md)).

## Proposing a Change

1. Branch off `main` using this repo's `<type>/<description>` convention (e.g. `fix/codex-kit-sandbox-probe`).
2. Make your change.
3. Verify syntax before committing:
   ```bash
   node --check plugins/codex-kit/scripts/<changed-file>.mjs
   python3 -m py_compile plugins/codex-kit/skills/codex-session-lookup/scripts/<changed-file>.py
   ```
4. If the change alters a skill's or command's actual behavior (not just prose formatting), test it. Two mechanisms exist, and most changes need both:
   - **Eval definitions** exist under `evals/<skill-name>/` at the repo root (`skill-tester` Quick Workflow shape) for all 11 of this plugin's skills. 9 of the 11 have been structurally graded only — Claude read each skill's documented behavior against its eval's `expected_output` and recorded a verdict in that skill's own SKILL.md "Testing & Validation" section — with no live, empirical `skill-tester` run (`grading.json`/`outputs/` from a real with-skill agent dispatch) on disk, since several of these skills shell out to the real Codex CLI and a live run would have real external side effects. Two skills have real live coverage instead: `codex-windows-guardrails` has all 3 of its evals run live, with `grading.json` on disk for each; `codex-review-bridge` has 3 of its 4 evals (`eval-2`, `eval-3`, `eval-4`) run live, with its original `eval-1` still structural-only. Running and grading a live eval for the skill you changed — not just re-confirming the structural grade — is still the mechanism this plugin intends to use for a behavior change.
   - **Persisted smoke tests** under `plugins/codex-kit/scripts/smoke-tests/` (`node scripts/smoke-tests/<name>.mjs`, run from `plugins/codex-kit/`) cover specific deterministic behavior fixes — see that directory's own `README.md` for what each one checks and when to re-run it.
5. Open a pull request.

## Code Style

No linter is currently configured for this plugin's `.mjs`/`.py` files. Match the existing style in the file you're editing.

See [README.md](./README.md) for installation and usage — this file covers contribution workflow only.
