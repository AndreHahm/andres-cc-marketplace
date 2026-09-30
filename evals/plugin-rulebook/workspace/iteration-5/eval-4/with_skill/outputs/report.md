# R27 check: misc-kit `commands/config-settings.md`

**Verdict: R27 FLAGS it, as ADVISORY (never REQUIRED/FAIL).**

## Reasoning
1. R27 (SKILL.md, Component Naming: Grammatical Form, ADVISORY) applies to command file basenames. Commands have no `name` field, so the filename itself is checked. Expected form for a command is verb-first (per `references/naming-conventions.md` and `references/component-naming-grammatical-form.md`).
2. The prefix carve-out does not apply. The rule strips a prefix before checking only "for a command in a plugin that has an R33-registered prefix". misc-kit's record has `"prefix": null` and no `domain_prefix`, so nothing is registered. The references say to check the full basename as before.
3. Full basename checked: `config-settings`. Its first token, `config`, is a noun (as given in the task), not a verb. The name reads as a noun phrase, not an action.
4. Result: the command does not start with a recognizable verb, which is a listed R27 violation. Severity is ADVISORY only. It is interpretive, so the maintainer may decline.

## Note on `config` and `settings`
Do not treat `config` as a stripped prefix. `null` prefix means R33 registers nothing, so R33 itself raises no finding here.

## Suggested fix (optional)
Rename to a verb-first form such as `configure-settings.md` or `edit-settings.md`, or keep the name if there is a considered reason. The rule surfaces the mismatch, it does not force a rename.

## Other rules
Only R27 was evaluated, per the task. R33 is inert for this plugin (null prefix, no domain_prefix).
