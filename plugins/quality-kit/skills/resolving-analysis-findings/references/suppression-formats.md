# Suppression Formats

An inline suppression silences one rule on one line and keeps its reason next to the code. Every one carries
a stated reason, and rung 2 on anything other than `Minor`/`Info` or an accepted shape needs the approval in
`SKILL.md`'s Decision rights. Verified on 2026-10-17 means: checked with the local tool, in this repository.

| Engine | Syntax | Status |
|---|---|---|
| Bandit (Python) | `# nosec B603 B607  # list-form call, literal command, no shell` | Local `bandit` only: it skipped all findings on the line and printed no warning. Codacy, including Prospector_bandit, honoring it is not confirmed until the Cloud re-check after a push |
| Bandit, reason after `--` | `# nosec B404 -- reason words` | Works but noisy: Bandit reads each reason word as a test id and prints a warning per word. Use the trailing `# reason` form above |
| Semgrep | `# nosemgrep` or `# nosemgrep: <rule-id>` on the flagged line | Repository precedent (for example workledger-kit's `subprocess.run` calls: `grep -rl nosemgrep plugins scripts`). Not re-verified against Codacy's Semgrep here |
| ESLint | `// eslint-disable-next-line <rule> -- reason` | One file under `plugins/` uses `eslint-disable` (`codex-kit`'s `guarded-dispatch.mjs`); not verified against Codacy |
| Pylint, Biome | `# pylint: disable=<id>`, `// biome-ignore <rule>: reason` | No use in this repository; not verified. Do not rely on them without a check |

## Rules

- **Name the rule ids.** A bare `# nosec` silences every Bandit rule on the line, including ones added later.
  List the ids Codacy actually reports on that line (for example `B603 B607`); a B404 import takes `# nosec B404`.
- **Put it where the finding is reported.** For a multi-line call the finding sits on the line that opens the
  call (`subprocess.run(`), so the comment goes there, not on the argument line.
- **One reason, stated.** The reason says why the shape is safe or accepted ("literal command, list
  arguments, no shell"), not "false positive".
- **Keep lines within the repository's line length** (`line-length` in `pyproject.toml`'s `[tool.ruff]`):
  break a call across lines rather than letting a comment push it over.
- **Edit the canonical `plugins/...` file.** The `.claude/` copy is generated and byte-identical; sync, do
  not hand-edit it.

## Not suppressible inline

A finding raised by an engine with no inline syntax, or one that applies to a whole file, needs rung 3 (a
Codacy ignore) or rung 4 (`exclude_paths`) instead. Both go through the approval gate in `SKILL.md`.
