---
name: Flaky test triage
area: testing
slug: testing__flaky-triage
internal_id: p2c3d4e5f6a7
version: 1
short_description: Find tests that fail intermittently and suggest a cause.
status: draft
origin: web
source_ref:
  url: https://example.com/prompts/flaky-tests
  retrieved_on: "2026-11-12"
---

Look at the last twenty CI runs for the default branch.
List each test that both passed and failed in that window.
For each one, suggest the most likely cause and the file to look at first.
Stop when every listed test has a suggested cause.
