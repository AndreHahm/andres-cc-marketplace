# Skill Development File Index

Every bundled file `skill-development` ships, with its purpose and the phase in which to read it. Paths are relative to the skill directory (`../../references/` is the plugin-root `references/`). `SKILL.md`'s Reference Guide section points here.

### Phase 1–2: Understand & Design

| File | Purpose | When to Read |
|---|---|---|
| `references/how-skills-work.md` | Token loading mechanics, activation internals, selection mechanism | Phase 1 (understand) — deep dive |
| `references/skill-categories.md` | 9 categories with templates and improvement patterns | Phase 1 (identify category) and Phase 4 (improve) |
| `references/slash-command-conversion.md` | Detection, mapping, conversion logic, validation | Phase 1 — Convert entry path |
| `references/web-search-research.md` | Web search research for unfamiliar domains | Phase 1 (understand) |
| `references/platform-reference.md` | Frontmatter fields, string substitutions, hook system, platform gotchas | Phase 2 (design) |
| `references/templates.md` | Full skill creation templates (token-optimized Basic, Complex, patterns, description examples) | Phase 1 (Greenfield) and Phase 2 (design) — scaffold |
| `references/skill-workflow.md` | 80% Rule, content distribution, preservation gates | Phase 2 (design) — content placement decisions |
| `references/resource-organization.md` | Content placement decision framework | Phase 2 (design) |
| `../../references/pdk-content-guidelines.md` | Description formulas, phrase library, activation examples | Phase 2 (design) and Phase 5 (polish) |
| `../../references/pdk-ask-user-question-patterns.md` | AskUserQuestion interaction patterns, decision trees, wizard pattern | Phase 2 (design) — skills with user interviews |
| `references/task-management-patterns.md` | TaskCreate/TaskUpdate instruction patterns for multi-step components | Phase 2 (design) — skills/agents with 3+ step workflows |
| `references/anti-patterns.md` | Token-wasting, activation, structure, content, and tool-scoping anti-patterns | Phase 2 (design) and Phase 4 (improve) |
| `references/advanced-patterns.md` | Production patterns, skill archetypes, specialized skill designs | Phase 2 (design) and Phase 4 (improve) |
| `references/complex-skills-patterns.md` | Error handling, tool scoping, validation scripts, security review | Phase 2 (design) — complex skills |
| `../../references/pdk-allowed-tools.md` | Tool scoping validation, principle of least privilege | Phase 2 (design) — tool scoping |
| `../../references/pdk-design-patterns.md` | Gotchas patterns, progressive disclosure, hooks, setup, composability | Phase 2 (design) |
| `references/self-containment-principle.md` | External dependency architecture and guidance | Phase 2 (design) — external dependencies |
| `references/secrets-and-credentials.md` | Secrets detection, git safety, env-var patterns, testing | Phase 2 (design) — skills with credentials |
| `../../references/pdk-size-limits.md` | Strict size limits reference | Phase 2 (design) |
| `references/tessl-best-practices.md` | Tessl-style Activation/Implementation standards | Phase 2 and Phase 5 |

### Phase 3–5: Test, Improve & Polish

| File | Purpose | When to Read |
|---|---|---|
| `references/schemas.md` | JSON schemas for evals, grading, benchmark, comparison | Phase 3 (test) |
| `references/eval-writing-guide.md` | How to write good assertions | Phase 3 (test) |
| `references/eval-workflow.md` | Step-by-step eval workflow reference | Phase 3 (test) |
| `references/benchmark.md` | Eval-driven scorecard and iteration table | Phase 3–4 (measure quality) |
| `../../references/pdk-compliance-testing.md` | TDD compliance testing: pressure scenarios, rationalization tables, meta-testing protocol | Phase 3.5 — after quantitative evals |
| `references/testing.md` | Trigger rate, eval set schema, regression guide | Phase 3–5 |
| `references/rubric.md` | Tessl-aligned Activation/Implementation grading rubric | Phase 5 (polish) |
| `references/troubleshooting-guide.md` | Doesn't trigger, triggers too often, instructions not followed, large context, frontmatter errors | Phase 5 (polish) and debugging |
| `references/checklist.md` | Comprehensive pre-release validation across all dimensions | Phase 5 (polish) — before packaging |
| `agents/grader.md` | Evaluate assertions against outputs | Phase 3 (test) |
| `agents/comparator.md` | Blind A/B comparison between two outputs | Phase 4 (improve) |
| `agents/analyzer.md` | Analyze benchmark patterns and comparison results | Phase 3–4 |
| `scripts/aggregate_benchmark.py` | Aggregate benchmark results across iterations | Phase 3 step 5 (invoked as `python ${CLAUDE_SKILL_DIR}/scripts/aggregate_benchmark.py`) |
| `scripts/run_loop.py` | Run description optimization loop | Phase 5 (polish) |
| `scripts/quick_validate.py` | Quick skill validation check | Phase 5 (before packaging) |
| `scripts/package_skill.py` | Package skill into distributable `.skill` file | Phase 5 (packaging) |
| `scripts/init_skill.py` | Scaffold template directory for standalone (non-plugin) skills | Phase 1 (Greenfield — non-plugin only) |
| `scripts/repair_skill.py` | Diagnose and repair skill loading failures | Skill Repair section |
| `scripts/scan_skills.py` | Inventory all skills with metadata and usage statistics | Skill Consolidation step 1 |
| `scripts/analyze_similarity.py` | Find merge candidates by trigger/keyword overlap | Skill Consolidation step 2 |
| `scripts/smoke_test.py` | This skill's own persisted smoke test (frontmatter validity, referenced-file existence, Bash-scope grant consistency) | Before packaging / after any SKILL.md edit |
| `scripts/run_eval.py` | Trigger evaluation for a skill description: does a query make Claude read the skill (JSON output) | Phase 5 — invoked by `run_loop.py`, not directly |
| `scripts/improve_description.py` | Propose an improved description from eval results via `claude -p` | Phase 5 — invoked by `run_loop.py`, not directly |
| `scripts/generate_report.py` | HTML report of each description attempt from `run_loop.py` output | Phase 5 — invoked by `run_loop.py`, not directly |
| `scripts/utils.py` | Shared helpers (e.g. `parse_skill_md`) for the scripts above | Internal dependency |
| `eval-viewer/generate_review.py` | Build the eval viewer (Outputs and Benchmark tabs; `--static` for a standalone HTML file) | Phase 3 step 6 (review outputs) |
| `eval-viewer/viewer.html` | The viewer's page template, filled in by `generate_review.py` | Internal dependency |
| `assets/eval_review.html` | Page for reviewing and exporting the trigger eval set (`eval_set.json`) | Phase 5 (description optimization) |
| `assets/skill-template-basic.md` | Basic SKILL.md starter template | Phase 1 (Greenfield) and Phase 2 (design) — scaffold |
| `assets/skill-template-complex-body.md` | Starter body for a complex skill | Phase 2 (design) — complex skills |
| `assets/reference-file-template.md` | Starter for a `references/` file | Phase 2 (design) — content placement |
| `plugin-rulebook` skill | Plugin-level rules — invoke before finalizing to check naming, language, formatting, tool-scoping, and external-reference compliance | Phase 5 (before packaging) |
| `CHANGELOG.md` | Change history for this skill | Reference |
