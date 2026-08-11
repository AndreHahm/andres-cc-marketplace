# starting-work Skill Trace
## Scenario: "Start new work for feature add-caching"
- Current branch: main (synced with origin)
- Working tree: clean
- Step 3 answer: Worktree
- Step 4 answer: Use default path

---

## Ordered Tool Call Sequence

### Step 1: Note the starting point and sync

1. **Bash**: `git branch --show-current`
   - Purpose: Capture starting branch for report
   - Expected output: `main`

2. **Bash**: `git fetch origin --prune`
   - Purpose: Sync local repo with remote, remove stale remote-tracking branches

3. **Bash**: `git symbolic-ref refs/remotes/origin/HEAD`
   - Purpose: Resolve the actual default branch name (fallback to `main` if fails)
   - Expected output: `refs/remotes/origin/main`

4. *No AskUserQuestion needed here*: User is already on `main` (the resolved default branch), so the "base off resolved branch or current branch" question does not fire per instructions line 41.

5. **Bash**: `git status --porcelain`
   - Purpose: Verify working tree is clean before proceeding
   - Expected output: (empty, indicating clean tree)

6. *No `git pull --ff-only` in this scenario*: User is already synced per scenario, already on default branch. The instructions state: "If not already on the resolved default branch, ask via AskUserQuestion" and "If basing off it: git checkout <resolved-branch>, then git pull". Since we're already on the default branch and synced, the checkout/pull steps are not needed.

---

### Step 2: Resolve the branch name

7. *No AskUserQuestion needed*: The scenario provides "feature add-caching" as the work description (part of the user's initial task). Assume `$ARGUMENTS = "feature add-caching"` supplies both type and description.
   - Type: `feature` — validated as single lowercase word ✓
   - Description: `add-caching` — validated as kebab-case ✓
   - Both valid; no re-ask needed per instructions line 59.

---

### Step 3: Ask worktree or plain branch

8. **AskUserQuestion** (FIRST worktree-related question)
   - **Exact text from SKILL.md (line 65-66)**: "Create a plain branch, or a separate worktree for this?"
   - **Options** (with `use_worktree: true`, the default):
     - "Worktree (Recommended)"
     - "Plain branch"
   - **Simulated user answer**: "Worktree"
   - **Note**: This question asks *whether* to create a worktree, not *where* (per line 131).

---

### Step 4: Create

9. **Bash**: `"${CLAUDE_PLUGIN_ROOT}/scripts/write-git-kit-marker.sh" git-branch-create starting-work`
   - Purpose: Write the git-branch-create marker immediately before creating the branch/worktree (instructions line 73-76)
   - Timing: Must be run right before branch/worktree creation, not earlier

10. **AskUserQuestion** (SECOND, distinct question — specifically for worktree path)
    - **Exact text from SKILL.md (lines 83-84)**: "Create the worktree at `<path>`?"
    - **Computed default path** (instructions line 78): `.claude/worktrees/add-caching`
    - **Options** (from line 84):
      - "Use this path"
      - "Enter a different path"
    - **Simulated user answer**: "Use this path"
    - **CRITICAL REQUIREMENT** (lines 85-86): "Don't rely on step 3's worktree-vs-branch question to also cover the path (its own options only ever say 'Plain branch' / 'Worktree' — never fold the computed path into that option's description text as a substitute for asking here)."
    - **Timing**: Fires AFTER the worktree-vs-branch answer (Step 3), BEFORE `git worktree add` runs (see line 94)

11. **Bash**: `git worktree add -b feature/add-caching .claude/worktrees/add-caching`
    - Purpose: Create the worktree with the branch name and confirmed path
    - Branch name: `feature/add-caching` (from step 2)
    - Path: `.claude/worktrees/add-caching` (from step 4's AskUserQuestion confirmation)

12. **Bash**: `git worktree lock .claude/worktrees/add-caching --reason "claude session"`
    - Purpose: Lock the worktree immediately after creation to prevent accidental removal (instructions line 95-97)

---

### Step 5: Report

13. *Prose/text output only* (not a tool call):
    - Report the branch name created: `feature/add-caching`
    - Report the worktree path: `.claude/worktrees/add-caching`
    - Report current location and that `cd`-ing into the worktree path is needed
    - Report that the worktree is now session-locked
    - Point to `finishing-work`/`/git-cleanup` for removal
    - Mention `git-worktrees` for further operations

---

## Summary of Tool Calls in Order

| # | Tool | Command/Question | Purpose |
|---|---|---|---|
| 1 | Bash | `git branch --show-current` | Capture starting branch |
| 2 | Bash | `git fetch origin --prune` | Sync with remote |
| 3 | Bash | `git symbolic-ref refs/remotes/origin/HEAD` | Resolve default branch |
| 4 | Bash | `git status --porcelain` | Verify clean tree |
| 5 | AskUserQuestion | "Create a plain branch, or a separate worktree for this?" | Ask worktree vs. branch (Step 3) |
| 6 | Bash | write-git-kit-marker.sh git-branch-create starting-work | Write marker before branch creation |
| 7 | AskUserQuestion | "Create the worktree at `.claude/worktrees/add-caching`?" | Confirm worktree path (Step 4) |
| 8 | Bash | `git worktree add -b feature/add-caching .claude/worktrees/add-caching` | Create worktree |
| 9 | Bash | `git worktree lock .claude/worktrees/add-caching --reason "claude session"` | Lock worktree |

---

## Key Finding: Two Distinct AskUserQuestion Calls

**Step 3 (Worktree-vs-Branch):**
- Question: "Create a plain branch, or a separate worktree for this?"
- Asks: *whether* to use a worktree
- Options mention only "Plain branch" and "Worktree", not any path
- Fires: Before step 4, before marker script, before path decision

**Step 4 (Worktree-Path Confirmation):**
- Question: "Create the worktree at `<path>`?"
- Asks: *where* to create the worktree
- Options are "Use this path" and "Enter a different path" with validation on override
- Fires: After step 3's worktree answer, after marker script, before `git worktree add`
- Computed path (`.claude/worktrees/add-caching`) is NOT mentioned in step 3's options
