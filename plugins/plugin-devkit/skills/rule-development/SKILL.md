---
name: rule-development
description: >-
  Creates and validates .claude/rules/ behavioral guardrail files using contrastive
  Incorrect/Correct examples. Use when a mistake recurs across agent sessions, when the user
  identifies a behavioral gap, or when standardizing code conventions or adding path-scoped
  constraints for specific file types.
allowed-tools: Read Write Edit Glob Grep Skill
---

# Create Rule

Guide for creating effective `.claude/rules` files with contrastive examples that improve agent accuracy.

## Quick Start

1. **State the behavioral gap** — "Agent does X, should do Y" (concrete observation, not vague)
2. **Determine scope** — global (all files), path-scoped (`paths:` frontmatter), or user-level (`~/.claude/rules/`)
3. **Write Incorrect example first** — the exact plausible mistake the agent produces
4. **Write Correct example** — minimal fix of the same scenario
5. **Write description** — 1-2 sentences: WHAT the rule enforces + WHY it matters, imperative form
6. **Assemble rule file** — use the template in Rule Structure below; run Rule Creation Checklist
7. **Validate** — run `/rules-review` to confirm it fires on real violations with no false positives

## When to Use

- A behavior must apply to ALL agent sessions
- Agents repeatedly make the same mistake despite corrections
- A convention has clear right/wrong patterns (contrastive examples are possible)
- Path-specific guidance is needed for certain file types

## When NOT to Use

- Task-specific workflows → use a skill instead
- One-time instructions → put in the prompt
- Broad project context → put in CLAUDE.md
- Multi-step procedures → use a skill

## Core Principle

Effective rules use **contrastive examples** (Incorrect vs Correct) to eliminate ambiguity. Rules are
behavioral guardrails that load into every session — they are "standing orders" that every agent
inherits automatically. If guidance is task-specific, create a skill instead.

A rule states *what* must or must not happen; a skill teaches *how* to perform multi-step work.
Rule files must not contain procedural content — numbered steps or multi-step code blocks belong
in a skill, not a rule.

## Rules vs Skills vs CLAUDE.md

| Aspect | Rules (`.claude/rules/`) | Skills | CLAUDE.md |
|--------|--------------------------|--------|-----------|
| **Loading** | Every session (or path-scoped) | On-demand | Every session |
| **Purpose** | Behavioral constraints | Procedural knowledge | Project overview |
| **Size** | ~50 lines body (50-200 words for the description) | 200-2000 words | Medium |
| **Format** | Contrastive examples | Step-by-step | Bullets |

## Rule Structure

Every rule MUST follow the Description-Incorrect-Correct template. See [rule-file-skeleton.md](references/rule-file-skeleton.md) for the bare template and [examples.md](references/examples.md) for complete worked examples.

`paths` is the only field with official platform meaning; `title` and `impact` are internal
plugin-devkit conventions for organizing rules, not required by the platform.

## Rule Types

### Global Rules (no `paths` frontmatter)

Load every session. Use for universal constraints.

### Path-Scoped Rules (`paths` frontmatter)

Rules without `paths` load unconditionally, every session; rules with `paths` load only when Claude works with a matching file. See `references/rules-specification.md`'s "Path-Specific Rules" section for the full explanation, the pattern-assessment table, and multi-pattern/brace-expansion detail.

**Use `paths` whenever it can be defined** — reduces context noise for unrelated work. Avoid overly broad patterns like `**/*` or `*`.

### User-Level Rules (`~/.claude/rules/`)

Apply across all projects for personal preferences. See `references/rules-specification.md` for setup details.

## Writing Effective Rules

**Description principles:**
- Be specific: `"Functions must not exceed 50 lines"` not `"Keep functions short"`
- State the WHY: `"Use early returns — deeply nested code increases cognitive load"`
- Use imperative language — `MUST`, `NEVER` — not passive voice, "try to," or "consider"

**Compactness budget:** Keep the rule body under ~50 lines; the 50-200 word range applies to the
core description, not the whole file (excluding code examples). One rule per file.

**Session-start budget (recommended, not a hard limit):** Keep the combined size of CLAUDE.md and
all `.claude/rules/` files under ~300 lines — every rule loads at session start (or on file match)
and adds to context cost.

