---
allowed-tools: Bash(git status:*), Bash(git diff:*), Bash(git branch:*), Read
description: Show detailed git repository status
argument-hint: (optional) focus area or file path to emphasize in the summary
---

# Git Status Command

Show detailed git repository status

## Instructions

Analyze the current state of the git repository by performing the following steps:

1. **Run Git Status Commands**
   - Execute `git status` to see current working tree state
   - Run `git diff HEAD origin/main` to check differences with remote
   - Execute `git branch --show-current` to display current branch
   - Check for uncommitted changes and untracked files

2. **Analyze Repository State**
   - Identify staged vs unstaged changes
   - List any untracked files
   - Check if branch is ahead/behind remote
   - Review any merge conflicts if present

3. **Read Key Files**
   - Review README.md for project context
   - Check for any recent changes in important files
   - Understand project structure if needed

4. **Provide Summary**
   - Current branch and its relationship to main/master
   - Number of commits ahead/behind
   - List of modified files with change types
   - Any action items (commits needed, pulls required, etc.)

This command helps developers quickly understand:

- What changes are pending
- The repository's sync status
- Whether any actions are needed before continuing work

Arguments: $ARGUMENTS