---
description: Apply organization-wide rules (from merge-rules output) to the current project. Detects tech stack, merges Principles, cleans up promoted patterns from .local.md, and fixes non-conforming files.
argument-hint: "[source-url-or-path] [--dry-run] [--config <path>]"
allowed-tools: Read, Glob, Grep, Write, AskUserQuestion, Bash(ls *), Bash(mkdir *), Bash(wc *), Bash(mktemp *), Bash(rm -rf */rules-apply-*), Bash(rm .claude/rules/**/*.local.md), Bash(gh api *), Bash(gh auth status *)
---

Apply organization-wide rules to the current project using the `rules-apply` skill: $ARGUMENTS
