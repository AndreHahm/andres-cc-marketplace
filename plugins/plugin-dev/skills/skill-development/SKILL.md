---
name: skill-development
description: >-
  Create, test, evaluate, improve, repair, and consolidate Claude Code skills. Use when the user
  asks to "create a skill", "add a skill to plugin", "write a new skill", "improve a skill",
  "make a skill for X", "turn this into a skill", "convert a slash command to a skill", "apply a
  skill template", "improve skill description", "organize
  skill content", "fix a broken skill", "repair a skill", "consolidate skills", "find duplicate
  skills", "bulletproof a skill", "verify skill under pressure", or "compliance test a skill".
  Also covers skill structure, progressive disclosure, skill categories, testing, compliance
  testing, and slash-command conversion for Claude Code plugins.
allowed-tools: Read Write Edit Glob Grep Agent Skill Bash(python:*) Bash(mkdir:*)
---

# Skill Development for Claude Code Plugins

Create, test, measure, and iteratively improve skills using category-aware design, gotchas-driven development, and progressive disclosure. Covers the full lifecycle: from understanding intent through design, testing, improvement, and polish. Also covers slash-command conversion, repair, and consolidation.

## When to Use

This skill covers the full skill lifecycle — creation, testing, improvement, repair, and consolidation. The Quick Start table below maps your goal to the right entry path.

## Quick Start

Identify the entry path and jump in:

| Path | When to Use | First Step |
|---|---|---|
| **Extract** | "turn this into a skill" | Extract tools/steps from conversation → write minimal SKILL.md → test on original task |
| **Greenfield** | "make a skill for X" | Start with one concrete task → succeed → extract winning approach into skill |
| **Audit** | "improve/audit this skill" | `cp -r` snapshot → run Quality Checklist → fix violations |
| **Convert** | "convert slash command to skill" | Read `${CLAUDE_SKILL_DIR}/references/slash-command-conversion.md` |
| **Repair** | "fix/repair a skill" | `scripts/repair_skill.py --diagnose <skill-name>` |
| **Consolidate** | "find duplicate/consolidate skills" | `scripts/scan_skills.py` → `scripts/analyze_similarity.py` |

## When NOT to Use

- **Refining an existing skill only** → use `/skill-refiner-interactive`
- **Reviewing skill quality** → use the `skill-reviewer` agent
- **Quick standalone repair (issue already diagnosed)** → run `scripts/repair_skill.py` directly; skip the full skill workflow
- **Standalone empirical benchmarking of an already-built skill** (with_skill vs. baseline pass rates, timing/token metrics, iteration-over-iteration comparison) → use `skill-tester`. This skill's own Phase 3 is scoped to validating a skill *during its own creation/audit workflow*, not a dedicated benchmark pipeline — don't run both on the same skill in the same pass.

## Mindset

Skills are instructions **for Claude**, not documentation for people. Always ask: "Will this help Claude execute the task?" — not "Is this readable?" Every line must earn its place by pushing Claude out of default patterns, providing project-specific context, or naming a non-obvious constraint.

## About Skills

Skill directory structure:
- `SKILL.md` (required) — instructions and navigation
- `scripts/` — executable code for deterministic tasks
- `references/` — docs loaded into context as needed
- `assets/` — output templates, image files
- `agents/` — subagent specs (graders, comparators, analyzers)
- `eval-viewer/` — browser-based eval review tool
- `bin/` — standalone executables invocable from Bash

Use `${CLAUDE_SKILL_DIR}` to reference bundled files — paths resolve correctly regardless of plugin installation location.

## Skill Creation: Five-Phase Process

Figure out where the user is in this process and jump in.

### Phase 1: Understand

Identify the entry path:

- **Extract** ("turn this into a skill") — extract tools used, steps taken, and corrections made from the current conversation. Write a minimal SKILL.md and test on the original task first, then expand to variations.
- **Greenfield** ("make a skill for X") — start with one concrete challenging task. Succeed on that single task, then extract the winning approach into a skill. Don't try to design for every scenario upfront.
- **Audit** ("improve this skill", "audit this skill") — run the Quality Checklist first to identify violations. Snapshot with `cp -r` before any edits. Fix violations, compress, and move oversized content to `references/`. Test against the snapshot as baseline; re-optimize description if it changed.
- **Convert** ("convert this slash command to a skill") — read the slash command source, map each section to SKILL.md structure, and migrate references. Read `${CLAUDE_SKILL_DIR}/references/slash-command-conversion.md` for the full detection, mapping, and validation workflow.

