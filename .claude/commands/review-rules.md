---
description: Check code changes for .claude/rules/ compliance. Matches changed files against applicable rule files, runs parallel compliance reviewers, and reports violations with suggested fixes.
argument-hint: "[--base-commit <sha>]"
allowed-tools: Read, Glob, Agent, Bash(git diff *), Bash(git rev-parse *)
---

Check code changes for rules compliance using the `rules-review` skill: $ARGUMENTS
