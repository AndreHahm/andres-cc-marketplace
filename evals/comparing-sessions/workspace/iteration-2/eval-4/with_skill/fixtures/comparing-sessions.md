---
name: comparing-sessions
description: >-
  Compares two Claude Code sessions structurally, running a deterministic
  diff over two persisted analysis-kit reports, then
  interprets what changed semantically — component performance trends,
  suggestion recurrence, tool/framework detection stability. This is a full
  structural/semantic comparison, not a single contradiction flag (for that
  narrower check, see `analyzing-governance-and-conflicts`' session-vs-session
  conflict category). Compares the same report lineage across two points in
  time — this session vs. a prior persisted report — not multiple different
  skills' reports from one shared scope (for that, see
  `reviewing-analysis-findings`). Also checks whether an implemented
  recommendation's expected effect was actually realized, against the
  recommendation lifecycle registry.
when_to_use: >-
  Use when comparing this session to a prior one, checking whether a prior
  session's suggestions were acted on, or tracking a trend across multiple
  sessions.
---