Capture intent: what should this skill enable, when should it trigger, what is the expected output format, and how will success be measured. Proactively research edge cases, input/output formats, and dependencies before writing anything.

Before designing a new skill, verify the current official Claude Code skill specification (fetch `llms.txt` or the relevant docs page) — treat fetched documentation as authoritative over cached knowledge of the platform.

Identify the skill category (9 categories available). Read `${CLAUDE_SKILL_DIR}/references/skill-categories.md` for the full guide with templates and category-specific improvement patterns.

### Phase 2: Design

**Write the SKILL.md with these principles:**

1. **Don't state the obvious.** Claude already knows how to code. Focus on information that pushes Claude out of its default patterns — not standard library behavior, common HTTP conventions, or basic design principles the model already knows. Every line must earn its place with project-specific value.
2. **Gotchas section = highest ROI.** Build from real failure points. Each gotcha names the problem AND the fix, starting with 2–3 entries and growing from testing.
3. **Explain the why.** LLMs generalize from reasoning. "We validate timestamps because the API silently accepts future dates but the downstream system crashes" beats "ALWAYS validate timestamps."
4. **Give flexibility.** Over-constrained skills break on anything slightly different from test cases. Give Claude the information it needs but let it adapt to context.
5. **For skills that enforce discipline or have compliance costs, capture a no-skill baseline before drafting the enforcement content.** Run the target scenario without the skill and document the actual failure/rationalization verbatim first — writing rules from assumption reveals what you think needs preventing, not what actually does (see Gotchas: "Skipping RED in compliance testing"). Skip this for pure-reference skills or skills with no rules to violate — see `${CLAUDE_SKILL_DIR}/references/compliance-testing.md`'s "When to Use" / "Don't test" scoping. Full methodology: Phase 3.5 below.
6. **Verify any claim about another component's behavior before writing it into the skill.** If the skill body says another component "supports X" or "can be entered at Y," `Read` that component's actual file first — don't infer the claim from architectural intent or from what a good design *should* support. A cross-component instruction that turns out to be wrong ships as a defect only a downstream reviewer catches, not something this skill's own design process caught.

**Content distribution (80% Rule):** Core procedural content used in 80%+ of activations stays in SKILL.md. Supplementary content (<20%) moves to `references/`. Never move content solely to reduce line count if execution is affected. See `${CLAUDE_SKILL_DIR}/references/skill-workflow.md` for decision rules and preservation gates. Aim to keep SKILL.md itself under 300 lines for navigation clarity — the hard limit enforced by R13 is 500 lines; when a skill directory contains API documentation, schema tables, or background reference material exceeding ~100 lines, extract it to `references/` as a concrete size-based trigger alongside the 80% Rule.

**Skill placement:** Confirm where the skill will live before creating: project-scoped (`.claude/skills/`), user-space (`~/.claude/skills/`), or plugin-scoped (`skills/` in plugin). Never default to user-space without asking — it affects all projects.

**Complex skill considerations:** For error handling, tool scoping, validation, and security review patterns: `${CLAUDE_SKILL_DIR}/references/complex-skills-patterns.md`. For self-containment architecture: `${CLAUDE_SKILL_DIR}/references/self-containment-principle.md`. For secrets/credentials handling: `${CLAUDE_SKILL_DIR}/references/secrets-and-credentials.md`. For tool scoping (principle of least privilege): `${CLAUDE_SKILL_DIR}/references/allowed-tools.md`. Any skill that uses shell-injected dynamic context must be reviewed as executable content; design it to degrade gracefully when `disableSkillShellExecution` is set.

**Reference linking pattern:** Front-load what the file covers before linking it: `Pattern: [core idea]. See \`references/file.md\` for [edge cases/advanced scenarios].` Without context, Claude loads references out of uncertainty. With it, Claude loads them intentionally.

**Structure the folder** by deciding what each level contains:
- `scripts/` — helper functions, validation scripts, data fetchers. Bundle when all subagents independently write similar code.
- `references/` — API docs, detailed specifications. Split by variant for multi-framework support.
- `workflows/` — multi-step procedural flows invoked from SKILL.md (keep each file under 300 lines). **After writing**: verify no `workflows/` file links to a `references/` file as an action step — such chains force runtime context loads callers don't expect.
- `assets/` — output templates, image files.
- `bin/` — standalone executables the Bash tool can invoke by name.

