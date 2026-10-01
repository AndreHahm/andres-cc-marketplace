# Canonical Path Resolution (R19)

Full detail for R19. SKILL.md carries the rule's one-line statement and a pointer here.

Before checking a component, resolve its actual absolute file path and verify no duplicate or shadow copy of the same named component exists in another scope.

**Scope:** Any component invoked by name (skill, agent, command, hook, rule) — check project `.claude/skills/`, plugin `plugins/*/skills/` (and equivalent `agents/`, `commands/`, `hooks/`, `.claude/rules/` locations), and user `~/.claude/skills/` for a same-named duplicate.

**Violations:**
- The invoked component name resolves to two or more directories, and their contents differ
- The compliance report does not state the absolute path that was actually checked

**Fix:** Report the resolved absolute path in the compliance report header. If duplicates exist with differing content, FAIL and require the invoker to disambiguate by full path or resync the copies before proceeding.

## Exception — in-development plugin mirrors

A plugin still under active development may need its components staged into the project's `.claude/` directory so they actually run before the plugin is packaged and installed — removing the `.claude/` copy at this stage would break the very components being developed. Treat this as an intentional, expected duplicate, not a violation: verify the copies are identical (see R20) and note it as PASS/informational, not ADVISORY-to-deduplicate. Do not suggest removing the `.claude/` copy until the plugin has actually been installed (confirmed via `/plugin` or the marketplace) — finishing edits is not the same as installation.

## Exception — distributed-vs-local canonical divergence

A component whose own content must resolve differently depending on install context (e.g. a path variable inside a skill's frontmatter `hooks:` block that needs to reference the *distributed* plugin install location in the canonical `plugins/*/` copy, but the *local repo* location in the `.claude/` mirror copy, since the mirror is never itself distributed) may need its two copies to genuinely differ in content, not just directory location. This is **not** the same as the in-development-mirror exception above — that one requires identical content; this one requires the opposite. Treat it as PASS/informational, not a violation, **only when** `.claude/marketplace-sync.json`'s `divergence_exceptions` list contains an entry whose `source` and `dest` fields exactly match the two file paths under review (not merely *some* entry with a non-empty `reason` — the source/dest fields are what tell a real R19 violation apart from a legitimately-declared one, since both look identical from the diff alone). Report the divergence and cite the matching entry's `reason` in the compliance report rather than silently passing it.
