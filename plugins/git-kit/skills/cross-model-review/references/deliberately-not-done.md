# Deliberately Not Done

- **No Phase 0 deterministic lint/typecheck gate** — this repo already runs linters/formatters
  before every commit via `.pre-commit-config.yaml`; a duplicate gate here would be redundant.
- No loop-until-both-agree (models converge by going silent, not by being right).
- No persisted artifacts / state machine — `$RUN` is scratch, not committed (see Phase 3's closing
  note on why it isn't actively deleted either).
- No auto-applying fixes.
- No enabling `codex-windows-guardrails` on the user's behalf — it stays opt-in.
