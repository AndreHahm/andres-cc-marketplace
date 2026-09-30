# R27 check: misc-kit/commands/config-settings.md

**Result: R27 FLAGS it - ADVISORY (never REQUIRED).**

## Reasoning
- R27 (Component Naming: Grammatical Form) applies to command file basenames (commands have no `name` field; the filename is checked). Expected form: verb-first (`create-plugin`, `review-rules`).
- misc-kit has no registered R33 prefix, so no prefix is stripped. Per `component-naming-grammatical-form.md` and `naming-conventions.md`: "For a plugin with no prefix registered yet, check the full basename as before."
- Full basename checked: `config-settings`. It starts with `config`, a noun, not a verb. It reads as a noun phrase (config settings), not an action.
- Therefore it violates the verb-first convention for commands.

## Contrast
If misc-kit had a registered prefix (e.g. `misc`), only the portion after `<prefix>-` would be checked. Here the whole basename is checked, so `config` is the first word and fails.

## Severity and fix
- ADVISORY only: R27 is interpretive and never blocking; a maintainer may decline with a considered reason.
- Fix: rename to a verb-first form (e.g. `configure-settings`, `edit-settings`), or reconsider the component type (a noun-named component may fit better as a skill).
- Other rules (R4 kebab-case) pass: `config-settings` is valid kebab-case.
