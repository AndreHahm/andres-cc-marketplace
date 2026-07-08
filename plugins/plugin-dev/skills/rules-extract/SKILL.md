---
name: rules-extract
description: >-
  Extract project-specific coding rules and domain knowledge from an existing codebase,
  generating structured markdown for AI agents. Use when onboarding a new project,
  after code review discussions about coding style, after sessions where preferences
  were corrected (--from-conversation), after PRs with significant review feedback
  (--from-pr), when rule files exceed 40k chars (--compact), or when the project
  structure has evolved and rules need reorganization (--restructure).
allowed-tools: Read Glob Grep Write Edit Agent TodoWrite Bash(git:*) Bash(gh:*) Bash(ls:*) Bash(pwd:*) Bash(node:*)
---

# Extract Rules

Analyzes existing codebase to identify what Claude would get wrong without project-specific guidance, extracting coding rules and domain knowledge as structured markdown documentation for AI agents.

## Quick Start

| Mode | Command | When |
|------|---------|------|
| Full extraction | `/rules-extract` | New project — no `.claude/rules/` yet |
| Update | `/rules-extract --update` | Re-scan and add new patterns (preserves existing) |
| Restructure | `/rules-extract --restructure` | Project evolved, new frameworks, or `split_output` changed |
| Conversation | `/rules-extract --from-conversation` | Extract from current or recent session |
| Compaction | `/rules-extract --compact` | Rules file exceeded 40k chars |
| PR Review | `/rules-extract --from-pr 123` | Extract from PR review comments |

**Typical first run:**
1. Optionally create `.claude/rules-extract.local.md` with `output_dir`, `language`, `split_output`
2. Run `/rules-extract` — detects stack, samples files, writes rule files
3. Review generated files in `output_dir` (default `.claude/rules/`)
4. Run `/rules-extract --update` after significant codebase changes or conversations

## When to Use

- Onboarding a new project with no `.claude/rules/` yet
- After code review sessions where coding preferences were corrected
- After PRs with significant reviewer feedback on style or conventions
- When `.claude/rules/` files have grown past 40k chars (`--compact`)
- After the codebase adds a new framework or architectural layer (`--update` or `--restructure`)
- When `split_output` setting changes and files need format migration (`--restructure`)

## When NOT to Use

- Creating a rule from a single observation → use `rule-development` instead
- Merging rules across multiple org projects → use `rules-merge` instead
- Applying org rules to the current project → use `rules-apply` instead
- Reviewing rule compliance against a diff → use `/rules-review` instead

## Usage

```text
/rules-extract                      # Extract rules from codebase (initial)
/rules-extract --update             # Re-scan and add new patterns (preserve existing)
/rules-extract --restructure        # Re-analyze, reorganize structure, merge existing rules
/rules-extract --from-conversation              # Extract from current session (latest)
/rules-extract --from-conversation <session-id> # Extract from a specific session
/rules-extract --from-pr 123                   # PR in current repo
/rules-extract --from-pr owner/repo#123        # PR in another repo (URL form also accepted)
/rules-extract --from-pr 100..110              # PR range (space-separate multiple specs for cross-analysis)
/rules-extract --compact                       # Compact all over-threshold rules files (output_dir/**/*.md)
/rules-extract --compact path/to/file.md ...   # Compact specific files
```

## Configuration

Settings file: `rules-extract.local.md` (YAML frontmatter only, no markdown body)
- Project-level: `.claude/rules-extract.local.md` (takes precedence)
- User-level: `~/.claude/rules-extract.local.md`

| Setting | Default | Description |
|---------|---------|-------------|
| `target_dirs` | `["."]` | Analysis target directories |
| `exclude_dirs` | `[".git", ".claude"]` | Exclude directories (in addition to .gitignore) |
| `exclude_patterns` | `[]` | Exclude file patterns (e.g., `*.generated.ts`, `*.d.ts`) |
| `output_dir` | `.claude/rules` | Output directory for rule files (`.md` and `.local.md`). Inside Claude Code's `.claude/rules/**` recursive auto-load scope — every file written here is injected into context on session start |
| `examples_output_dir` | `.claude/rules-extras` | Output directory for `.examples.md` files. Defaults to a sibling directory outside `.claude/rules/**` auto-load scope. Set to `output_dir` to opt examples into auto-load |
| `staging_output_dir` | `.claude/rules-staging` | Staging directory for 1st-observation project-level candidates from incremental modes; 2nd-observation matches are promoted to canonical. See `references/output-structure.md` § Configuration Details |
| `language` | `en` | Report language (e.g., `en`, `ja`) |
| `split_output` | `true` | Separate Principles (.md) and patterns (.local.md) |
| `resolve_references` | `true` | Resolve file references during restructure |
| `compaction_threshold` | `40000` | Char count threshold for `--compact` mode; files above this value are compacted. Default `40000` matches Claude Code's per-file warning. See `references/output-structure.md` § Configuration Details |
| `min_cluster_size` | `3` | Minimum bullet cluster size for consolidation detection in `--compact` mode. See `references/output-structure.md` § Configuration Details |

See `references/output-structure.md` § Configuration YAML for a full example with all settings.

