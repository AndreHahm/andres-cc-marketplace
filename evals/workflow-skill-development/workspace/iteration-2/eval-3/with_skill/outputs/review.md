# Structural review: deploy-pipeline

Skill files read: workflow-skill-development/SKILL.md and references/anti-patterns-structure.md.

## Findings

### 1. AP-2 Monolithic SKILL.md (640 lines, all inline) - FAIL
The 500-line limit is a hard structural rule, and attention to buried details degrades past it. The draft is 140 lines over, with every procedure, table and example inline.
Fix:
- Keep only principles, routing, quick references and links in SKILL.md.
- Move detailed reference material (tables, examples) to `references/`.
- Move step-by-step procedures to `workflows/`.
- Link each file directly from SKILL.md with a one-line summary.
- Target well under 500 lines.

### 2. AP-4 Hardcoded absolute paths (Step 2 and Step 5) - FAIL
`/Users/jane/projects/deploy/config.yaml` and `/Users/jane/projects/deploy/scripts/push.sh` only exist on Jane's machine. The skill breaks for anyone else, and the rule has no exceptions.
Fix:
- Use `${CLAUDE_SKILL_DIR}` for files the skill ships:
  - Step 2: `Read ${CLAUDE_SKILL_DIR}/references/config.yaml` (or wherever it ships).
  - Step 5: `${CLAUDE_SKILL_DIR}/scripts/push.sh`.
- Use `${CLAUDE_PLUGIN_ROOT}` only in command files.
- If `config.yaml` is project-specific and lives outside the skill, take its path as an argument or discover it with Glob. Do not bake in a user path.
- Step 5 also runs a script that pushes, which is likely destructive or irreversible. Consider a Safety Gate pattern with two confirmations before it runs, and scope any Bash grant narrowly (not bare `Bash`).

### 3. AP-3 Reference chain (overview -> details -> edge-cases) - FAIL
`references/overview.md` sends the reader to `details.md`, which sends it to `edge-cases.md`. That is a chain of reference files pointing at each other. Each hop loses context, and the rule is that every file is one hop from SKILL.md.
Fix:
- Remove the "Before continuing, read..." and "Then read..." lines from the reference files.
- Link `overview.md`, `details.md` and `edge-cases.md` each directly from SKILL.md's Reference Index, stating when to read each.
- Alternatively, merge the content that is always needed together into one file.

### 4. AP-5 / broken-reference risk - CHECK
The reference files must exist and every path must resolve. Verify with Glob. SKILL.md also does not appear to link these files at all, which makes them effectively orphaned until fixed per finding 3.

### 5. Gaps in the summary (verify in the full draft)
The summary is thin, so these could not be confirmed. Check the full file for:
- AP-1: the required When to Use and When NOT to Use body sections (R35), plus an activation-focused third-person description with exclusions. The summary shows only `name`.
- AP-6 / AP-7: numbered phases with entry and exit criteria. The body uses "Step 2", "Step 5", but phase structure is unconfirmed.
- AP-8: a verification step at the end of the pipeline, which matters especially for a deploy.
- Error handling for step failures.
- Tool scoping: least-privilege `allowed-tools`, no bare `Bash`.
- Then run `plugin-rulebook` before finalizing.

## Summary
Three confirmed failures: AP-2 (size), AP-4 (hardcoded paths, two occurrences), AP-3 (reference chain). The other points are unverifiable from the summary and should be checked.