**Incorrect examples** must show patterns agents **plausibly produce** — the most common mistake,
not contrived bad code. **Correct examples** must show the minimal fix for the same scenario.

For extended guidance on what makes effective examples, see `references/examples.md`.

**`.examples.md` companion files:** For rules with nuanced edge cases, create a sibling file
`<rule-name>.examples.md` in the same directory. The compliance reviewer (`/rules-review`) loads
it automatically alongside the rule file. Use it for additional Good/Bad contrasts, edge cases,
and anti-patterns that would push the main rule file past the 200-word budget.

### Enforcement Limits

Rules alone achieve roughly 70% compliance — they are instructions, not code. A hard directive
(`MUST NEVER` around a destructive or irreversible action) must be backed by a deterministic
enforcement mechanism — a hook or permission rule — not the rule text alone.

## Additional Process Guidance

### Security Self-Check (after assembling the rule file)

After writing examples, scan the rule file for sensitive information that may have been copied
from real code:

1. Grep for long hex strings: `[0-9a-fA-F]{20,}`
2. Grep for base64-like strings: `[A-Za-z0-9+/=]{40,}`
3. Grep for keyword-adjacent literals: `(key|token|secret|password|credential)\s*[:=]\s*["'][^"']+`
4. Grep for internal URLs: `(internal|staging|localhost:[0-9]+)`

If found, replace with placeholders (`API_KEY_REDACTED`, `https://example.com`, etc.) before saving.

### Iterate and Refine

Optionally treat rule creation as TDD: observe the behavior gap first (RED), write the rule
(GREEN), validate with `/rules-review` (REFACTOR).

Apply Decompose → Filter → Reweight cycle before finalizing.

**7.1 Decompose** — "Is this rule trying to cover more than one concept?"
- If YES → split into multiple focused rules, one concept each

**7.2 Misalignment Filter** — "Could this rule penalize acceptable variations?"
- If YES → narrow scope or rewrite contrastive examples
- Verify: would an agent actually produce the Incorrect pattern? If not, rule is contrived

**7.3 Redundancy Filter** — Check existing rules for overlap:
```
Glob .claude/rules/**/*.md
Grep "relevant-keyword" in .claude/rules/
```
If overlap found → update existing rule, delete the duplicate you just created.

Also check for **cross-format duplicates**: a project-specific pattern in a `.local.md` file may
already be captured as a Principle in the corresponding `.md` file under a different name. Use
semantic equivalence (synonyms, case-insensitive), not just exact string match. If the new rule's
intent matches an existing Principle, skip creating a new file and reference the existing one.

**7.4 Impact Reweight** — Assign `impact` frontmatter:
- **CRITICAL**: Data loss, security vulnerabilities, system failures
- **HIGH**: Broken functionality, incorrect behavior, hard-to-debug issues
- **MEDIUM**: Degrades quality, readability, or maintainability
- **LOW**: Minor style or convention issue

**7.5 User Feedback Loop** — Share the rule with the user.
- If approved → done
- If not → update to close gaps, iterate until approved

**7.6 Staleness Watch** — Rules that reference project-specific symbols (function names, types,
hook signatures) can become stale when the codebase evolves. After any major refactor or
dependency upgrade, verify that inline code signatures in rule examples still exist:
```
Grep "`symbolName`" in .claude/rules/**/*.md
```
If a symbol no longer exists, update the example or remove the rule if the pattern is obsolete.
Do NOT auto-delete — flag for user review.

## Directory Structure

```
.claude/
├── CLAUDE.md
└── rules/
    ├── code-style.md            # Global
    ├── error-handling.md        # Global
    ├── security.md              # Global
    └── frontend/
        ├── components.md        # Path-scoped
        └── state-management.md  # Path-scoped
```

Naming: lowercase with hyphens, named by concern (`error-handling.md` not `try-catch-patterns.md`).

**Canonical categories** — when rules apply to a specific language, framework, or integration
library, place them in the appropriate subdirectory so they can participate in org-wide rule
sharing (`/rules-extract`, `/rules-merge`, `/rules-apply`):

