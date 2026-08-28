# Verify Rule Scope Before Lazy-Loading

Before proposing to move an always-loaded rule to path-scoped (`paths:` frontmatter) or fold it into a
skill's own body, re-derive its actual applicability from its own "When this applies" text — never
pattern-match it against a sibling rule that was migrated correctly.

## Incorrect

A rule covering both "modify" and "create" operations gets path-scoped to load only on a matching
file *read*, because a sibling rule with the same shape was already scoped that way:

```yaml
paths:
  - "plugins/*/skills/**"
```

The rule's own compliance table explicitly covers creating a brand-new skill — but a file that doesn't
exist yet can't be read, so path-scoping silently drops the rule's "create" coverage.

## Correct

The rule's own scope is checked for a create operation before scoping. Since one exists, and no
realistic create path already involves reading a matching sibling file first, the rule stays
always-loaded (no `paths:` frontmatter) instead of being scoped.

## When this applies

Proposing to lazy-load an existing always-loaded `.claude/rules/*.md` / `plugins/*/rules/*.md` file —
either by adding `paths:` frontmatter, or by folding its content into a skill's own body — before that
proposal is presented or applied.

## Rule

- **Read the rule's own "When this applies" section in full** before scoping or folding it — never infer
  applicability from its title or from how similar it looks to an already-migrated sibling.
- **Path-scoping:** if the rule's scope includes a *create* operation (a new file, branch, worktree, or
  component that doesn't exist yet), path-scoping is unsafe — a path-scoped rule loads on read, and a
  brand-new file has nothing to read yet. Default to keeping it always-loaded unless every realistic path
  to that create operation already reads a matching sibling file first (and treat even that as a risk to
  disclose, not a guarantee). Enumerate every path pattern the rule's text implies, grepping the whole
  `plugins/` and `scripts/` tree, not just the migration's working example. Cross-check every sibling
  rule touched in the same migration: if two rules both claim to cover the same topic (e.g. "scripts")
  but only one's `paths:` list actually includes the matching pattern, that asymmetry is itself evidence
  one of them is wrong — resolve it before proposing either.
- **Folding into a skill:** list every trigger path the rule names, not just the one the target skill
  obviously governs — a rule naming three paths and folded into a skill covering one has silently dropped
  the other two unless each is separately verified reachable. Read the target skill's own "When NOT to
  Use"/constraints section first — if it refuses to run under the exact condition the rule describes, the
  fold can't cover that condition. A trigger path with no governing skill at all (e.g. a raw manual
  command) can't be folded; the rule stays standalone.
- **Canonical source:** before editing, find the rule's true canonical source with a whole-tree search
  (`plugins/*/rules/`, `scripts/marketplace_ci/rules/`) — `.claude/rules/<name>.md` is a generated mirror,
  and editing it directly is silently reverted by the next sync. After editing, re-run the sync and diff
  the mirror pair — confirm the `.claude/` copy actually reflects the edit, not stale pre-edit content
  the sync silently restored.
- **Batch proposals:** check every candidate individually against this rule, not sampled or
  pattern-matched from ones that already passed, and get an independent review before treating the
  migration as ready to ship.

## Why

Source: a 2026-08-27 rule-migration session (PR #154) proposed 7 relocations; PR review (Codex + Devin)
found 2 of 5 path-scoped rules and the one skill-folded rule needed a full revert. `plugin-rulebook-enforcement.md`
was path-scoped to load on file *read*, but its own compliance table names creating a brand-new
skill/agent/command/hook — nothing to read yet for a file that doesn't exist. Separately,
`orphaned-worktree-git-read-fallthrough.md` was folded into `git-cleanup`'s own Phase 5, but the rule
named three trigger paths (`git-cleanup`, `finishing-work`'s hand-off, a *manual* `git worktree remove`)
and `git-cleanup` itself refuses to run from inside the worktree it would remove — the fold covered one
of three paths, arguably not even that one cleanly. Both were pattern-matched against correctly-migrated
rules rather than individually re-derived from their own scope text, and neither was caught by the first
independent review pass — only a second reviewer caught each.

This rule stays always-loaded (no `paths:`) for the same reason: its own scope covers folding into a
skill's own body, which edits a *skill* file — a path a `paths:`-scoped version of this rule would never
match, since path-scoping only fires on reading a matching file. Path-scoping itself, applied to the rule
whose entire job is warning against unsafe path-scoping, would be exactly the anti-pattern above.
