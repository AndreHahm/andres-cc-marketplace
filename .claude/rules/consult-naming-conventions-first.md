# Consult Naming Conventions First

## When this applies

Naming any new plugin-devkit component — a skill, agent, command, or rule — before the name is chosen, not after.

## Rule

Before naming a new component, read `plugin-rulebook/references/naming-conventions.md`'s Component-Type Conventions table (skill: noun/gerund, agent: role-noun, command: verb-first, rule: behavior-description) and name the component to match on the first pass. Don't rely on `plugin-rulebook`'s R4 (kebab-case) or R27 (grammatical form, ADVISORY) to catch a mismatch after the fact — those checks run at "before finalizing," the end of the process, once the name may already be cross-referenced elsewhere.

## Why

Three rules created earlier in this same session used topic-noun-phrase names (`inspiration-vs-structure.md`, `component-configuration.md`, `component-testing.md`) when `naming-conventions.md` already documented "behavior-description" as this repo's rule-naming style (`no-hardcoded-secrets`-style). The file had the answer the whole time; not checking it before naming cost 3 separate commits later in the same session to rename the files, update their cross-references, and re-mirror them — pure rework that a 30-second check up front would have avoided entirely.
