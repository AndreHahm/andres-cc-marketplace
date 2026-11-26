---
name: tracking-recommendation-lifecycle
description: >-
  Appends one status-change event to the shared, append-only recommendation registry
  (`.claude/output/analysis-kit-recommendations/events.jsonl`) for a recommendation produced by
  `generating-analysis-recommendations`, moving it through proposed/accepted/declined/implemented/
  verified/measured/closed/reopened/superseded. Never infers `verified` from a commit landing or
  `measured` from a passing test alone -- both require the user to supply the actual evidence behind the
  claim, per this plugin's own evidence-over-assertion discipline. Also reports current/historical status
  for one or all tracked recommendations. Use when marking a recommendation accepted/declined, recording
  that a fix landed or was verified, logging a measured real-world effect, or checking a recommendation's
  current lifecycle status.
---