For platform features (frontmatter fields, string substitutions, hook system), read `${CLAUDE_SKILL_DIR}/references/platform-reference.md`.

**Lifecycle and field semantics:** Skill content is injected into the conversation at invocation and remains active until compaction or session end — write instructions as standing guidance for the full task, not one-time setup text. If a skill expects free-form user input, place `\$ARGUMENTS` at the intended position in the body; Claude Code does not append it automatically. Use `disable-model-invocation: true` to block autonomous invocation and `user-invocable: false` only to hide a skill from the slash menu — the latter does not restrict programmatic invocation. Never use `${CLAUDE_PLUGIN_ROOT}` or `${CLAUDE_PLUGIN_DATA}` in prose body text outside code blocks or inline code — these expand at runtime and produce unexpected literal strings in documentation contexts. Skills also support `when_to_use`, `arguments`, `disallowed-tools`, `effort`, `context`, `agent`, `background`, `hooks`, `paths`, and `shell` — full field-by-field schema in `${CLAUDE_SKILL_DIR}/references/schemas.md`.

For design patterns (sequential workflow, multi-MCP coordination, gotchas structure, progressive disclosure, hooks, composability), read `${CLAUDE_SKILL_DIR}/references/design-patterns.md`.

**Principle of Lack of Surprise:** Skills must not contain malware, exploit code, or content that facilitates unauthorized access or data exfiltration. A skill's contents should not surprise the user in their intent. Decline requests to create misleading skills or skills designed for malicious purposes.

**Writing patterns** — use these structural templates when defining output formats or examples:

*Output format definition:*
```markdown
## Report structure
ALWAYS use this exact template:
# [Title]
## Executive summary
## Key findings
## Recommendations
```

*Examples pattern:*
```markdown
## Commit message format
**Example 1:**
Input: Added user authentication with JWT tokens
Output: feat(auth): implement JWT-based authentication
```

### Phase 3: Test

1. Write 2–3 realistic test prompts. Share with the user for approval. Save to `evals/evals.json` (schema: `${CLAUDE_SKILL_DIR}/references/schemas.md`).
2. Spawn all runs in one turn — one with-skill, one baseline (no skill, or snapshot of previous version). Launching everything at once lets runs finish around the same time.
3. **Capture timing** when each subagent task completes — save `timing.json` to the run directory immediately: `{"total_tokens": ..., "duration_ms": ..., "total_duration_seconds": ...}`. This data arrives through the task notification only and isn't persisted elsewhere; process each notification as it arrives.
4. Draft assertions while runs are in progress. Read `${CLAUDE_SKILL_DIR}/references/eval-writing-guide.md` for how to write good assertions.
5. Grade each run using `${CLAUDE_SKILL_DIR}/agents/grader.md`. `grading.json` expectations must use fields `text`, `passed`, and `evidence` — the viewer depends on these exact field names. Aggregate: `python -m scripts.aggregate_benchmark <workspace>/iteration-N --skill-name <name>` — this writes the iteration's `benchmark.json`/`benchmark.md` and appends a summary row to `<workspace>/benchmark-log.md`, a cumulative running history across all iterations (append-only — never edit past rows by hand). Then do an analyst pass — read `${CLAUDE_SKILL_DIR}/agents/analyzer.md` for patterns (non-discriminating assertions, high-variance evals, time/token tradeoffs).
6. Launch eval viewer: `python ${CLAUDE_SKILL_DIR}/eval-viewer/generate_review.py <workspace>/iteration-N --skill-name <name>`. For iteration 2+: add `--previous-workspace`. The viewer has two tabs — **Outputs** (click through test cases, leave feedback; previous iteration output shown collapsed) and **Benchmark** (pass rates, timing, token usage per configuration). Navigation via prev/next or arrow keys; "Submit All Reviews" saves `feedback.json`.
7. After a Claude model update, rerun evals. A pass rate drop signals needed adaptation.

→ Once baseline quality is confirmed, run **Phase 3.5** to verify compliance under adversarial conditions.

Do NOT use `/skill-test` or other testing skills during eval runs — they conflict with this workflow.

### Phase 3.5: Compliance Testing (TDD for Skills)

**What it tests**: Whether the skill enforces compliance under adversarial conditions — not just whether it improves output quality. Run this after Phase 3 quantitative evals confirm baseline quality.