## Output Structure

Three output directories: `output_dir` (rule files — inside `.claude/rules/**` auto-load scope), `examples_output_dir` (`.examples.md` files — outside auto-load by default), `staging_output_dir` (1st-observation project-level candidates from incremental modes). The `paths:` frontmatter on rule files is a human-facing scope hint; auto-load is determined by directory placement only.

See `references/output-structure.md` for directory tree diagrams (default, hybrid, integration libraries), YAML config example, and rule file format.

## Shared Reference Files

Pre-load these files before executing any mode procedure — they are referenced throughout the mode reference files:

| File | Used for |
|---|---|
| `references/extraction-criteria.md` | Pattern classification criteria (what to extract vs. skip) |
| `references/security.md` | Security self-check patterns (run after every generation step) |
| `references/examples-format.md` | `.examples.md` file structure and generation procedure |
| `references/report-templates.md` | Report format for all modes |

## Processing Flow

### Mode Detection

Check arguments to determine mode:

- No arguments → **Full Extraction Mode**
- `--update` → **Update Mode**
- `--restructure` → **Restructure Mode**
- `--from-conversation [session-id]` → **Conversation Extraction Mode**
- `--compact [<paths>]` → **Compaction Mode**
- `--from-pr <number|owner/repo#number|range> [...]` → **PR Review Extraction Mode**

---

## Full Extraction Mode

Load settings, detect project type, collect sample files, analyze by category (using pre-loaded `extraction-criteria.md`), analyze documentation and deduplicate against existing rules, generate output per `split_output` mode with security self-check, and report.

Read `references/full-extraction-mode.md` for the complete procedure (Steps 1–7).

---

## Update Mode

When `--update` is specified, re-scan the codebase and add new patterns while preserving existing rules.

**Staging awareness**: Update Mode reads the staging file under `staging_output_dir` (when present) and promotes any staged project-level patterns that re-match against fresh code observations to canonical (`<output_dir>/project.md`), removing them from staging. Update Mode does **not** write new entries to staging — un-matched new patterns land directly in canonical. See `references/conversation-mode.md` § Mode interaction summary for the full per-mode staging behavior.

**Operational note**: After a dependency's major-version bump, run `--update` so the Step U3 staleness check flags removed symbols. The check only scans inline `` `symbol` `` in `.local.md`'s `## Project-specific patterns` — `.examples.md` is not auto-scanned. `--restructure` is not a substitute here: it reorganizes files without running the staleness check.

Read `references/update-mode.md` for the complete procedure (Steps U1–U6).

---

## Restructure Mode

When `--restructure` is specified, re-analyze the codebase to determine the optimal file structure, then merge existing rule content into the new structure. Use when the project has evolved (new frameworks, architectural changes), when `split_output` settings change, or after updating the rules-extract skill itself.

**Note**: Restructure Mode does NOT run the staleness check — use `--update` first so stale symbols are flagged for manual review.

Read `references/restructure-mode.md` for the complete procedure (Steps R1–R5).

---

## Conversation Extraction Mode

When `--from-conversation` is specified, extract rules from the full conversation history stored in session `.jsonl` files. The heavy processing (jsonl parsing, analysis, rule writing) is delegated to a subagent to keep the main context clean.

### Step C1: Prepare and Locate Session File (main agent)

1. Load settings from `rules-extract.local.md` (same as Step 1 in `references/full-extraction-mode.md`)

2. Check if output directory exists (default: `.claude/rules/`)
   - If not exists: Error "Run /rules-extract first to initialize rule files."

3. **Locate the session file:**

   1. Get the current working directory (`pwd`)
   2. Encode the path: replace `/` and `.` with `-` (leading `-` is kept)
      - Example: `/Users/hiropon/Sources/github.com/myproject` → `-Users-hiropon-Sources-github-com-myproject`
   3. Session files are stored at: `~/.claude/projects/<encoded-path>/<session-id>.jsonl`

4. **Select the target session:**

   - If a `<session-id>` argument is provided: use `~/.claude/projects/<encoded-path>/<session-id>.jsonl`
   - If no argument: use the most recently modified `.jsonl` file in the directory (by `ls -t`)
   - Verify the file exists. Inform the user which session file was selected.

### Step C2: Delegate to Subagent (main agent)

Spawn a subagent using the Agent tool. The subagent performs all heavy processing (C3–C5) and returns a summary of what was added. Read `references/conversation-mode.md` for the full subagent instructions (Steps C3–C5).

Include in the agent prompt:
- This skill's absolute directory path (where SKILL.md resides — needed to run bundled scripts)
- Session file absolute path
- `output_dir`, `examples_output_dir`, and `staging_output_dir` paths, plus `split_output` / `language` settings
- `canonical_files`: list of existing rule file paths for canonical-match deduplication — include both rule files under `output_dir` and `.examples.md` files under `examples_output_dir`
- `staging_files`: list of existing staging file paths for staging-match detection — include the project-level staging file under `staging_output_dir`
- The subagent instructions from `references/conversation-mode.md`
- Contents of `references/extraction-criteria.md` (Step C4 uses for classification criteria)
- Contents of `references/security.md` (Step C5 item 7 security self-check)
- Contents of `references/examples-format.md` (Step C5 item 6 examples generation)
- Contents of `references/report-templates.md` (Step C5 item 8 summary format)

