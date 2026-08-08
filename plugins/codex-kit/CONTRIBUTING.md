# Contributing

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
4. If the change alters a skill's or command's actual behavior (not just prose formatting), test it — a `skill-tester` Quick Workflow eval run is the mechanism this plugin's own build used; see `evals/<skill-name>/` at the repo root for the existing eval definitions and grading records per skill.
5. Open a pull request.

## Code Style

No linter is currently configured for this plugin's `.mjs`/`.py` files. Match the existing style in the file you're editing.

See [README.md](./README.md) for installation and usage — this file covers contribution workflow only.
