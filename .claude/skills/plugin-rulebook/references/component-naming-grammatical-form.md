# R27 — Component Naming: Grammatical Form (Full Detail)

Extracted from `SKILL.md`'s R27 entry to keep the skill under its own R13 line-budget threshold (the
same reason R28-R32's detail already lives in dedicated reference files). See `SKILL.md`'s R27 entry
for the one-line summary and severity.

Skills, agents, and commands should follow their documented grammatical form per
`references/naming-conventions.md`'s Component-Type Conventions table — not just valid kebab-case (R4),
but the right *shape* of phrase for the component type. Never REQUIRED: this is an interpretive,
judgment-based check, not a mechanical pattern match, and a maintainer may have a considered reason to
diverge (an established external convention, or the cost of renaming a widely cross-referenced
component).

**Scope:** `name` field in SKILL.md frontmatter, `name` field in agent file frontmatter, and command
file basenames (commands have no `name` field — check the filename itself).

**Expected form per type:**
- Skill: a noun or gerund phrase naming a domain/capability (`skill-development`, `plugin-rulebook`,
  `bootstrapping-a-python-project`) — not a bare imperative verb phrase.
- Agent: a role-based noun phrase (`skill-reviewer`, `plugin-validator`) — not a bare imperative verb
  phrase.
- Command: starts with a verb (`create-plugin`, `review-rules`).

**Violations (ADVISORY only):**
- A skill named as a bare imperative verb phrase with no noun/gerund framing (e.g. a skill named
  `create-pr` reads as a command's action, not a skill's domain).
- An agent named without role-noun framing.
- A command that doesn't start with a recognizable verb.

**Fix:** Rename to match the documented form, or reconsider the component type (a bare-imperative-named
skill may actually want to be a command). Flag and move on if the maintainer declines — this rule exists
to surface the mismatch, not to force a rename.
