# Judgment: plugin-lifecycle-maintenance vs. "review my PR for bugs"

## Answer: No — the skill would not trigger.

## Reasoning

The prompt "review my PR for bugs" is a generic code-review request for a pull request. It has nothing to do with maintaining a Claude Code plugin, and the skill description gives no plausible hook for it:

- **Scope mismatch**: The description opens with "Orchestrates ongoing maintenance for an already-built plugin" — the entire skill is scoped to plugin maintenance, not general code/PR review. A PR full of arbitrary application code bugs is outside that domain entirely.
- **No matching trigger phrase**: The explicit example triggers listed are "improve this plugin based on the retro", "enhance this plugin compared to X", "check plugin-devkit's rules against upstream docs", "run a self-check on plugin-devkit", and "keep plugin-devkit current with the platform docs." None resemble "review my PR for bugs" in phrasing or intent.
- **Named upstream sources don't match**: The skill activates on findings "from analyzing-sessions, plugin-comparison, or the dev-rules commands" — i.e., retrospectives, plugin comparisons, or rules-modernization audits. A PR bug review is not one of these; it's not a retro, not a comparison against another plugin, and not a rules-freshness audit.
- **Bug-finding vs. fix-application**: Even loosely, the skill's stated job is to take existing findings and drive them through human-approved apply/test/commit — it explicitly says it "never decides what to fix itself." "Review my PR for bugs" is a request to *find* problems in arbitrary code, which is closer to a code-review skill's job, not this orchestration skill's job of routing pre-existing findings to a fix pipeline.
- Nothing in the description mentions "PR," "pull request," or general bug-finding in non-plugin code at all.

Given the tight, repeatedly-reinforced scoping to "already-built plugin" maintenance and specific named workflows (retro, comparison, dev-rules), a semantic matcher would not fire this skill for a bare "review my PR for bugs" request.
