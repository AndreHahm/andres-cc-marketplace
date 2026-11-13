## Summary
Codex agent exports tell the agent to call Claude Code tools (`Glob`, `Grep`, `Read`) that Codex does not have

## Environment
- **Product/Service**: marketplace CI converter (`scripts/marketplace_ci/conversion.py`, `convert_agent()`) and the generated `.codex/agents/*.toml` exports
- **Region/Version**: PR #721 head `55c577d2`; `main` at 33ff1155

## Reproduction Steps
1. Open a generated export such as `.codex/agents/command-reviewer.toml`.
2. Read its `developer_instructions`: line 19 says "Search for the rulebook: `Glob(\"**/plugin-rulebook/SKILL.md\")`".
3. Compare with `docs/codex-subagents-schema.md`: Codex has no separate file-read or search tool and reads and searches files through its shell.

## Expected Behavior
An export's instructions name operations Codex can perform, for example a shell search (`rg --files`, `rg`) and a shell read (`cat`, `sed -n`), or the converter adds a note that maps the Claude tool names to their shell equivalents.

## Actual Behavior
`convert_agent()` copies the Claude agent body into `developer_instructions` unchanged, so the Claude tool calls stay in the text. 21 of the 26 exports on `main` name `Glob`, `Grep` or `Read` this way.

## Error Details
~~~
CI run 43446153560 (Codex delta review), head 55c577d2, two blocking Major findings:
- plugin-validator, agent-tool-compatibility, .codex/agents/command-reviewer.toml:19
- subagent-reviewer, tool-scoping, .codex/agents/authority-reviewer.toml:28
~~~

## Visual Evidence
None.

## Impact
**Low** - Not observed to fail: CI's own Codex reviewers (`plugin-validator`, `subagent-reviewer`) carry the same wording and read and search files correctly, which suggests Codex maps the names to its shell. Not verified that it always does. The finding blocks every PR that changes an export, until it is fixed or deferred.

## Additional Context
Found in PR #721 (https://github.com/AndreHahm/andres-cc-marketplace/pull/721), head SHA 55c577d22d687549cadc061623c4a8d08f04c5e2, CI job https://github.com/AndreHahm/andres-cc-marketplace/actions/runs/43446153560/job/131958801368. Reviewers: plugin-validator and subagent-reviewer (Codex exports). Severity: Major (as raised); deferred with the maintainer's risk acceptance.

**Related, not a duplicate:** #719 (the exports drop the source tool *limit*). That issue is about which tools an agent may use; this one is about the tool *names* in the instructions. Both are fixed in `convert_agent()`, so one change could close both.

**Open questions:**
1. Translate the names in the body (a rewrite that can break code spans and examples), or add one generated mapping note to the boundary note?
2. Should the converter also cover the `.agents/` skill exports, which copy skill bodies the same way?
