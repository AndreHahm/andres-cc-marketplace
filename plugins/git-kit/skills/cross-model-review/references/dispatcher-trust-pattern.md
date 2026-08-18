# Why the dispatcher-trust pattern is shaped this way

Extracted from SKILL.md's Preflight step 6 per plugin-rulebook's R13 (SKILL.md grew past the 500-line
Critical threshold). SKILL.md keeps the check's actual command and the one-line summary that both
alternatives matter; this file holds the fuller "why neither can be dropped" rationale.

The check's pattern is `plugins/codex-kit/(.*/)?(scripts|assets)/`, run against the unscoped
changed-file list. Two parts of that pattern are each load-bearing on their own:

- **The optional `(.*/)?` group.** It must also match `plugins/codex-kit/scripts/lib/codex-exec.mjs`
  — a shared executable both dispatch scripts (`bridge-invoke.mjs` and `guarded-dispatch.mjs`) import
  and run — not just the deeper `plugins/codex-kit/skills/<name>/scripts/*.mjs` paths. A pattern
  requiring an extra directory segment before `scripts/` misses that shared file entirely, letting a
  diff that modifies the actual code both dispatchers execute go undetected.
- **The `assets/` alternative.** `guarded-dispatch.mjs` reads
  `plugins/codex-kit/skills/codex-windows-guardrails/assets/dangerous-command-instructions.txt` and
  that skill's own `assets/settings.json` (which controls whether the Windows fallback is enabled at
  all) to shape and gate a `danger-full-access` run. Both live under `assets/`, not `scripts/`, so a
  `scripts/`-only pattern would miss a diff that weakens either one — the trust-relevant surface isn't
  limited to executable code.
