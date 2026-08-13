---
name: plugin-rulebook
description: >-
  Defines and enforces plugin-level rules governing all components (skills, agents, commands,
  hooks, rules) in a Claude Code plugin. Use when creating, validating, or refining any plugin
  component, checking naming conventions and R1-R27 formatting compliance, auditing a full plugin, or loading active
  rule configuration, or before finalizing or packaging any plugin component. Governs naming, language, formatting,
  tool-scoping, and structure across the entire plugin.
allowed-tools: Read Glob Bash(*/r20-sweep.sh:*) Bash(*/agent-cost-tracker.py:*)
---

# Plugin Rulebook

Read active settings from `${CLAUDE_SKILL_DIR}/assets/settings.json` (plugin-portable defaults), then merge any repo-specific overrides from `{REPO_ROOT}/.claude/plugin-rulebook.config.json` (if present), then check the target component against all enabled rules.

## Quick Start

1. **Read settings** — `${CLAUDE_SKILL_DIR}/assets/settings.json` on every invocation; always re-read, even if settings were loaded earlier in the same session. Then check `{REPO_ROOT}/.claude/plugin-rulebook.config.json` — if it exists, its values override the plugin defaults for the specific keys it sets (currently only R23's `whitelist`/`blacklist`/`excluded_paths`); if absent, proceed with the plugin's own defaults (empty lists — everything classifies as Unknown rather than inheriting another repo's policy). See R23's section below and `references/external-reference-policy.md` for the full merge procedure.
2. **Identify target** — component type: skill / agent / command / hook / rule
3. **Run checks** — apply each enabled rule to the component's files
4. **Emit report** — compliance report with PASS / ADVISORY / FAIL per rule (see Compliance Check Procedure)
5. **Periodic review** — independent of single-component checks, periodically audit all instruction layers together — CLAUDE.md, nested CLAUDE.md files, `.claude/rules/`, skills, agents, and hooks — for conflicts, drift, and duplicated instructions

## When to Use

- Before finalizing any new plugin component
- When validating or refining existing plugin components
- When another plugin-devkit skill requests rulebook compliance via Skill tool
- When auditing an entire plugin for consistency

## When NOT to Use

- Project-specific behavioral rules → use `rule-development` instead
- Skill quality metrics (token efficiency, trigger phrases) → use `skill-reviewer` instead
- Security threat analysis → use `skill-security` instead
- Script/code correctness (missing file encodings, shell logic bugs, mojibake corruption, YAML parsing gaps) → use `scripts-reviewer` instead. R1–R27 check structure, naming, formatting, and frontmatter only — a PASS here makes no claim about whether a component's scripts actually run correctly. This is not a hypothetical caveat: a 3-command pipeline once passed this exact check cleanly while shipping 2 real functional bugs (a multi-line-command normalization bug and a session-selection logic bug), both caught only by later running it against real data — see `plugin-lifecycle-upstream`'s Phase 5 command-component live-trial check, added for this reason.
- Dedicated wide-surface language-compliance review (scripts, config JSON, CLAUDE.md/README, beyond R1's own file scope) → use `language-reviewer` instead.
- A combined Validate+Audit+Report+Fix pipeline across a whole plugin, not just rule compliance in isolation → use `plugin-lifecycle-downstream` instead

**Note:** This skill's manual invocation model complements, but does not replace, automated live validation hooks. For production plugins, use both — manual rulebook checks during development and live enforcement hooks at commit or PR time.

## Active Rules

Rules are enabled/disabled in `${CLAUDE_SKILL_DIR}/assets/settings.json`. Defaults shown in brackets.

**Note on "command" as a scope category:** current platform docs describe `commands/*.md` as a legacy flat-file skill format ("custom commands have been merged into skills") and recommend `skills/` for new plugin components. This rulebook continues to check "command files" as their own scope category below because plugin-devkit's own plugin currently ships 16 components under `commands/` that depend on this convention — new components should prefer `skills/`.

**Severity vocabulary:** `REQUIRED` and `SUGGESTED` (used throughout this rulebook) correspond to [RFC 2119](https://datatracker.ietf.org/doc/html/rfc2119)'s `MUST`/`MUST NOT` and `SHOULD`/`SHOULD NOT` requirement levels respectively — a `REQUIRED` finding is a blocking violation, a `SUGGESTED` finding is a recommended fix a maintainer may have valid reasons to decline. `ADVISORY` (used for some sub-checks, e.g. R5's agent-field check) is this rulebook's own tier, sitting below `SUGGESTED`: worth flagging, never blocking, and not itself an RFC 2119 term.

---

### R1 — Language: English Only [REQUIRED, default: on]

All frontmatter fields and body content must be in English.

**Scope:** SKILL.md, agent files, command files, hook config, rule files, all `references/*.md`

**Violations:**
- Non-English text in `name`, `description`, or any other frontmatter field
- Non-English headings, prose, or procedural instructions in body content
- Non-English code comments (exception: user-facing output strings in locale-specific context)

**Fix:** Translate to English. For multilingual audiences, add a language variant file (R3).

---

### R2 — Reference Files: English Primary Required [REQUIRED, default: on]

Every file in `references/` must have an English version as the primary file.

**Primary file:** `references/<topic>.md` — always English, always required
**Scope:** All `references/` directories in any plugin component

**Violation:** A reference file exists only as a language variant (e.g., `references/guide.de.md`) with no English `references/guide.md`.

**Fix:** Create `references/<topic>.md` in English before adding any language variants.

---

### R3 — Reference Files: Optional Multilingual Variants [OPTIONAL, default: on]

Reference files may have additional language-specific variants alongside the English primary.

**Naming:** `references/<topic>.<lang-code>.md`
**Valid lang codes:** Per `settings.json → languages.additional` (default: `de`, `zh`, `fr`, `es`, `ja`, `pt`)

**Examples:**
- `references/patterns.md` — English (primary, required)
- `references/patterns.de.md` — German (optional)
- `references/patterns.zh.md` — Chinese (optional)

**Rule:** Variants must cover the same content as the English primary. English is authoritative.

---

### R4 — Naming: Kebab-Case Only [REQUIRED, default: on]

All component identifiers use lowercase kebab-case.

**Scope:** `name` field in all frontmatter; directory names; reference file names (excluding lang-code suffix)
**Pattern:** `^[a-z][a-z0-9-]+[a-z0-9]$` — min 3 chars, max per `settings.json → naming.max_length` (default: 64)
**Forbidden in `name` field:** words `anthropic`, `claude`

**Violations:** `skillDev` (camelCase), `skill_dev` (underscore), `Skill-Dev` (uppercase)

---

### R5 — Frontmatter: No Non-Standard Fields [REQUIRED, default: on]

Skill and agent frontmatter must not include command-only or unsupported fields.

**Forbidden in SKILL.md and agent files:**
- `version` — command-only field

**Allowed in skill and command files:** `argument-hint` — officially supported skill frontmatter field, also valid on commands
**Allowed in command files only:** `version`

**Non-functional in agent files (ADVISORY, not REQUIRED):** `hooks`, `mcpServers`, `permissionMode` are accepted by the schema on plugin-scoped agents but not honored — an upstream security restriction. Flag as ADVISORY when present in an agent file: the field doesn't break validation, it silently does nothing. Configurable via `settings.json → rules.R5_frontmatter_no_nonstandard_fields.config.agent_nonfunctional_fields`. **`AskUserQuestion` in `allowed-tools` (ADVISORY, not REQUIRED — corrected 2026-07-27):** listing it is a harmless no-op, not a schema violation — every tool remains callable regardless of `allowed-tools`. Flag as ADVISORY ("redundant, no effect"), never REQUIRED. See `${CLAUDE_SKILL_DIR}/references/frontmatter-corrections.md` for the full verification and reasoning behind the `AskUserQuestion` correction.

---

### R6 — Tool Scoping: Least Privilege [REQUIRED, default: on]

`allowed-tools` may be space-separated, comma-separated, or a YAML list. Space-separated is the preferred internal style. Apply principle of least privilege regardless of format.

**Preferred:** `allowed-tools: Read Edit Write Glob`
**Also valid:** `allowed-tools: Read,Edit,Write,Glob` (comma-separated), or a YAML list
**Wrong:** `allowed-tools: Bash(*)` (overly broad) or bare `allowed-tools: Bash` (no scope argument at all — equally unrestricted)

**Bash scoping:** Always scope to a named tool — `Bash(git:*)`, `Bash(python:*)` — never `Bash(*)` or bare `Bash`. Shell interpreters (`sh`, `bash`, `cmd`, `powershell`) are equivalent to `Bash(*)` and are REQUIRED violations regardless of argument pattern. See `${CLAUDE_SKILL_DIR}/references/frontmatter-corrections.md` for the full scope/verdict table.

**Tool completeness:** Every tool invoked in the command or skill body must be declared in `allowed-tools`. Scan the body for tool name references (`Bash`, `Write`, `Edit`, `Glob`, `Grep`, `Read`, `WebFetch`, `WebSearch`, etc.) — any tool called but absent from `allowed-tools` is a REQUIRED violation. **Agent files — the Bash-scoping rule above does not apply the same way:** an agent's `tools` field has no documented Bash-scoping syntax at all. A `Bash(cmd:*)`-style entry there is a FAIL in the opposite direction — replace with bare `Bash`, never tighten the scope further. Flag as REQUIRED. See `${CLAUDE_SKILL_DIR}/references/frontmatter-corrections.md` for the full reasoning.

**Violation:** Body instructs Claude to run a shell command (Bash) but `Bash(...)` is absent from `allowed-tools`.

---

### R7 — Formatting: No Emoji in Structural Elements [SUGGESTED, default: on]

Emoji must not appear in section headings, frontmatter fields, or procedural step labels.

**Allowed:** Emoji in sample output, user-facing strings, or illustrative examples
**Forbidden:** `## 🚀 Quick Start`, `- ✅ Step 1:` as primary structural label

*Disable in `settings.json → rules.R7_no_emoji_in_structure.enabled: false` if preferred.*

---

### R8 — Frontmatter: Multiline Description Syntax [REQUIRED, default: on]

Descriptions over 80 characters must use `>-` YAML block scalar syntax.

**Correct:**
```yaml
description: >-
  Defines and enforces plugin-level rules across all components.
```
**Wrong:** `description: "Defines and enforces plugin-level rules across all components in a plugin."`

**Command description length (ADVISORY, command files only):** The `description` field is shown in `/help` and truncated beyond 60 characters. For command files, emit an ADVISORY finding when `description` is 61–80 characters. Descriptions over 80 characters are already a REQUIRED violation per the check above.

---

### R9 — Security: No Hardcoded Credentials [REQUIRED, default: on]

No API keys, tokens, passwords, or secrets in any plugin file.

**Scope:** All files including scripts, assets, and config files
**Exception:** Placeholder values in examples only — `YOUR_API_KEY_HERE`, `$API_KEY`

---

### R10 — Reference File Naming: Descriptive and Specific [REQUIRED, default: on]

Reference files use lowercase, hyphen-separated, descriptive topic names.

**Rules:**
- Max 40 chars for topic portion (before any lang-code suffix)
- No generic names: `reference.md`, `guide.md`, `config.md`, `docs.md`, `info.md`
- No abbreviations unless universally recognized: `api`, `mcp`, `ui`, `ux`, `url`

**Good:** `validation-checklist.md`, `allowed-tools.md`, `movement-pattern.md`
**Bad:** `ref.md`, `guide.md`, `stuff.md`, `misc.md`

---

### R13 — SKILL.md Line Count: Tiered Severity [REQUIRED, default: on]

Enforce quality thresholds on SKILL.md total line count using four severity tiers.

**Thresholds** (configurable in `assets/settings.json → rules.R13_skillmd_line_limit.config.thresholds`):

| Lines | Severity | Required Action |
|-------|----------|-----------------|
| ≤ 100 | OK | None |
| > 100 | Weak Warning | Record as informational; no fix required |
| > 300 | Soft Warning | Recommend planning extraction soon; do not block |
| > 490 | Warning | Recommend moving content to `references/`; do not block |
| > 500 | Critical | Must move content to `references/` before proceeding |

See `${CLAUDE_SKILL_DIR}/references/size-rules.md` for the full severity behavior definitions.

---

### R14 — References: One Level Deep [REQUIRED, default: on]

No subdirectories inside `references/` — only `references/<file>.md` is valid.

**Scope:** All `references/` directories in any plugin component

**Violations:**
- `references/advanced/patterns.md` — nested subdirectory
- `references/v2/schema.md` — versioned subdirectory

**Fix:** Move nested files to the top level: `references/advanced-patterns.md`. If content volume demands grouping, extract to a dedicated skill instead.

---

### R17 — Formatting: No Bare URLs [SUGGESTED, default: on]

All hyperlinks must use named reference syntax — text in brackets, URL in parentheses.

**Correct:** `See the [documentation](https://docs.example.com) for details.`
**Wrong:** `See https://docs.example.com for details.`

**Exception:** URLs inside code blocks or as placeholder values in examples are allowed.

*Disable in `settings.json → rules.R17_no_bare_urls.enabled: false` if preferred.*

---

### R18 — Inline Code Block Size: Tiered Severity [REQUIRED, default: on]

Enforce quality thresholds on inline fenced code blocks using three severity tiers.

**Thresholds** (configurable in `assets/settings.json → rules.R18_code_block_line_limit.config.thresholds`):

| Block Lines | Severity | Required Action |
|-------------|----------|-----------------|
| ≤ 10 | OK | None |
| > 10 | Weak Warning | Suggest extracting; no fix required |
| > 20 | Warning | Recommend extracting to `scripts/` or `references/`; do not block |
| > 30 | Critical | Must extract to `scripts/` file and replace with pointer before proceeding |

See `${CLAUDE_SKILL_DIR}/references/size-rules.md` for the full severity behavior definitions and extraction targets.

---

### R19 — Canonical Path Resolution [REQUIRED, default: on]

Before checking a component, resolve its actual absolute file path and verify no duplicate or shadow copy of the same named component exists in another scope.

**Scope:** Any component invoked by name (skill, agent, command, hook, rule) — check project `.claude/skills/`, plugin `plugins/*/skills/` (and equivalent `agents/`, `commands/`, `hooks/`, `.claude/rules/` locations), and user `~/.claude/skills/` for a same-named duplicate.

**Violations:**
- The invoked component name resolves to two or more directories, and their contents differ
- The compliance report does not state the absolute path that was actually checked

**Fix:** Report the resolved absolute path in the compliance report header. If duplicates exist with differing content, FAIL and require the invoker to disambiguate by full path or resync the copies before proceeding.

**Exception — in-development plugin mirrors:** A plugin still under active development may need its components staged into the project's `.claude/` directory so they actually run before the plugin is packaged and installed — removing the `.claude/` copy at this stage would break the very components being developed. Treat this as an intentional, expected duplicate, not a violation: verify the copies are identical (see R20) and note it as PASS/informational, not ADVISORY-to-deduplicate. Do not suggest removing the `.claude/` copy until the plugin has actually been installed (confirmed via `/plugin` or the marketplace) — finishing edits is not the same as installation.

---

### R20 — Duplicate Fact Sweep [REQUIRED, default: on]

When a canonical value changes (enum lists, size thresholds, forbidden-field lists, model or tool names), search the plugin tree for other occurrences of the old value in sibling files and flag any not updated.

**Scope:** SKILL.md prose, prompt/template files, validator scripts, and other skills that duplicate a fact owned by `settings.json` or another canonical source.

**Violations:**
- A `settings.json` value changes (e.g., `agent.color.valid_values`, `agent.permissionMode.valid_values`, R13/R18 thresholds, R5 forbidden-field list) but a sibling file still references the old value
- A quick-reference copy of a fact (e.g., a table in another skill's SKILL.md) goes stale after its source of truth is edited

**Fix:** Grep the plugin directory for the previous value before closing out the change; update every occurrence, or record the divergence as intentional.

---

### R21 — Skill Description Size: Tiered Severity [REQUIRED, default: on]

Enforce quality thresholds on SKILL.md frontmatter `description`, `when_to_use`, and their combined length.

**Scope:** SKILL.md frontmatter only (commands use the separate ≤60/80-char check in R8; agents have no `description` size rule).

**Limits** (configurable in `assets/settings.json → rules.R21_skill_description_size.config.limits`):

| Field | Min | Max |
|---|---|---|
| `description` | 80 | 1024 |
| `when_to_use` | — | 512 |
| combined (`description` + `when_to_use`) | 80 | 1536 |

**Thresholds** (configurable in `assets/settings.json → rules.R21_skill_description_size.config`):

| Metric | Critical | Warning | OK | Warning | Critical |
|---|---|---|---|---|---|
| `description` length | < 20 | 20–79 | 80–1018 | 1019–1024 | > 1024 |
| `when_to_use` length | — | — | ≤ 506 | 507–512 | > 512 |
| combined length | — | — | ≤ 1524 | 1525–1536 | > 1536 |

Overall severity for the component is the most severe tier triggered across the three metrics.

See `${CLAUDE_SKILL_DIR}/references/size-rules.md` for the full severity behavior definitions.

---

### R22 — Argument Frontmatter Consistency: Tiered Severity [REQUIRED, default: on]

Enforce that `argument-hint`/`arguments` frontmatter accurately reflects the argument placeholders (`\$ARGUMENTS`, `\$ARGUMENTS[N]`, `\$0`/`\$1`/..., `$name`) actually consumed in the body.

**Scope:** SKILL.md and command files (`commands/*.md`) — commands and skills share the same frontmatter fields and substitution mechanism.

**Reminder — positional placeholders are 0-based:** `\$0` is the first argument, `\$1` the second, matching `\$ARGUMENTS[0]`/`\$ARGUMENTS[1]`. A file that uses `\$1` to mean "the first argument" is itself off by one — check for this specifically, it's the most common instance of the wrong-position case below.

**Detecting "accepts arguments":** the body contains `\$ARGUMENTS`, `\$ARGUMENTS[N]`, a bare `\$0`/`\$1`/`\$2`/... placeholder not escaped with a backslash, or `$name` for a name declared in `arguments`.

**Severity:**

| Condition | Severity |
|---|---|
| Body accepts arguments (per above), but both `argument-hint` and `arguments` are absent or empty | ⚠️ Warning |
| `argument-hint` or `arguments` is non-empty, and the body consumes a position or name beyond what's declared | ❌ Critical — missing argument |
| `argument-hint` or `arguments` is non-empty, and it declares a slot (bracketed token or name) never referenced anywhere in the body | ❌ Critical — stale/orphaned argument |
| `argument-hint` or `arguments` is non-empty, and the order it declares doesn't match the position the body actually consumes it at | ❌ Critical — wrong argument position |

See `${CLAUDE_SKILL_DIR}/references/argument-consistency.md` for the detection procedure and worked examples.

---

### R23 — External Reference Policy: Whitelist/Blacklist [REQUIRED, default: on]

Every reference to an external company, GitHub organization, marketplace, plugin, skill, or repository — in URLs, plugin/skill names, prose mentions, `mcpServers` configs, or `marketplace.json` entries — must resolve to an explicit whitelist or blacklist classification. This exists to clean up stray external references left behind after adapting components, functionality, or behavior from another plugin, marketplace, or repository (e.g. importing a pattern from a plugin like `acme-tools`) — the kind of reference that's fine to keep intentionally, but easy to forget and never revisit.

**Scope (as checked by `plugin-rulebook` directly):** SKILL.md, agent files, command files, hook config, rule files, and all files in `references/`/`scripts/`/`examples/`/`workflows/` — the same component scope as R1. `CLAUDE.md`/`AGENTS.md`/`README.md`/`CONTRIBUTING.md` are **not** in `plugin-rulebook`'s own scope, consistent with `claudemd-reviewer`'s documented exception. The dedicated `external-references-reviewer` agent deliberately extends this same R23 classification to that wider file surface (mirroring how `language-reviewer` extends R1–R3) — that extension lives in the agent, not in this rule's default scope.

**Classification** (configurable in `assets/settings.json → rules.R23_external_reference_policy.config`, merged with the repo-specific override file — `config.whitelist`/`config.blacklist`/`config.excluded_paths` are inherently repo-specific and ship empty by default, see "Repo-Specific Configuration" below):

| Classification | Meaning | Severity |
|---|---|---|
| **Whitelisted** | Matches `config.whitelist`, or a plugin explicitly listed in a `marketplace.json` found in the repo | OK — no finding |
| **Blacklisted** | Matches `config.blacklist` | ❌ Critical — must be removed or replaced before proceeding |
| **Unknown** | Matches neither list | ⚠️ Advisory — flag for the maintainer to explicitly whitelist or blacklist, not a blocking defect by itself |
| **Broken** | A referenced URL, repo, plugin, or skill name that doesn't resolve to anything that exists | ❌ Critical — distinct from classification; a stale or invalid reference is a correctness defect regardless of whitelist/blacklist status |

Marketplace auto-allow, excluded-path handling, the illustrative-example exception, whitelist/blacklist entry-format examples, and the full matching procedure: `${CLAUDE_SKILL_DIR}/references/external-reference-policy.md`.

---

### R24 — Allowed Programming Languages: Python, Bash, JavaScript/TypeScript Only [REQUIRED, default: on]

Only Python, Bash, and JavaScript/TypeScript may be used as programming/scripting languages anywhere in the plugin. The whitelist is closed: any language not on it is banned by default-deny, not just the languages named explicitly (Ruby is named in `config.banned` for visibility, even though the closed whitelist already implies the same rejection).

**Scope:** Standalone script files in any `scripts/` directory, and fenced code blocks in SKILL.md, agent files, command files, hook config, rule files, `references/`, `examples/`, and `workflows/` tagged with a general-purpose programming/scripting language identifier.

See `${CLAUDE_SKILL_DIR}/references/allowed-languages.md` for the full whitelist/banned/exempt lists, worked violation examples, and fix guidance.

---

### R25 — Unplanned-Overhead Disclosure [REQUIRED, default: on]

A skill or pipeline that documents a phase as quick/fast/bounded must disclose to the user, in plain language, whenever actual execution deviated from that documented scope — extra debugging detours, retries, an unplanned fallback — rather than silently absorbing the cost and reporting only a clean final result.

**Scope:** SKILL.md and agent files for any component that documents a quick/fast/bounded step or phase (e.g. a pipeline's Test phase, a "Fast mode," a stated per-phase test-count cap). See `${CLAUDE_SKILL_DIR}/references/overhead-and-cost-rules.md` for violations and fix guidance.

---

### R26 — Expensive-Action Opt-In [REQUIRED, default: on]

A skill or agent that may trigger an expensive action — per-item nested LLM/subprocess calls, a full whole-plugin re-verification, or heavy multi-agent dispatch — must gate that action behind an explicit `AskUserQuestion` decision before running it, rather than defaulting to always running the expensive path.

**Scope:** SKILL.md and agent files that document a step capable of triggering per-item nested LLM/subprocess calls, whole-surface re-scans, or multi-agent dispatch fan-out. See `${CLAUDE_SKILL_DIR}/references/overhead-and-cost-rules.md` for violations and fix guidance.

---

### R27 — Component Naming: Grammatical Form [ADVISORY, default: on]

Skills, agents, and commands should follow their documented grammatical form per `references/naming-conventions.md`'s Component-Type Conventions table — not just valid kebab-case (R4), but the right *shape* of phrase for the component type. Never REQUIRED: this is an interpretive, judgment-based check, not a mechanical pattern match, and a maintainer may have a considered reason to diverge (an established external convention, or the cost of renaming a widely cross-referenced component).

**Scope:** `name` field in SKILL.md frontmatter, `name` field in agent file frontmatter, and command file basenames (commands have no `name` field — check the filename itself).

**Expected form per type:**
- Skill: a noun or gerund phrase naming a domain/capability (`skill-development`, `plugin-rulebook`, `bootstrapping-a-python-project`) — not a bare imperative verb phrase.
- Agent: a role-based noun phrase (`skill-reviewer`, `plugin-validator`) — not a bare imperative verb phrase.
- Command: starts with a verb (`create-plugin`, `review-rules`).

**Violations (ADVISORY only):**
- A skill named as a bare imperative verb phrase with no noun/gerund framing (e.g. a skill named `create-pr` reads as a command's action, not a skill's domain).
- An agent named without role-noun framing.
- A command that doesn't start with a recognizable verb.

**Fix:** Rename to match the documented form, or reconsider the component type (a bare-imperative-named skill may actually want to be a command). Flag and move on if the maintainer declines — this rule exists to surface the mismatch, not to force a rename.

---

## Repo-Specific Configuration

Two files hold data that's specific to the repository this plugin is installed in, rather than portable plugin defaults: `{REPO_ROOT}/.claude/plugin-rulebook.config.json` (R23's `whitelist`/`blacklist`/`excluded_paths`) and `{REPO_ROOT}/.claude/plugin-rulebook-audit-decisions.md` (this repo's Upstream Audit decision log). See `references/repo-specific-configuration.md` for the load procedure and why these aren't `.claude/plugin-rulebook.local.md`-style personal files.

---

## Suggested Additional Rules

Four rules (R11, R12, R15, R16) exist but are disabled by default. See `${CLAUDE_SKILL_DIR}/references/suggested-additional-rules.md` for the full list and why each might be worth enabling.

---

## Compliance Check Procedure

1. Resolve the canonical absolute path of the target component (R19). If the component name resolves to more than one directory (project, plugin, or user skill locations), compare contents — if they differ, halt and report a FAIL before continuing
2. Before finalizing any component, verify the current official Claude Code specification; treat current docs as authoritative over rulebook-cached thresholds if they differ
3. Read `${CLAUDE_SKILL_DIR}/assets/settings.json` — load enabled rules and configuration values. Then check `{REPO_ROOT}/.claude/plugin-rulebook.config.json`; if present, merge its R23 `whitelist`/`blacklist`/`excluded_paths` on top per "Repo-Specific Configuration" above
4. List all files in the target component directory (Glob)
5. For each enabled rule, check all applicable files
6. Classify each finding:
   - **REQUIRED** → blocking violation (must fix before deployment)
   - **SUGGESTED** → advisory violation (recommended fix)
   - **R13/R18 verification method:** count SKILL.md lines and every fenced code block's lines mechanically (a script-based scan of the actual file, not visual sampling) — see `references/size-rules.md`'s "How to Apply" step 3 for why sampling misses violations, especially blocks containing a nested inner fence
   - **R18 consolidation:** when 3 or more code blocks exceed the 10-line weak-warning threshold, emit a single consolidated ADVISORY — "N blocks exceed 10 lines; consider extracting the largest (M lines) to `references/` or `scripts/`" — rather than one entry per block
   - **R20 sweep:** when a rule change touches a canonical enum/threshold/field value, grep sibling files across the plugin tree for the previous value and list each stale occurrence as a separate FAIL
7. Emit compliance report:

```
📋 Rulebook Compliance: <component-name> (<type>)
Path: <resolved-absolute-path> [R19: no duplicates found]
Settings: assets/settings.json [loaded]
Rules checked: N enabled / 27 total

PASS    R1 R2 R4 R5 R6 R8 R9 R10 R14 R19
ADVISORY R7 — emoji in heading "## 🚀 Quick Start" (SKILL.md:14) [SUGGESTED]
FAIL    R3 — references/patterns.de.md exists but references/patterns.md missing [REQUIRED]

Status: FAIL — 1 blocking violation
Scope: structure/naming/formatting/frontmatter only — does not check script or code
correctness (encodings, shell logic, mojibake). Run `scripts-reviewer` separately for that.
```

## Testing & Validation

**Expected triggers** — phrases that should activate this skill:
- "validate this skill for rulebook compliance"
- "audit my plugin component for naming compliance"
- "check R6 tool scoping on this skill"
- "run rulebook compliance before I finalize this agent"
- "does my hook follow the plugin rules?"

**Non-triggers** — phrases that should NOT activate this skill:
- "help me name a variable in Python" → code naming, not plugin naming
- "review my PR for bugs" → use `skill-reviewer` instead
- "check skill quality and token usage" → use `skill-reviewer` instead

**Quality gates:**
- [ ] `${CLAUDE_SKILL_DIR}/assets/settings.json` loads without JSON errors
- [ ] All enabled rules (R1–R10, R13, R14, R17–R27) appear in the compliance report
- [ ] R14 and R17 findings are correctly classified (REQUIRED vs SUGGESTED)
- [ ] PASS / ADVISORY / FAIL emitted for every enabled rule checked
- [ ] Disabled rules (R11, R12, R15, R16) are not checked or reported

## Upstream Source Verification

Whether a rule traces back to an official Claude Code doc, and whether that doc has changed, is tracked by the `upstream-sources-registry` skill — not by this skill. `find-dev-rule`/`verify-dev-rules`/`update-dev-rule` consult that registry and surface any gap through their own classification. See `.claude/rules/plugin-rulebook-enforcement.md`'s "Upstream Source Verification" section for the full procedure and how intentional divergences are recorded.

---

## Reference Guide

| Resource | Purpose |
|---|---|
| `${CLAUDE_SKILL_DIR}/assets/settings.json` | Active rule configuration (plugin-portable defaults) — read this first on every invocation |
| `{REPO_ROOT}/.claude/plugin-rulebook.config.json` | Repo-specific R23 whitelist/blacklist/excluded_paths override — read second, if present (see "Repo-Specific Configuration" above) |
| `{REPO_ROOT}/.claude/plugin-rulebook-audit-decisions.md` | This repo's own Upstream Audit decision log (moved out of the plugin package — see "Repo-Specific Configuration" above) |
| `${CLAUDE_SKILL_DIR}/references/repo-specific-configuration.md` | Full load procedure and rationale for the repo-config split, expanded from "Repo-Specific Configuration" above |
| `${CLAUDE_SKILL_DIR}/references/adding-a-new-rule.md` | Checklist of every location a new rule (RNN) touches — SKILL.md sections, settings.json, the R20 sibling sweep, and mirroring — read before adding a rule |
| `${CLAUDE_SKILL_DIR}/references/size-rules.md` | R13/R18/R21 tiered thresholds for line count, code block size, and description size |
| `${CLAUDE_SKILL_DIR}/references/argument-consistency.md` | R22 detection procedure and worked examples for argument-hint/arguments consistency |
| `${CLAUDE_SKILL_DIR}/references/naming-conventions.md` | Full naming rules with examples for all component types |
| `${CLAUDE_SKILL_DIR}/references/formatting-rules.md` | Detailed formatting requirements and anti-patterns |
| `${CLAUDE_SKILL_DIR}/references/language-rules.md` | Language requirements, lang codes, multilingual variant procedure |
| `${CLAUDE_SKILL_DIR}/references/external-reference-policy.md` | R23 detection procedure, whitelist/blacklist matching, marketplace.json auto-allow, worked examples |
| `${CLAUDE_SKILL_DIR}/references/plugin-file-surface.md` | Shared plugin-scope/CWD-scope file-enumeration definition used by `language-reviewer`, `external-references-reviewer`, `consistency-reviewer`, `completeness-reviewer`, and `scripts-reviewer` |
| `${CLAUDE_SKILL_DIR}/references/gitignore-exclusion.md` | Shared procedure, used by every reviewer agent, for excluding gitignored paths before reviewing Glob results — and the companion authoring-side rule that no component may reference a gitignored path as a live dependency |
| `${CLAUDE_SKILL_DIR}/references/overhead-and-cost-rules.md` | R25/R26 violations, fix guidance, and worked examples |
| `${CLAUDE_SKILL_DIR}/references/compact-rule-checklist.md` | Pattern/violation/severity table for all 23 enabled rules, no narrative — read by the `plugin-rulebook-checker` agent instead of this file, to avoid re-reading full teaching prose on every isolated/backgrounded dispatch |
| `${CLAUDE_SKILL_DIR}/references/allowed-languages.md` | R24 full whitelist/banned/exempt lists, worked violation examples, and fix guidance |
| `${CLAUDE_SKILL_DIR}/references/suggested-additional-rules.md` | R11/R12/R15/R16 — disabled-by-default rules and why each might be worth enabling |
| `${CLAUDE_SKILL_DIR}/references/branch-and-pr-preflight.md` | Open-PR check and Branch-scope check procedures, shared with `plugin-lifecycle-upstream`, `plugin-lifecycle-downstream`, and `plugin-lifecycle-maintenance` |
| `${CLAUDE_SKILL_DIR}/references/open-item-discipline.md` | Phase-Completion check, Pre-Commit Disclosure, and downstream's proactive offer — shared by all three lifecycle skills |
| `${CLAUDE_SKILL_DIR}/references/frontmatter-corrections.md` | R5's `AskUserQuestion`/non-functional-field corrections, R6's agent-file Bash-scoping exception and full scope/verdict table |
| `${CLAUDE_SKILL_DIR}/references/evidence-schema.md` | Shared scope-manifest/finding/report-revision/evidence-bundle shapes used across `plugin-lifecycle-downstream`'s twelve-phase pipeline; validated by `scripts/validate_evidence.py` |
