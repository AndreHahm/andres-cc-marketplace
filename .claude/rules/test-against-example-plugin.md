# Test Against example-plugin

## When this applies

A new or structurally-modified `plugin-devkit` component whose job is to inspect, review, validate, or
otherwise operate against a plugin's actual on-disk component/manifest structure — before that component
is finalized. This covers 21 agents and 9 skills (see "In Scope" below), not every plugin-devkit
component.

## Rule

Before finalizing a new or structurally-modified in-scope component, run a live dry-run of it against
`example-plugin` (this repo's own minimal test-fixture plugin) and record the result. This is a live
workflow step, checkable only at the moment it should have happened — not something a static file
inspection can verify after the fact.

**In scope — 21 agents:**
- All 17 `*-reviewer` agents: `activation-reviewer`, `claudemd-reviewer`, `command-reviewer`,
  `completeness-reviewer`, `consistency-reviewer`, `dependency-reviewer`,
  `external-references-reviewer`, `hook-reviewer`, `human-doc-reviewer`, `language-reviewer`,
  `permission-reviewer`, `rule-reviewer`, `scripts-reviewer`, `security-reviewer`, `skill-reviewer`,
  `skilldir-reviewer`, `subagent-reviewer`
- `plugin-inspector`, `plugin-rulebook-checker`, `plugin-validator`, `smoke-tester` — same "operates
  against a plugin's actual structure/components" criterion, just not named `*-reviewer`

**In scope — 9 skills:**
- `plugin-lifecycle-upstream`, `plugin-lifecycle-downstream`, `plugin-lifecycle-maintenance`
- `plugin-auditor`, `plugin-grader`, `plugin-comparison`, `plugin-rulebook` (its direct-invocation
  mode, not just via `plugin-rulebook-checker`)
- `marketplace-inventory`, `plugin-inventory` — both read a plugin's or the marketplace's actual
  on-disk component/manifest structure in their `discover`/`check`/`plan` modes, the same criterion
  `plugin-inspector`/`plugin-validator`/`smoke-tester` meet above

**Explicitly excluded, with reasoning:**
- `agent-creator` — creates a *new* agent; its target is a spec to generate from, not an existing
  plugin's current state to analyze. Same reasoning excludes the component **Design** skills
  (`skill-development`, `hook-development`, `agent-development`, `command-development`,
  `rule-development`) — these already have their own `scripts/smoke_test.py` convention rather than an
  `example-plugin`-dry-run shape.
- `build-handoff-writer` — reads prior run records/commits to write a summary; doesn't itself inspect
  plugin structure.
- `enhancement-suggestor` — `Read`-only, consumes findings JSON another component already produced;
  nothing to dry-run against `example-plugin` directly.
- Session-analysis skills (`analyzing-sessions`, `mining-recurring-patterns`), the `rules-*` pipeline,
  git-kit-style skills — target is a session transcript or git state, not a plugin's component
  structure.

**Keeping the in-scope list current:** when a new skill or agent is added that meets the in-scope
criterion above, this list must be updated in the same commit/session that adds it — see
[[resweep-closed-scope-lists-on-new-components]] for the rule that catches a new qualifying component
being silently omitted.

## Recording the run

No agent `.md` file carries a test/verification section in its own frontmatter or body. Rather than
adding a new field (which would also need `plugin-rulebook`'s `agent.allowed_fields` list updated — an
R20 duplicate-fact-sweep concern), reuse the convention already in use for exactly this purpose:
`.claude/output/<component-name>/example-plugin-<ISO8601-timestamp>.{json,md}`. This works identically
for skills and agents — no schema change needed either way. Skills additionally cross-reference this
record from their own `## Testing & Validation` section's "Last dated run record:" line (see
`plugin-rulebook`'s R29); agents rely on the `.claude/output/` artifact alone.

## Trigger

"Before finalizing" — the same cadence `.claude/rules/plugin-rulebook-enforcement.md` already uses:
after the last modification in a creation/editing sequence, not per-intermediate-edit.

## Enforcement

Policy gate, no backing hook — same disclosed-limitation model
`.claude/rules/require-security-review-before-new-gate.md` uses for itself. A live dry-run against
`example-plugin` is a semantic judgment about whether testing actually happened, not something a
mechanical `PreToolUse` hook can verify. Compliance depends on author/reviewer attention at "before
finalizing" time.

## Why

A reviewer or inspector agent/skill that has only ever been read, never actually run against a real
plugin structure, can carry a subtle bug (a wrong Glob pattern, a misresolved path, a scope check that
never actually matches anything) that a narrative read-through won't catch. `example-plugin` exists in
this repo specifically as a minimal, safe-to-run fixture for this purpose — running the new or changed
component against it before finalizing is the cheapest real signal available that the component's Glob/
path/scope logic actually works against a real directory tree, not just against the author's mental
model of one.
