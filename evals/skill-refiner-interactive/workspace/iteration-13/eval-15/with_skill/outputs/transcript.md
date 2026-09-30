# Transcript: skill-refiner-interactive, eval-15 (Validation against diverged mirror)

Operator request: "Validate the skill demo-mirror."
Target copies: `target/skills/demo-mirror/` (plugin copy) and `target/claude-mirror/skills/demo-mirror/` (`.claude/skills/` mirror).

## Quick Start A (escape hatch)
Conversation history has no predating context (no skill file, problem description, or active skill discussion; the request only names the skill and the action). Escape-hatch question NOT asked. Continue to B.

## Quick Start B
Request already names the skill (`demo-mirror`). Plain-text "What skill do you want to work on?" skipped.

## Quick Start C
Request already says "Validate". Action question skipped.

## Quick Start D
Route: "Validate" -> skip the interview, go directly to Core Workflow: Validation. No pre-analysis, no goal selection, no BATCH 1/2.

## Core Workflow: Validation, step 1 (Locate the skill)
- Glob `**/skills/demo-mirror/SKILL.md` under the target tree finds two copies: `target/skills/demo-mirror/SKILL.md` and `target/claude-mirror/skills/demo-mirror/SKILL.md`.
- Gitignore exclusion: neither path is in a gitignored directory (.temp/.draft/.backup); both are real candidates.
- Mirror-pair check (R19): both the plugin copy and the `.claude/skills/` mirror exist, so treat as an in-development staging mirror. Compared SKILL.md (the only file in each copy; no references/ or scripts/ in either). Result: they DIFFER.
  - Line 11 differs:
    - plugin copy: `Read the file, find TODO markers with Grep, and list each with its line number.`
    - mirror copy: `Read the file, find TODO markers with Grep, and list each with its line number, grouped by marker type.`
- Differ -> HALT per R19. Because this is Validation (never edits a copy), ask the Validation form of the Mirror question from `references/interview-question-templates.md`.

### AskUserQuestion (Validation form of Mirror question)
```
question: "Found this skill at both target/skills/demo-mirror/ and target/claude-mirror/skills/demo-mirror/, but their content differs. Validation is report-only and changes nothing. How should I proceed?"
header: "Mirror"
options:
  - "Show me the diff first": display what differs, then end the session so the operator can reconcile and re-run
  - "Stop": don't touch either copy; end the session so the operator can reconcile
```
(Only two options; no "[path A] is correct" / "[path B] is correct" overwrite options, because Validation never edits a copy.)

Simulated operator answer: **"Show me the diff first"**

## Acting on the answer
Display what differs:
```
--- target/skills/demo-mirror/SKILL.md
+++ target/claude-mirror/skills/demo-mirror/SKILL.md
@@ line 11 @@
-Read the file, find TODO markers with Grep, and list each with its line number.
+Read the file, find TODO markers with Grep, and list each with its line number, grouped by marker type.
```
Frontmatter identical in both copies (name, description, allowed-tools). Only the Quick Start body line differs.

Per the template, "Show me the diff first" in Validation means: display the diff, then END THE SESSION so the operator can reconcile the copies and re-run. No authoritative copy is chosen, nothing is overwritten.

## Outcome
- Validation step 2 (delegate to `skill-reviewer` and `plugin-rulebook`) NOT reached.
- Validation step 3 (present the report) NOT reached.
- DELEGATION REACHED: no (session ended at the mirror halt, before any delegation; no report presented).
- Session ended after showing the diff; the operator is asked to reconcile the two copies and re-run validation.
- No edits made to either copy; no files created other than this transcript, `final-tree.txt`, and the copied fixture under `target/`.
