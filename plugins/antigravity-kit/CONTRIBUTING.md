# Contributing

## Preferred Language

This plugin's preferred scripting language is **bash** — `scripts/*.sh` (the delegation, cost-compare,
job, media, trace, and doctor logic) and `hooks/*.sh` carry the plugin's core behavior, with no build
step. `scripts/agy-migrate.py` and `scripts/measure-session.py` are a named exception for JSON/YAML-heavy
work where Python is a better fit; new scripts should default to bash unless there's a specific reason
to add another Python one.

## Development Setup

You need the [Antigravity CLI](https://antigravity.google/docs/cli-using) (`agy`, authenticated — `agy
models` should list Gemini models) and Claude Code. No package manager is needed.

```bash
bash tests/run-tests.sh          # dependency-free; stubs `agy`, no network
shellcheck scripts/*.sh tests/*.sh hooks/*.sh   # --severity=error
```

## Proposing a Change

1. Branch off `main` using this repo's `<type>/<description>` convention (see `.commitlintrc.cjs` for the
   type enum).
2. Make your change.
3. Run the test suite and shellcheck before opening a PR:
   ```bash
   bash plugins/antigravity-kit/tests/run-tests.sh
   shellcheck --severity=error plugins/antigravity-kit/scripts/*.sh plugins/antigravity-kit/tests/*.sh plugins/antigravity-kit/hooks/*.sh
   ```
4. If you touch `hooks/`, `bin/`, or `scripts/`, run `bash plugins/antigravity-kit/scripts/doctor.sh` —
   it validates the executable-bit contract this plugin relies on.
5. If you touch a manifest, confirm it still parses:
   `python3 -c "import json; json.load(open('plugins/antigravity-kit/.claude-plugin/plugin.json'))"`
6. Keep [`skills/antigravity/SKILL.md`](skills/antigravity/SKILL.md) honest — it's the plugin's brain.
   If behavior changes, update it; don't claim a capability the code doesn't have.
7. Check [`KNOWN_ISSUES.md`](KNOWN_ISSUES.md) for unresolved gaps before starting — your change may
   already be tracked there, or resolve one of them.
8. Open a pull request.

## Conventions

- Match the surrounding style — POSIX-ish bash, `set -euo pipefail`, quote expansions.
- **Target bash 3.2.** macOS still ships `/bin/bash` 3.2.57, and macOS is a supported platform, so
  `declare -A`, `readarray`/`mapfile`, `${var^^}` and friends are out. Same for GNU-only flags on `sed`,
  `date`, and `grep` — BSD userland is the floor. Testing on Linux only will not catch these.
- New scripts get a `usage()` and a test in `tests/run-tests.sh`.
- Cost numbers in docs are estimates — if you quote figures, say so and point at `prices.json`.

See [README.md](./README.md) for installation and usage — this file covers contribution workflow only.
