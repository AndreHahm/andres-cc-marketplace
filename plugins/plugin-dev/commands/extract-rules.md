---
description: Extract project-specific coding rules and domain knowledge from the existing codebase, generating markdown documentation for AI agents. Supports multiple modes including codebase scan, conversation extraction, PR review extraction, update, restructure, and compaction.
argument-hint: "[--update|--restructure|--compact|--from-conversation [session-id]|--from-pr <number|range>]"
allowed-tools: Read, Glob, Grep, Write, Edit, Agent, TodoWrite, Bash(ls *), Bash(mkdir *), Bash(git ls-files *), Bash(git checkout HEAD -- *), Bash(wc *), Bash(head *), Bash(tail *), Bash(sort *), Bash(uniq *), Bash(tree *), Bash(gh pr view *), Bash(gh pr diff *), Bash(gh api *), Bash(gh auth status *), Bash(gh repo view *), Bash(node *)
model: opus
---

Extract coding rules and domain knowledge using the `rules-extract` skill: $ARGUMENTS
