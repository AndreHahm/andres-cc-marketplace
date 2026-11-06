# Eval 2 (with_skill): convert release-notes slash command

Followed skill-development SKILL.md, Convert path -> references/slash-command-conversion.md, plus pdk-allowed-tools.md for grants.

Assumed user answers (AskUserQuestion points): placement = skills/release-notes/ under outputs (as the task dictates); no eval fan-out run (conversion only); keep auto + user invocation.

Decisions:
- name `release-notes`; third-person description with quoted trigger phrases.
- allowed-tools: `Bash(git:*) Bash(gh:*) Read Write` as separate entries (the original comma-joined `Bash(git:*, gh:*)` form is not carried over).
- Behavior preserved (gh pr list --state merged, group by conventional type, write RELEASE_NOTES.md). One deliberate addition: date-scoping via `--search "merged:>=<tag-date>"`, because `gh pr list --state merged` alone has no "since last tag" filter. Stated in the skill body.
- git grant justified by tag lookup; Read by the existing-file check; Write by RELEASE_NOTES.md.
- Not run: quick_validate, eval loop, rulebook (task limited to outputs dir).
- Observation: the conversion reference describes commands as `~/.claude/commands/*.sh`, while this task is a `.claude/commands/*.md`; the mapping still applied cleanly.
