# Trace: standalone-commits Step 6 (Wave 2 Commit)

## Scenario
Wave 2 of a 3-wave sequence. Files already staged. Commit claim already written. Evaluating step 6 execution exactly as prescribed by the Staging Workflow in SKILL.md.

---

## Staging Workflow Step 6: Commit the Staged Wave in Three Parts

### Step 6a: Compose Message
**Instruction (SKILL.md line 97-98):**
> Compose the message per `commit` skill's "Best Practices for Commits" (conventional format) and "Commit Message Footer" sections — link to those sections rather than restating the type list or trailer table here, so the two skills can't drift apart on format. Make the subject name the outcome, not the implementation detail (see "Commit Message Shape" below).

**Tool Call 1: (Implicit - Instruction Execution)**
- Action: Compose a conventional commit message following the `commit` skill's documented format sections
- References: `commit` skill's "Best Practices for Commits" (conventional format) and "Commit Message Footer" sections
- Subject line pattern: `<type>(<scope>): <outcome description>` — names the outcome, not the implementation detail
- Body (if present): explains the reason, invariant, or review boundary per `commit` skill's footer guidance
- **Key behavior:** The composed message uses the format conventions from `commit` skill; this SKILL.md documentation links to those sections rather than restating the type list or trailer table inline

**Example composed message (for tracing purposes):**
```
feat(schema): add required field metadata types and validation factory functions

This wave establishes the Wave 1 foundation contract that Wave 2 implementation
and Wave 3 consumers depend on. Includes:
- IconDefinition and CoverDefinition types
- FieldMetadata type with optional name/description
- Factory helpers for creating field metadata

The wave is reviewable and auditable on its own: types alone are sufficient
to verify the contract is sound and complete.
```

---

### Step 6b: Confirm via AskUserQuestion
**Instruction (SKILL.md line 98-99):**
> Confirm with `AskUserQuestion` — show the exact composed message and ask "Commit this wave with this message?" — options "Commit as shown" / "Revise the message" / "Stop". "Revise the message" loops back to 6a; "Stop" leaves the wave's files staged but uncommitted.

**Tool Call 2: AskUserQuestion**
- **Prompt structure:**
  - Title/question: "Commit this wave with this message?"
  - Display: The exact composed message from step 6a
  - Options:
    1. "Commit as shown"
    2. "Revise the message"
    3. "Stop"

- **Conditional flow (per skill instructions):**
  - If "Commit as shown" → proceed to step 6c
  - If "Revise the message" → loop back to step 6a (recompose)
  - If "Stop" → exit step 6; files remain staged but uncommitted

**Critical sequencing note:** This AskUserQuestion appears **before** step 6c's marker-write. The confirmation is shown to the user before any git-kit marker is written or before `git commit` is executed.

---

### Step 6c: Commit (Conditional on "Commit as shown" Selection)

#### Step 6c.1: Write Git-Kit Marker (Immediately Before Commit)
**Instruction (SKILL.md line 99-101):**
> Immediately before committing, run `"${CLAUDE_PLUGIN_ROOT}/scripts/write-git-kit-marker.sh" git-commit standalone-commits` — this writes the marker git-kit's commit-guard hook requires (it accepts markers up to 60 seconds old, so write it right before this step, not earlier, and after 6b's confirmation — not before it, since a slow confirmation could otherwise let the marker go stale before `git commit` runs).

**Tool Call 3: Bash (write-git-kit-marker.sh)**
- **Command:** `"${CLAUDE_PLUGIN_ROOT}/scripts/write-git-kit-marker.sh" git-commit standalone-commits`
- **Timing:** Executes **immediately after** 6b's confirmation ("Commit as shown" selected), **immediately before** the `git commit` command
- **Purpose:** Writes the marker git-kit's commit-guard hook (`guard-raw-commit.sh`) requires to allow the commit
- **Marker freshness:** Valid for up to 60 seconds; must be written right before `git commit` to ensure it does not go stale during a slow confirmation
- **Dependency:** This marker-write does NOT occur if user selected "Revise the message" or "Stop" in step 6b

**Critical ordering constraint:** Marker is written AFTER 6b's confirmation gate, not before. This prevents a stale marker if the user confirmation takes longer than expected.

#### Step 6c.2: Execute git commit
**Instruction (SKILL.md line 101-102):**
> Then run `git commit` with the confirmed message.

**Tool Call 4: Bash (git commit)**
- **Command:** `git commit -m "<the confirmed message from step 6b>"`
- **Argument:** The exact message confirmed by the user in step 6b (subject + body if present)
- **Execution:** Happens immediately after the marker-write (Tool Call 3)
- **Result:** Creates a new commit in the branch with the confirmed message, containing all staged files from step 3

---

## Summary of Tool Call Sequence

| Sequence | Step | Tool | Trigger | Timing Relative to Confirmation |
|----------|------|------|---------|--------------------------------|
| 1 | 6a | (instruction execution) | Compose message | Before confirmation |
| 2 | 6b | `AskUserQuestion` | Show message & confirm | **Before marker-write** ← **CRITICAL** |
| 3 | 6c.1 | `Bash` (write-git-kit-marker.sh) | Write marker | **After confirmation, before git commit** ← **CRITICAL** |
| 4 | 6c.2 | `Bash` (git commit) | Execute commit | After marker-write |

---

## Key Assertions Verified by This Trace

### Assertion 1: AskUserQuestion showing exact composed message fires BEFORE marker-write
- **Evidence from trace:** Tool Call 2 (AskUserQuestion) occurs at step 6b, before Tool Call 3 (write-git-kit-marker.sh) at step 6c.1
- **Skill.md reference:** "Confirm with `AskUserQuestion` — show the exact composed message" (line 98) appears before "immediately before committing, run ... write-git-kit-marker.sh" (line 99-101)
- **Status:** SATISFIED

### Assertion 2: Marker-write happens AFTER confirmation, immediately before git commit, not BEFORE confirmation
- **Evidence from trace:** 
  - Tool Call 2 (AskUserQuestion in 6b) is the confirmation gate
  - Tool Call 3 (write-git-kit-marker.sh in 6c.1) is explicitly listed as occurring "immediately before committing"
  - Tool Call 3 is positioned after the conditional "If 'Commit as shown'" from step 6b
  - Tool Call 4 (git commit in 6c.2) immediately follows Tool Call 3
- **Skill.md reference:** "write it right before this step, not earlier, and after 6b's confirmation — not before it, since a slow confirmation could otherwise let the marker go stale before `git commit` runs" (line 100-101)
- **Status:** SATISFIED

### Assertion 3: Composed message references commit skill's sections rather than restating type list or trailer table inline
- **Evidence from trace:**
  - Step 6a instruction: "Compose the message per `commit` skill's 'Best Practices for Commits' (conventional format) and 'Commit Message Footer' sections — link to those sections rather than restating the type list or trailer table here" (SKILL.md line 97-98)
  - The SKILL.md itself links to the `commit` skill's sections by name, does not restate the conventional type list (feat/fix/etc.) or the footer trailer table inline
- **Skill.md reference:** "link to those sections rather than restating the type list or trailer table here, so the two skills can't drift apart on format" (line 98)
- **Status:** SATISFIED

---

## Conclusion

The Staging Workflow step 6 as written in SKILL.md prescribes:
1. Compose the message using conventions from the `commit` skill (not restating them)
2. Show the exact message via AskUserQuestion **before** the marker-write
3. Write the marker **after** confirmation, **immediately before** git commit
4. Execute git commit

This ordering satisfies all three assertions. The skill correctly gates the marker-write behind the user's confirmation, preventing stale markers from being written during slow confirmations.
