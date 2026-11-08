## Summary
plugin-rulebook has no rule for the 10,000-character agent body limit that agent-development documents and CI enforces

## Environment
- **Product/Service**: plugin-rulebook and plugin-devkit (`agent-development`, `subagent-reviewer`), this marketplace repo
- **Region/Version**: `main` at 6b05df03

## Reproduction Steps
1. Edit an agent file such as `plugins/plugin-devkit/agents/security-reviewer.md` so its body (the characters after the closing frontmatter delimiter) is over 10,000 characters.
2. Run the per-edit hook (`pdk-rulebook-check.py`) and the before-finalizing `plugin-rulebook` check.
3. Push the branch and open a PR.

## Expected Behavior
The rulebook flags the oversized agent body when the agent is edited, in the same way R13, R18 and R21 flag the size of a skill's line count, code blocks and description fields.

## Actual Behavior
The rulebook has no size rule for an agent body. R21 even states that agents have no description size rule. The per-edit hook reported "No mechanical issues found" on every edit of the agent files in PR #675, and the before-finalizing check had nothing to apply. The defect surfaced only after the push, in the CI Codex delta review.

## Error Details
CI run 42471529366, job 128704015860 "Codex delta review". Reviewer `subagent-reviewer` reported a blocking Major finding (rule label "prompt-quality") on `plugins/plugin-devkit/agents/security-reviewer.md` line 39:

~~~
The plugin agent body is 10,347 characters, exceeding agent-development's hard maximum
of 10,000 characters. [...] The repository validator reports the over-10,000-character warning.
~~~

It kept the required "Publish Codex policy result" check red until the body was trimmed to 9,964 characters (commit 720e8c4c).

## Visual Evidence
None.

## Impact
**Medium** - The limit is enforced in CI as a blocking finding but is invisible to local checks, so each violation costs a push, a CI run and a review round. Nothing breaks at runtime and the workaround is to trim the file.

## Additional Context
Found in PR #675.

**Where the 10,000 figure is stated today.** Five places in four files, all in `plugin-devkit`, none in `plugin-rulebook`:
- `plugins/plugin-devkit/skills/agent-development/SKILL.md` line 187 ("Keep under 10,000 characters") and line 256 (table row "System prompt | 20-10,000 chars (ideal: 500-3,000)").
- `plugins/plugin-devkit/skills/agent-development/references/validation.md` line 84.
- `plugins/plugin-devkit/agents/subagent-reviewer.md` line 77.
- `plugins/plugin-devkit/skills/agent-development/scripts/validate-agent.sh` lines 235-236. It adds a warning (not an error) when the extracted system prompt is over 10000 characters. It is the only mechanical check of the figure that I found.

**Agents already over the cap on `main`** (body measured as the characters after the closing frontmatter delimiter): `permission-reviewer` 13,036 and `skill-reviewer` 16,481. CI did not flag them in PR #675. Probably this is because the review looks at changed lines, but I did not verify that. The reviewer did flag `security-reviewer` in that PR, which expanded a section of an already-oversized body.

**Related, not a duplicate:** #624 (agent-development conventions diverge from the official sub-agent documentation and are not recorded as intentional). It does not mention the size limit. A search of open and closed issues for "agent body size", "10,000 characters", "plugin-rulebook agent size", "subagent-reviewer" and "agent length limit" found no issue about it.

**Open questions (not decided here):**
1. Where does 10,000 come from: the official Claude Code sub-agent documentation, or a local convention? I did not verify the official documentation.
2. How is the body measured? This report used the characters after the closing frontmatter delimiter. `validate-agent.sh` uses its extracted `${#SYSTEM_PROMPT}`. The rule must pin one definition.
3. Which severity tier: REQUIRED, or tiered like R13 and R21 with a warning band below the cap? Should it be forward-looking only (new or modified agents, like R28-R37), since two existing agents already exceed it?
4. Enforcement: add a mechanical check to `pdk-rulebook-check.py` and to the `plugin-rulebook-checker` agent, so the per-edit hook and the before-finalizing check agree with CI?
5. R20 duplicate-fact sweep: the number would become a canonical value in `plugin-rulebook`'s `assets/settings.json`. The five places above would need to point at it or be swept together.
6. What happens to the two existing oversized agents: grandfather, trim, or split detail into references?

**Suggested labels (maintainers to confirm):** `t: feature`, `a: ai-setup`, `s: triage`, and `p: low` or `p: medium`.