```
.claude/
└── rules/
    ├── project.md               # Project-wide domain rules (no paths: — applies to all files)
    ├── languages/
    │   ├── typescript.md        # Portable principles for this language
    │   └── typescript.local.md  # Project-specific patterns (not portable)
    ├── frameworks/
    │   ├── react.md
    │   └── rails-controllers.md # Layer-specific: <framework>-<layer> naming
    └── integrations/
        └── rails-pundit.md      # Integration libraries: <framework>-<integration>
```

`project.md` is inherently project-specific — do not design it for portability across projects.
`languages/`, `frameworks/`, and `integrations/` subdirectories follow the rules-extract/rules-merge
convention and can be shared via `/rules-merge` and `/rules-apply`.

## Rule Creation Checklist

- [ ] Behavioral gap: "does X, should do Y"
- [ ] Rule type determined: global, path-scoped, or user-level
- [ ] Incorrect example shows plausible agent mistake
- [ ] Correct example shows minimal fix of the same scenario
- [ ] Description states WHAT and WHY, in imperative form
- [ ] Frontmatter: `title` and `impact` present (internal convention; `paths` is the only officially platform-recognized field)
- [ ] Body under ~50 lines; description 50-200 words (excluding code examples)
- [ ] One topic per file
- [ ] No overlap with CLAUDE.md or other rules
- [ ] Path scoping uses correct glob patterns (if applicable)
- [ ] File placed in `.claude/rules/` with descriptive hyphenated name
- [ ] No sensitive information in examples (secrets, tokens, internal URLs)
- [ ] Compliance verified: `/rules-review` fires on intended violations, no false positives

## Updating Existing Rules

When a rule needs a new pattern added (without overwriting existing content):

1. Read the existing rule file before editing.
2. Append to the appropriate section — do not replace existing Incorrect/Correct examples.
3. **Preserve manual edits**: treat existing content as authoritative.
4. Re-run the redundancy filter (see Iterate and Refine → 7.3) — the new addition may now overlap with another rule.
5. Re-run the security self-check on the updated file.
6. Re-run `/rules-review` to confirm the updated rule still fires correctly.

When existing rules under `languages/` or `frameworks/` are updated, check whether the same
pattern applies across other projects — if it does, promote it to a Principle (portable, no
project-specific implementation details) rather than keeping it as a project-specific pattern.

## Rule-Doc Drift

A rule can become stale when the codebase intentionally adopts a different pattern. In this case
the violation is in the **rule**, not the code. Signs of rule-doc drift:

- The same "non-compliant" pattern appears in 3+ locations in the codebase, all consistent.
- The rule's text cites a numeric threshold or API behavior that the project has intentionally changed.
- A major dependency upgrade changed the recommended approach.

**Do not fix the code.** Update or remove the stale rule instead:
1. Confirm the pattern change was intentional (not an oversight).
2. Rewrite the rule's description and examples to match current conventions.
3. If the pattern no longer has a wrong/right distinction, delete the rule.
4. Run `/rules-extract --update` to capture the new convention if it wasn't previously documented.

## Periodic Maintenance

Periodically audit CLAUDE.md, nested CLAUDE.md files, and all `.claude/rules/` files together for
conflicting, duplicated, or drifted instructions — instructions written at different times can
silently contradict each other, and Claude may resolve the conflict arbitrarily.

## Reference Guide

| Resource | Purpose |
|---|---|
| `references/examples.md` | Complete worked examples, anti-patterns, extended writing guidance |
| `references/rules-specification.md` | Official Claude Code rules documentation (path scoping, symlinks, user-level rules) |
| `plugin-rulebook` | Plugin-level rules — invoke before finalizing any rule file to check naming, language, formatting, and external-reference compliance |
| `plugin-rulebook/references/size-rules.md` — R18 section | Before extracting an oversized inline example (e.g. a full rule-file skeleton) into `examples/`, check its "Before extracting, check whether extraction actually removes the violation" guidance first — a naive extraction can just re-wrap the same content in another oversized fence inside the new file. `examples/global-rule-example.md` and `examples/path-scoped-rule-example.md` in this skill are worked examples of extracting correctly (standalone files, independent non-nested fences) |
