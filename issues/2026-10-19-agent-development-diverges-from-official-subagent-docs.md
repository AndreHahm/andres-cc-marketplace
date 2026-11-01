## Summary
plugin-devkit's `agent-development` conventions differ from the official sub-agent documentation in four ways, and none is recorded as an intentional divergence

## Environment
- **Product/Service**: andres-cc-marketplace, `plugin-devkit` (`agent-development` skill, `plugin-rulebook` R6, the 25 agents under `plugins/plugin-devkit/agents/`)
- **Region/Version**: found during #522 (branch `refactor/skill-development`, PR #571); official pages checked on 2026-10-19; Claude Code 2.1.302

## Reproduction Steps
1. Read the official [sub-agents page](https://code.claude.com/docs/en/sub-agents) in full, plus the [permissions page](https://code.claude.com/docs/en/permissions) and [skills page](https://code.claude.com/docs/en/skills).
2. Read Anthropic's `plugin-dev` `agent-development` skill (`plugins/plugin-dev/skills/agent-development/SKILL.md` in the `anthropics/claude-code` repository).
3. Compare them with `plugins/plugin-devkit/skills/agent-development/SKILL.md` and `plugin-rulebook` R6.
4. Count the agents that follow the repo's own convention: `grep -l "^## When to invoke" plugins/plugin-devkit/agents/*.md | wc -l`.

## Expected Behavior
Each repo-vs-official difference is either aligned with the docs, or recorded as an intentional divergence in one place (the repo's mechanism for this is an Excluded Candidate in `pdk-verify-dev-rules`, see `.claude/rules/plugin-rulebook-enforcement.md`, "Upstream Source Verification"). The wording in `agent-development` matches what is actually enforced.

## Actual Behavior
The differences are stated as if they were the standard, are enforced unevenly, and are recorded nowhere:

1. **`## When to invoke` section.** `agent-development` says every agent ends with a `## When to invoke` section of 2-4 prose trigger scenarios (creation steps, file template, seven-part prompt structure). The official sub-agents page never mentions it: only `name` and `description` are required, delegation comes from the `description` ("when Claude should delegate to this subagent", plus "use proactively" phrasing), and the body is the system prompt with no prescribed sections. Anthropic's `plugin-dev` skill does not use that heading either; it puts the triggering conditions and 2-4 example blocks in the description. So this section is a repo-only convention. It is also applied unevenly inside the repo: **10 of the 25 agents have it, 15 do not** (`activation-reviewer`, `skill-reviewer`, `subagent-reviewer`, `consistency-reviewer`, `claudemd-reviewer`, `command-reviewer`, `completeness-reviewer`, `hook-reviewer`, `human-doc-reviewer`, `language-reviewer`, `plugin-validator`, `rule-reviewer`, `scripts-reviewer`, `skilldir-reviewer`, `enhancement-suggestor`). A Codex parity review on PR #571 flagged `skill-reviewer` and `activation-reviewer` as Major for lacking it, so reviewers enforce the standard while most agents do not follow it.
2. **Example blocks.** `plugin-dev` recommends 2-4 example blocks in the description; the official sub-agents page shows none. This repo removed them from agent descriptions on purpose. That is a deliberate divergence from `plugin-dev`, but it is not written down as one.
3. **Bash for read-only reviewers.** `agent-development` says read-only reviewer agents must not receive `Bash`, `Write` or `Edit`. The official page's own read-only `code-reviewer` example lists `tools: Read, Grep, Glob, Bash`. The repo rule is stricter than the docs, which is fine as a policy but should be recorded as one.
4. **Scoped Bash in agent `tools`.** R6 treats a scoped `Bash(...)` entry in an agent's `tools` field as a violation and requires bare `Bash`. The official page documents that a `Bash(...)` specifier in `disallowedTools` removes the whole tool, and its `db-reader` example uses bare `tools: Bash` plus a `PreToolUse` hook. The page text read does not show a `Bash(...)` entry in a `tools` allowlist either way. **Unverified:** whether the CLI accepts or ignores a scoped entry in `tools`; this needs a live check before the rule is cited as official behavior.

## Impact
**Low** - nothing is broken. The cost is review noise (parity reviews raise Major findings for a repo-only convention that most agents do not follow) and a rulebook that presents its own stricter choices as the official standard.

## Additional Context
- Related: #564 (interpreter-wide Bash grants; a comment there records the official-docs findings for `allowed-tools`) and #570 (deferred findings, includes `validate-agent.sh` being looser than the documented rules).
- Suggested fix: record each of the four as an Excluded Candidate through `pdk-verify-dev-rules`, and register the sub-agents page in the upstream-sources registry if it is not tracked. For item 1, decide between (a) relaxing `agent-development`'s wording from "requires" to "recommended" and (b) adding the section to the 15 agents. Do a live check for item 4.
- Acceptance: the four items each have a recorded decision; `agent-development` wording matches enforcement; reviewers stop flagging the missing section for agents the decision exempts.
- Raised in PR #571.
