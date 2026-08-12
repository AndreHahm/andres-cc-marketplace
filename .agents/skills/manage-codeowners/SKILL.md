---
name: manage-codeowners
description: >-
  Bootstrap, view, and maintain a repo's .github/CODEOWNERS file — create one seeded with the repo owner as a catch-all if it doesn't exist yet, add/update/remove path-owner entries, and validate syntax. Use when asked to set up CODEOWNERS, add a codeowner, check who owns a file/path, or when merge-pr reports no CODEOWNERS file exists.
allowed-tools: Bash(gh repo view:*), Read, Write, Edit
---

# Manage CODEOWNERS

Create and maintain `.github/CODEOWNERS`. This file is a load-bearing dependency for `merge-pr`'s rights check (Tier 2) — without it, `merge-pr` fails closed and only the repo owner can ever merge anything.

## Instructions

1. **Check existence**: `Read` `.github/CODEOWNERS`.
2. **If missing — bootstrap**: get the repo owner via `gh repo view --json owner --jq '.owner.login'`. Use `AskUserQuestion` to confirm before writing: show the proposed content (a single catch-all line, `* @<owner>`) and explain why — `merge-pr`'s CODEOWNERS check fails closed with no file, so this line means "only the repo owner can merge until more entries are added." On confirmation, `Write` `.github/CODEOWNERS` with that single line plus a short header comment explaining the file's purpose.
3. **If it exists — show current content**, then ask what the user wants to do:
   - **Add/update an entry**: ask for the path pattern and owner(s) (`@username` or `@org/team`). Append (or `Edit` an existing matching line) — CODEOWNERS resolves ownership by *last matching line wins*, so note that a newly appended pattern will only take precedence over earlier lines if it comes after them in the file; if the intent is to override an earlier broader pattern, place the new line below it.
   - **Remove an entry**: ask which line, confirm via `AskUserQuestion` before deleting (removing a CODEOWNERS line can silently drop someone's merge rights via `merge-pr`'s Tier 2 check).
   - **Validate syntax**: each non-comment, non-blank line must be `<path-pattern> <@owner-or-team>...` — at least one owner token per line, each starting with `@`. Flag any line missing an owner token or using a bare username without `@`.
4. **Report** the resulting file content and path after any write.

## Boundaries

- Only writes `.github/CODEOWNERS` — never touches branch protection rules or repo collaborator settings (those are separate GitHub concepts this skill doesn't manage).
- Bootstrap always asks first — never silently creates the file.
- Does not verify that a listed `@username`/`@org/team` actually exists or has repo access — GitHub itself surfaces that mismatch in its UI; duplicating that check here would need extra API calls for a low-value guard.

## Testing & Validation

**Verify this skill activates on:**
- "set up a CODEOWNERS file for this repo"
- "add a codeowner for the /docs path"
- "who owns this file/path"
- "merge-pr says there's no CODEOWNERS file, can you create one"

**Verify it does NOT activate on:**
- "check if I have merge rights on this PR" → `merge-pr`
- "who can review this PR" → `collaborating-on-a-pr`
- "look up repo settings via the API" → `gh-operations`
- "start a new branch for this" → `starting-work`

**Quality gates:**
- [ ] Bootstrap (file missing) always confirms via `AskUserQuestion` before writing — never silently
      creates the file
- [ ] Bootstrap always seeds a single catch-all line (`* @<owner>`) using the actual repo owner from
      `gh repo view`, plus an explanatory header comment
- [ ] Add/update always accounts for "last matching line wins" — flags when a new pattern needs to go
      below an earlier broader one to take precedence
- [ ] Remove always confirms via `AskUserQuestion` before deleting a line — never removes silently
- [ ] Validate syntax always flags a line missing an owner token or using a bare username without `@`
- [ ] Never touches branch protection rules or repo collaborator settings — CODEOWNERS file only
- [ ] Never verifies that a listed `@username`/`@org/team` actually exists or has access — documented as
      an intentional non-check, not a gap