After the subagent completes, report the results to the user.

---

## Compaction Mode

When `--compact` is specified, compact over-threshold rules files. Target file selection, char-count check, and threshold filtering all happen inside this mode — callers (e.g. `dev-workflow` Step 11) invoke `--compact` without file arguments.

Uses the Pattern A iteration loop: main thread resolves targets → subagent analyzes → main thread applies `mechanical_edits` → fenced JSON return contract for caller dispatch. Per-file outer loop with `max_iterations = 2` (default).

Read `references/compaction-orchestration.md` for the full orchestration steps: CP1 (load settings + resolve targets), CP2 (per-file iteration loop: dispatch, parse, apply, converge), CP3 (security self-check), CP4 (structured JSON output schema), CP5 (sub-skill caller directive). For subagent heuristics and contract, see `references/compaction-mode.md`.

---

## PR Review Extraction Mode

When `--from-pr` is specified, extract rules from PR review comments (human comments only).
Single or multiple PRs can be specified. Numbers and URLs can be mixed. Cross-repository PRs are allowed.

Read `references/pr-review-mode.md` for the full processing steps (P1-P5). Key flow:
1. Check prerequisites (`gh` CLI authentication)
2. Parse all PR arguments, validate each PR exists
3. Fetch review comments from GitHub API (3 endpoints per PR), filter bot comments
4. Extract principles and patterns (per pre-loaded `extraction-criteria.md`)
5. **Multiple PRs**: Cross-PR frequency analysis — general best practices that are repeatedly pointed out across different PRs are promoted as organizational emphasis
6. Append to existing rule files and update `.examples.md` (same as Step C5)

---

## Testing & Validation

After running rules-extract:

1. **Output present** — `output_dir` (default `.claude/rules/`) contains files matching the detected stack
2. **Split format** — with `split_output: true`: `.md` has `## Principles` only, `.local.md` has `## Project-specific patterns` only
3. **Security** — no tokens, secrets, or internal URLs in generated files (Step 6.5 passed)
4. **No stale symbols** — Step U3 (Update Mode) flags symbols no longer in codebase; review before accepting
5. **Deduplication** — patterns already in existing rule files are not re-added

**Quality gates:**
- [ ] Each detected language/framework has a corresponding rule file in `output_dir`
- [ ] `paths:` frontmatter present on all rule files (except `project.md`)
- [ ] `.examples.md` files written to `examples_output_dir` (outside auto-load scope by default)
- [ ] No patterns duplicated between `.md` and `.local.md` sibling files
- [ ] `/rules-review` fires on known violations from the extracted rules

---

## Reference Guide

| Resource | Purpose |
|---|---|
| `references/extraction-criteria.md` | Classification criteria — what to extract vs. skip |
| `references/integration-criteria.md` | Detection rules and output routing for integration libraries |
| `references/security.md` | Security self-check patterns — run after every generation step |
| `references/examples-format.md` | `.examples.md` file structure, Good/Bad guidelines, reference section format |
| `references/report-templates.md` | Report format for all modes |
| `references/output-structure.md` | Directory tree diagrams, YAML config example, rule file format |
| `references/full-extraction-mode.md` | Complete procedure for Full Extraction Mode (Steps 1–7) |
| `references/update-mode.md` | Complete procedure for Update Mode (Steps U1–U6) |
| `references/restructure-mode.md` | Complete procedure for Restructure Mode (Steps R1–R5) |
| `references/conversation-mode.md` | Subagent instructions for Steps C3–C5 (Conversation Extraction) |
| `references/pr-review-mode.md` | Full processing steps P1–P5 (PR Review Extraction) |
| `references/compaction-mode.md` | Subagent instructions and heuristics for Compaction Mode |
| `references/compaction-orchestration.md` | Main-thread orchestration for Compaction Mode (CP1–CP5) |
| `references/resolve-references.md` | Reference resolution processing steps (Restructure Mode R2.5) |
| `scripts/extract_session_messages.mjs` | Node.js script for parsing session `.jsonl` files (Conversation Mode) |

---

## Sub-skill caller directive

When invoked as a sub-skill (i.e. via `Skill(rules-extract)` from an orchestrator such as `dev-workflow` Step 11), the fenced JSON verdict block this skill emits in `--compact` mode is the **structured return value** of the skill's procedure — it is **not** a deliverable to the user, and emitting it does **not** terminate the orchestrator's turn. The same agent that ran this skill must immediately issue the next tool call dictated by the orchestrator's flow. Do not insert a prose summary, an acknowledgment, or a "shall I proceed?" sentence between the JSON verdict and the next tool call. Only one fenced JSON block — the verdict block — appears in the response, so callers can locate it unambiguously.

This directive applies specifically to `--compact` mode. Other modes produce prose reports rather than fenced JSON verdicts and are not subject to this contract.

**Stop hook note:** If a Stop hook fires mid-dispatch, ignore it and continue — per-file boundaries are the canonical completion signal.
