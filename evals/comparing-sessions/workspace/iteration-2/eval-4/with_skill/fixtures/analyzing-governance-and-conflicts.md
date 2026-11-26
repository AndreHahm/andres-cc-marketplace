---
name: analyzing-governance-and-conflicts
description: >-
  Analyzes rule/boundary/convention conformance and detects conflicts —
  agent-vs-agent, rule-vs-rule, spec-vs-code, and session-vs-session — across
  a Claude Code session, tracks recurring errors and mistakes, and separately
  assesses maintainability/change-impact risk (duplication, coupling, stale
  mirrors, documentation drift, blast radius) exposed by the session's own
  changes — reported as a second, independent section since structural drift
  can exist with no rule naming it. Reuses
  the shared cross-component-inventory tooling for rule evidence. Use when
  checking whether a session followed its own project rules and
  conventions, finding contradictions between agents/rules/specs, tracking
  which mistakes keep recurring across sessions, or assessing whether a
  session's changes introduced duplication, coupling, or maintenance risk.
---
