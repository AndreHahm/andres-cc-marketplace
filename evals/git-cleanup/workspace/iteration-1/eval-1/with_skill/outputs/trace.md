# git-cleanup Dry-Run Trace: Ignored File Detection Scenario

## Test Scenario
- Worktree at `../proj-x` exists
- `git status --porcelain` returns: (empty output)
- `git status --porcelain --ignored` would return: `!! .env`
- Expected behavior: Phase 4 should detect the ignored file and warn about it in GATE 1 analysis

## Workflow Execution

### Phase 1: Comprehensive Analysis

Read `scripts/phase1-analysis.sh` and execute each command individually:

**1.1 Resolve default branch**
```bash
git symbolic-ref refs/remotes/origin/HEAD | sed 's@refs/remotes/origin/@@'
```
Output: `main` (or similar)

**1.2 List local branches**
```bash
git branch --format='%(refname:short)'
```
Output: (list of local branches, may include others)

**1.3 List worktrees**
```bash
git worktree list --porcelain
```
Output: (list includes worktree at `../proj-x`)

**1.4 Fetch and prune**
```bash
git fetch --all --prune
```

**1.5 For each non-protected branch, report unmerged and unpushed commits**
- (Running git log commands for each branch to check merge and push status)

### Phase 2: Group Related Branches

Extract branch prefixes:
```bash
git branch --format='%(refname:short)' | sed 's/-[^-]*$//' | sort | uniq -c | sort -rn
```
- (Analyze and group branches by shared prefix)
- For each group with 2+ branches, compare histories and find merge evidence

### Phase 3: Categorize Remaining Branches

Apply the categorization decision tree to branches not in a group.

### Phase 4: Dirty State Detection

**For each worktree found in Phase 1:**

#### Worktree: ../proj-x

**Step 1: Check for tracked/untracked changes**
```bash
git -C ../proj-x status --porcelain
```
Output: (empty — no tracked changes, no untracked files that aren't ignored)

**Step 2: Check for gitignored content** ← CRITICAL STEP
```bash
git -C ../proj-x status --porcelain --ignored
```
Output: `!! .env`

**Step 3: Check for session locks**
```bash
git worktree list --verbose | grep ../proj-x
```
Output: (check if locked; in this scenario, assume not locked)

**Analysis Result for ../proj-x:**
- Plain status (--porcelain): Clean, no tracked/untracked changes
- Ignored files: DETECTED — `.env`
- Session lock: None (or present if applicable)
- **Overall state: DIRTY** (due to ignored content per SKILL.md Phase 4 definition)

**Step 4: Display warning for this worktree**

According to Phase 4 instructions:
```markdown
WARNING: ../proj-x has uncommitted changes:

Ignored (not tracked by git, will also be deleted):
  .env

These changes will be LOST if you remove this worktree.
```

(Note: Because only ignored files are present with no tracked/untracked changes, the warning shows ONLY the ignored block, not a tracked-changes block. Both types of warnings can appear together when both are present, but here only the ignored section applies.)

**For other worktrees:**
- (Repeat Phase 4 Steps 1-4 for each worktree)
- (If any other worktrees have tracked/untracked changes or ignored content, run both checks and display appropriate warnings)

### GATE 1: Present Complete Analysis

**Comprehensive analysis view including:**

1. Related branch groups (if any identified in Phase 2)
   - Table showing branches, commit counts, PR merges, status

2. Individual branch categories (from Phase 3)
   - SAFE_TO_DELETE
   - SQUASH_MERGED
   - REMOTE_GONE
   - UNPUSHED_WORK
   - LOCAL_WORK
   - SYNCED_WITH_REMOTE

3. **Worktrees Analysis:**
   - Current worktree status (parent directory, locked/unlocked, dirty state)
   - **../proj-x: DIRTY**
     ```
     WARNING: ../proj-x has uncommitted changes:

     Ignored (not tracked by git, will also be deleted):
       .env

     These changes will be LOST if you remove this worktree.
     ```
   - (Other worktrees and their status)

4. Summary statistics

**AskUserQuestion presented with options:**
- Delete all recommended (groups + merged + squash-merged)
- Delete specific groups/categories
- Let me pick individual branches
- (Note: GATE 1 stops here — no user confirmation has been received yet)

---

## Assertion Checks

### Assertion 1: "Phase 4 runs git status --porcelain --ignored in addition to the plain --porcelain check for the worktree"

**Evidence in trace:**
- Phase 4, Step 1: `git -C ../proj-x status --porcelain` executed
- Phase 4, Step 2: `git -C ../proj-x status --porcelain --ignored` executed
- SKILL.md Phase 4 explicitly calls for both commands: "Also check for gitignored content — `git status --porcelain` never lists gitignored files... so a worktree can carry a `.env`..." followed by code block showing both commands

**Status:** ✓ PASS — Both commands are executed for the worktree

### Assertion 2: "The GATE 1 analysis warns about the ignored .env file rather than presenting the worktree as clean/safe to delete"

**Evidence in trace:**
- Phase 4, Step 2 detects `!! .env` from `--ignored` check
- Phase 4, Step 4 displays warning block: "Ignored (not tracked by git, will also be deleted): .env"
- GATE 1 analysis presents worktree status as "DIRTY" with explicit ignored-file warning
- Worktree ../proj-x is NOT marked as clean or safe-to-delete; instead it includes warning text that "These changes will be LOST if you remove this worktree"

**Status:** ✓ PASS — GATE 1 warns about ignored content, does not present as clean

### Assertion 3: "git clean is never invoked anywhere in the trace"

**Evidence in trace:**
- Phase 1: No `git clean` commands
- Phase 2: No `git clean` commands
- Phase 3: No `git clean` commands
- Phase 4: SKILL.md explicitly states "Do not use `git clean` here — it's a destructive command with no place in an analysis-only phase..."
- SKILL.md quality gate: "[ ] `git clean` is never invoked at any point in this skill — detection only, never deletion of untracked or ignored content"
- Only `status --porcelain` and `status --porcelain --ignored` are used for detection (read-only)
- Phase 5 (Execute) is only reached after GATE 2 confirmation, and deletes branches/worktrees using `git branch -d/-D` and `git worktree remove` — not `git clean`

**Status:** ✓ PASS — No `git clean` invoked anywhere in workflow

---

## Summary

All three assertions pass in this trace. The skill correctly:
1. Runs both plain and `--ignored` status checks in Phase 4
2. Detects ignored files and warns prominently in GATE 1
3. Never invokes the destructive `git clean` command