Apply RED-GREEN-REFACTOR to skill documentation:

| TDD Phase | What You Do |
|-----------|-------------|
| **RED** | Run scenario WITHOUT skill — document exact failures and rationalizations verbatim |
| **GREEN** | Write skill addressing specific failures — nothing beyond what you observed |
| **REFACTOR** | Find new rationalizations, add explicit counters; re-test until no new rationalizations appear |

Write **pressure scenarios** with 3+ simultaneous pressures (time + sunk cost + authority + exhaustion). Single-pressure scenarios agents resist; multiple pressures reveal real behavior. Force an explicit A/B/C choice — never open-ended.

When a scenario fails: capture the rationalization verbatim → add an explicit negation in the rules → add a row to a rationalization table → add a red flag entry → update description with the violation symptom → re-test.

A skill is bulletproof when the agent: chooses the correct option under maximum pressure, cites skill sections, acknowledges the temptation, and meta-testing confirms "the skill was clear, I should follow it."

For the full methodology — pressure types, scenario templates, rationalization table format, meta-testing protocol (three response types), worked example, common mistakes — read `${CLAUDE_SKILL_DIR}/references/compliance-testing.md`.

### Phase 4: Improve

1. Read transcripts, not just final outputs.
2. Generalize from feedback — fix broadly, not fiddly. Try different metaphors or patterns if a stubborn issue persists.
3. Keep the prompt lean — remove instructions not pulling their weight. If rewriting finds ALWAYS or NEVER in all-caps, treat it as a signal: reframe as reasoning so the model understands why, rather than imposing rigid constraints.
4. Bundle repeated code — if all subagents independently write similar helper scripts, bundle the script in `scripts/` and reference from SKILL.md.
5. Add on-demand hooks if the model strays outside intended boundaries.
6. Always bump to `iteration-<N+1>/` — never rerun into a previous iteration.

For blind A/B comparison: `${CLAUDE_SKILL_DIR}/agents/comparator.md`. For benchmark pattern analysis: `${CLAUDE_SKILL_DIR}/agents/analyzer.md`.

### Phase 5: Polish

**Description optimization** — the description is a trigger condition, not a summary. Front-load trigger phrases. `description` should run 80–1024 characters, `when_to_use` up to 512, and the two combined cap at 1536 characters (see `references/size-limits.md` for the full tiered thresholds). Describe what the skill does and when to trigger it — not the internal workflow steps; a description that summarizes procedural steps reduces activation accuracy because Claude treats it as already-known detail rather than a trigger to read the body.

**Description formula:** `[Action]. Use when [trigger contexts]. [Scope/constraints].` Example: "Create Claude Code skills. Use when building new skills, improving existing ones, or converting slash commands. Covers full lifecycle: design, test, improve, polish." The exact formula is flexible, but the description must activate Claude on the right input without requiring the skill name to be mentioned — begin with the trigger context or primary use case.

Structure the description as **What + When**: What lists 5–8 specific capabilities using precise action verbs (Validate, Inject, Refactor — not vague terms like "manage" or "handle"). When defines explicit trigger conditions. For technical skills with file-based activation, add a trigger hint suffix: `(triggers: *.ext, keyword)`.

Generate 20 trigger eval queries (mix of should-trigger and should-not-trigger). Effective queries are specific: include file paths, personal context, backstory — not generic requests. Save as JSON `[{"query": "...", "should_trigger": true/false}]`. Then review with the user: read `${CLAUDE_SKILL_DIR}/assets/eval_review.html`, substitute `__EVAL_DATA_PLACEHOLDER__`, `__SKILL_NAME_PLACEHOLDER__`, and `__SKILL_DESCRIPTION_PLACEHOLDER__`, write to a temp file, and open it. The user edits queries and exports `eval_set.json`.

Run the optimization loop from `${CLAUDE_SKILL_DIR}`:

```bash
python -m scripts.run_loop \
  --eval-set <path-to-eval.json> \
  --skill-path <path-to-skill> \
  --model <model-id-powering-this-session> \
  --max-iterations 5 \
  --verbose
```

Apply `best_description` from JSON output to the frontmatter.

