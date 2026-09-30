---
name: clean-skill
description: >-
  Summarizes TODO and FIXME markers found in a single text file. Use when a user asks to
  list, count, or summarize TODO markers in one file.
when_to_use: >-
  Use when summarizing the TODO or FIXME comments of one named file.
allowed-tools: Read Grep
---

# Clean Skill

## Quick Start

Read the named file, find TODO and FIXME markers with Grep, and list each marker with its line number.

## When to Use

- Summarizing TODO and FIXME markers in one file

## When NOT to Use

- Searching a whole repository for markers — use a repo-wide search instead

## Testing & Validation

**Verify this skill activates on:**
- "summarize the TODOs in this file"

**Verify it does NOT activate on:**
- "find every TODO in the repo" → a repo-wide search

**Quality gates:**
- [ ] Every marker in the file appears in the summary with its line number

## Goal Verification

After summarizing, check that every marker found by Grep appears in the summary with its line number; report any marker that was missed.

## Reference Guide

This skill has no reference files.