For troubleshooting (doesn't trigger, triggers too often, instructions not followed, large context, frontmatter errors), read `${CLAUDE_SKILL_DIR}/references/troubleshooting-guide.md`.

Package with: `python ${CLAUDE_SKILL_DIR}/scripts/package_skill.py <path/to/skill-folder>`

If the `present_files` tool is available, present the resulting `.skill` file directly to the user. Otherwise, direct the user to the file path for download.

## Plugin-Specific Considerations

### Skill Location in Plugins

Plugin skills live in the plugin's `skills/` directory:

```
my-plugin/
├── .claude-plugin/plugin.json
└── skills/
    └── my-skill/
        ├── SKILL.md
        ├── references/
        └── scripts/
```

Create the structure directly — plugin skills do not use `init_skill.py` (for standalone skills outside a plugin, `${CLAUDE_SKILL_DIR}/scripts/init_skill.py <skill-name> --path <dir>` scaffolds a template directory):

```bash
mkdir -p plugin-name/skills/skill-name/{references,scripts}
touch plugin-name/skills/skill-name/SKILL.md
```

### Auto-Discovery

Claude Code automatically discovers skills by scanning `skills/` for subdirectories containing `SKILL.md`. Metadata (name + description) is always loaded; the SKILL.md body loads when the skill triggers; references and scripts load as needed.

### No Packaging Needed

Plugin skills are distributed as part of the plugin — not as separate ZIP files. Users get skills when they install the plugin.

### Testing in Plugins

```bash
cc --plugin-dir /path/to/plugin
```

## Skill Repair & Maintenance

Skills fail to load for predictable reasons. Common symptoms: "Unknown skill" errors, skills visible on disk but not discoverable, YAML parse failures, structural issues.

### YAML Frontmatter Requirements

YAML validation failures are the most common cause of "Unknown skill" errors:
- `name` must be **kebab-case only** — lowercase letters, numbers, hyphens. No underscores, Title Case, or camelCase.
- `name` must not contain "anthropic" or "claude" (reserved words — rejected silently).
- `name` must not be a YAML boolean keyword (`on`, `off`, `yes`, `no`, `true`, `false`).
- Use spaces, not tabs; Unix line endings (LF).
- Unquoted colons in `description` cause parse errors — wrap the value in quotes.

### Automated Repair

```bash
scripts/repair_skill.py --diagnose <skill-name>   # identify issues without changing anything
scripts/repair_skill.py <skill-name>              # fix automatically
scripts/repair_skill.py --list-issues             # audit all skills
```

### Known Platform Quirks

- **SDK vs CLI:** Skills may not auto-discover when using the Claude Agent SDK — this is a known platform issue. Validate with the CLI first.
- **Cache:** `/clear` may not flush skill caches. After adding or modifying a skill, exit and restart Claude Code completely.

### Prevention

1. Validate with `quick_validate.py` after creation or modification.
2. Keep directory names and registry entries consistent.
3. Test skill loading immediately after creation — don't batch validate later.

## Skill Consolidation

Identify and clean up duplicate or obsolete skills in a growing collection (10+ skills).

### Workflow

```bash
# Step 1: build inventory
python scripts/scan_skills.py --output skill_inventory.json

# Step 2: find merge candidates (Jaccard similarity on triggers/keywords)
python scripts/analyze_similarity.py --inventory skill_inventory.json --threshold 0.65
# outputs: skill_consolidation_report.md + skill_analysis.json

# Step 3: review report and execute merges/archives manually
```

### Decision Criteria

**Merge when:** ≥80% similarity, overlapping triggers causing ambiguous activation, or complementary workflows in the same domain.

**Archive when:** Never activated (`activation_count = 0`), unused for 6+ months, tech stack changed, or features removed.

**Archive process:** Move skill directory to `skills/archive/`, create `ARCHIVED.md` with reason and restoration steps, remove from registry, update `related_skills` references in other skills.

## Writing Style

Write the entire skill in **imperative/infinitive form** (verb-first), not second person:

✅ `To create a hook, define the event type.`
❌ `You should create a hook by defining the event type.`

Frontmatter `description` must use **third person**, prefixed with what the skill does:

✅ `Create Claude Code skills. Use when the user asks to "create X", "configure Y"...`
❌ `Use this skill when you want to create X...`

Target 1,500–2,000 words for the SKILL.md body. Move detailed content to `references/`.

**Writing philosophy:** Explain the why behind instructions — LLMs generalize from reasoning, not rules. "We check this because the downstream system crashes on future timestamps" is more powerful than "ALWAYS validate timestamps." Use theory of mind: understand what the user is trying to accomplish and transmit that understanding into the instructions. Avoid rigid ALWAYS/NEVER directives; if one appears, consider whether the reasoning can be stated instead.

## Communicating with the User

Adapt technical vocabulary to the user's apparent familiarity:
- "Evaluation" and "benchmark" are generally acceptable
- "JSON" and "assertion" require explanation unless the user has shown clear technical fluency
- Offer brief definitions when in doubt — non-technical users may be first-time CLI users

## Platform Adaptations

**Claude.ai:** Subagents unavailable — run test cases inline one at a time; skip baseline runs. No browser — present results in conversation instead of launching the viewer. Skip quantitative benchmarking and description optimization (requires `claude -p` CLI). Packaging still works. When updating an existing skill, preserve the original name and copy to a writable location before editing.

**Cowork:** Subagents work (use parallel runs; fall back to serial on timeouts). No display — use `--static <output_path>` with `generate_review.py` to produce a standalone HTML file; share the path as a link. **Generate the eval viewer before reviewing outputs yourself** — present to the user first. Feedback downloads as `feedback.json` when the user clicks "Submit All Reviews". Description optimization (`run_loop.py`) works via subprocess; run after the skill is finalized.

## Gotchas

- **Don't use other testing skills during Phase 3.** `/skill-test` or similar skills will conflict with this skill's eval workflow. Run evals using the steps in Phase 3 directly.
- **Skipping RED in compliance testing.** Writing compliance rules before watching an agent fail without the skill reveals what YOU think needs preventing, not what actually does. Always run no-skill baseline scenarios first.
- **Snapshot before improving.** Always `cp -r` the skill before making changes in Phase 4. Without a snapshot, there's no meaningful baseline comparison — the "before" is gone.
- **Create the workspace before spawning subagents.** `mkdir -p <skill-name>-workspace/iteration-N/<eval-name>` upfront. If each subagent tries to create the same parent directory, race conditions produce half-populated directories.
- **Don't reuse iteration numbers.** When improving, always bump to `iteration-<N+1>/`. Rerunning into a previous iteration silently overwrites the baseline needed for comparison.
- **`benchmark-log.md` is append-only.** It's the one cumulative file spanning all iterations — never rewrite or delete a past entry by hand. `scripts/aggregate_benchmark.py` appends automatically; only ever add to it, matching the same discipline as not reusing iteration numbers.
- **Kill the eval viewer.** The viewer process stays alive after review. Forgetting `kill $VIEWER_PID` causes port conflicts or zombie processes on subsequent launches.
- **Don't over-design upfront.** The biggest time sink is spending 30 minutes on a perfect SKILL.md that turns out to need rewriting after the first eval. Write the minimum, test, then improve.
- **Description bloat.** If the capability summary in the description exceeds 100 words (quoted trigger phrases excluded), some capabilities belong in the body. Description is a trigger condition, not a manual — move excess to SKILL.md body or `references/`.
- **Vague file triggers.** Avoid broad patterns like `src/**` or `**/*` for file-based trigger conditions — be surgical. Broad patterns cause over-triggering across unrelated files.
- **Optional: task tracking for multi-task workflows.** For multi-task skill-creation workflows, using TaskCreate/TaskUpdate/TaskList improves reliability and auditability. This is an internal convention, not a platform requirement.
- **Substitution variables in documentation examples.** `${CLAUDE_SKILL_DIR}`, `${CLAUDE_PLUGIN_ROOT}`, and similar patterns are expanded by the platform at runtime. Writing them in a SKILL.md code example that is meant to be illustrative — not executed — causes silent expansion that corrupts the example for the reader. Use plain text placeholders (e.g., `/path/to/skill`, `<skill-dir>`) in documentation context. Only use `${...}` syntax when the code will genuinely be executed with substitution.

## Testing & Validation

**Verify this skill activates on:**
- "create a skill for X" / "add a skill to plugin" / "write a new skill"
- "improve this skill" / "audit this skill" / "fix a broken skill"
- "bulletproof a skill" / "verify skill under pressure" / "compliance test a skill"
- "convert this slash command to a skill" / "consolidate my skills"

**Verify it does NOT activate on:**
- "help me debug Python" / "review my PR" / "write unit tests for X"
- "improve this existing skill" → use `skill-refiner-interactive` instead
- "add a hook to my project" → use `hook-development` instead

**Quality gates:**
- `quick_validate.py` passes without errors
- Description trigger rate ≥80% verified via `run_loop.py`
- `claude plugin validate .` passes
- All Markdown links inside the skill directory resolve — broken links are caught during review, not left for the user to discover
- All files in the skill directory are reachable from `SKILL.md` directly or via referenced files — an unreferenced supporting file is an orphan smell
- After creating or modifying a skill, test activation in a fresh session using natural trigger words, not the skill name itself

## Before Packaging

Run `quick_validate.py`, then work through the full pre-release checklist at `${CLAUDE_SKILL_DIR}/references/checklist.md`. Invoke `plugin-rulebook` to verify naming, language, formatting, and tool-scoping compliance. Before finalizing, verify the current official platform specification for the component type — treat current docs as authoritative over cached or rulebook-cached assumptions.

## Reference Files

### Phase 1–2: Understand & Design

| File | Purpose | When to Read |
|---|---|---|
| `${CLAUDE_SKILL_DIR}/references/lifecycle.md` | Historical draft lifecycle guide (superseded by this file's own Phase 1-5.5 process; kept for token-efficiency background) | Background reference |
| `${CLAUDE_SKILL_DIR}/references/how-skills-work.md` | Token loading mechanics, activation internals, selection mechanism | Phase 1 (understand) — deep dive |
| `${CLAUDE_SKILL_DIR}/references/skill-categories.md` | 9 categories with templates and improvement patterns | Phase 1 (identify category) and Phase 4 (improve) |
| `${CLAUDE_SKILL_DIR}/references/slash-command-conversion.md` | Detection, mapping, conversion logic, validation | Phase 1 — Convert entry path |
| `${CLAUDE_SKILL_DIR}/references/web-search-research.md` | Web search research for unfamiliar domains | Phase 1 (understand) |
| `${CLAUDE_SKILL_DIR}/references/skill-template.md` | Token-optimized skill template (minimal, <100 lines) | Phase 1 (Greenfield — token-budget focus) |
| `${CLAUDE_SKILL_DIR}/references/platform-reference.md` | Frontmatter fields, string substitutions, hook system, platform gotchas | Phase 2 (design) |
| `${CLAUDE_SKILL_DIR}/references/design-patterns.md` | Gotchas patterns, progressive disclosure, hooks, setup, composability | Phase 2 (design) |
| `${CLAUDE_SKILL_DIR}/references/templates.md` | Full skill creation templates (Basic, Complex, patterns, description examples) | Phase 2 (design) — comprehensive scaffold |
| `${CLAUDE_SKILL_DIR}/references/skill-workflow.md` | 80% Rule, content distribution, preservation gates | Phase 2 (design) — content placement decisions |
| `${CLAUDE_SKILL_DIR}/references/resource-organization.md` | Content placement decision framework | Phase 2 (design) |
| `${CLAUDE_SKILL_DIR}/references/content-guidelines.md` | Description formulas, phrase library, activation examples | Phase 2 (design) and Phase 5 (polish) |
| `${CLAUDE_SKILL_DIR}/references/ask-user-question-patterns.md` | AskUserQuestion interaction patterns, decision trees, wizard pattern | Phase 2 (design) — skills with user interviews |
| `${CLAUDE_SKILL_DIR}/references/task-management-patterns.md` | TaskCreate/TaskUpdate instruction patterns for multi-step components | Phase 2 (design) — skills/agents with 3+ step workflows |
| `${CLAUDE_SKILL_DIR}/references/anti-patterns.md` | Token-wasting, activation, structure, content, and tool-scoping anti-patterns | Phase 2 (design) and Phase 4 (improve) |
| `${CLAUDE_SKILL_DIR}/references/advanced-patterns.md` | Production patterns, skill archetypes, specialized skill designs | Phase 2 (design) and Phase 4 (improve) |
| `${CLAUDE_SKILL_DIR}/references/complex-skills-patterns.md` | Error handling, tool scoping, validation scripts, security review | Phase 2 (design) — complex skills |
| `${CLAUDE_SKILL_DIR}/references/allowed-tools.md` | Tool scoping validation, principle of least privilege | Phase 2 (design) — tool scoping |
| `${CLAUDE_SKILL_DIR}/references/self-containment-principle.md` | External dependency architecture and guidance | Phase 2 (design) — external dependencies |
| `${CLAUDE_SKILL_DIR}/references/secrets-and-credentials.md` | Secrets detection, git safety, env-var patterns, testing | Phase 2 (design) — skills with credentials |
| `${CLAUDE_SKILL_DIR}/references/size-limits.md` | Strict size limits reference | Phase 2 (design) |
| `${CLAUDE_SKILL_DIR}/references/tessl-best-practices.md` | Tessl-style Activation/Implementation standards | Phase 2 and Phase 5 |

### Phase 3–5: Test, Improve & Polish

| File | Purpose | When to Read |
|---|---|---|
| `${CLAUDE_SKILL_DIR}/references/schemas.md` | JSON schemas for evals, grading, benchmark, comparison | Phase 3 (test) |
| `${CLAUDE_SKILL_DIR}/references/eval-writing-guide.md` | How to write good assertions | Phase 3 (test) |
| `${CLAUDE_SKILL_DIR}/references/eval-workflow.md` | Step-by-step eval workflow reference | Phase 3 (test) |
| `${CLAUDE_SKILL_DIR}/references/benchmark.md` | Eval-driven scorecard and iteration table | Phase 3–4 (measure quality) |
| `${CLAUDE_SKILL_DIR}/references/compliance-testing.md` | TDD compliance testing: pressure scenarios, rationalization tables, meta-testing protocol | Phase 3.5 — after quantitative evals |
| `${CLAUDE_SKILL_DIR}/references/testing.md` | Trigger rate, eval set schema, regression guide | Phase 3–5 |
| `${CLAUDE_SKILL_DIR}/references/rubric.md` | Tessl-aligned Activation/Implementation grading rubric | Phase 5 (polish) |
| `${CLAUDE_SKILL_DIR}/references/troubleshooting-guide.md` | Doesn't trigger, triggers too often, instructions not followed, large context, frontmatter errors | Phase 5 (polish) and debugging |
| `${CLAUDE_SKILL_DIR}/references/checklist.md` | Comprehensive pre-release validation across all dimensions | Phase 5 (polish) — before packaging |
| `${CLAUDE_SKILL_DIR}/agents/grader.md` | Evaluate assertions against outputs | Phase 3 (test) |
| `${CLAUDE_SKILL_DIR}/agents/comparator.md` | Blind A/B comparison between two outputs | Phase 4 (improve) |
| `${CLAUDE_SKILL_DIR}/agents/analyzer.md` | Analyze benchmark patterns and comparison results | Phase 3–4 |
| `${CLAUDE_SKILL_DIR}/scripts/aggregate_benchmark.py` | Aggregate benchmark results across iterations | Phase 3 step 5 (invoked as `python -m scripts.aggregate_benchmark`) |
| `${CLAUDE_SKILL_DIR}/scripts/run_loop.py` | Run description optimization loop | Phase 5 (polish) |
| `${CLAUDE_SKILL_DIR}/scripts/quick_validate.py` | Quick skill validation check | Phase 5 (before packaging) |
| `${CLAUDE_SKILL_DIR}/scripts/package_skill.py` | Package skill into distributable `.skill` file | Phase 5 (packaging) |
| `${CLAUDE_SKILL_DIR}/scripts/init_skill.py` | Scaffold template directory for standalone (non-plugin) skills | Phase 1 (Greenfield — non-plugin only) |
| `${CLAUDE_SKILL_DIR}/scripts/repair_skill.py` | Diagnose and repair skill loading failures | Skill Repair section |
| `${CLAUDE_SKILL_DIR}/scripts/scan_skills.py` | Inventory all skills with metadata and usage statistics | Skill Consolidation step 1 |
| `${CLAUDE_SKILL_DIR}/scripts/analyze_similarity.py` | Find merge candidates by trigger/keyword overlap | Skill Consolidation step 2 |
| `plugin-rulebook` skill | Plugin-level rules — invoke before finalizing to check naming, language, formatting, tool-scoping, and external-reference compliance | Phase 5 (before packaging) |
| `references/skill-creator-original.md` | Original skill-creator methodology | Background reference |
| `CHANGELOG.md` | Change history for this skill | Reference |

**Internal dependencies** (not directly invoked — referenced by the scripts above): `scripts/run_eval.py`, `scripts/generate_report.py`, `scripts/improve_description.py`, `scripts/utils.py`, `scripts/__init__.py`, `eval-viewer/viewer.html`. `LICENSE.txt` — Apache License 2.0.

**Official docs:** [`llms.txt`](https://code.claude.com/docs/llms.txt) — fetch for platform spec changes (frontmatter, hooks, manifest). Bundled references cover design and eval methodology; official docs are authoritative for platform syntax.
