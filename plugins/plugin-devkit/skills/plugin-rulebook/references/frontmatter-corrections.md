# Frontmatter and Tool-Scoping Corrections

Rule details that were previously misclassified, then corrected against current official docs, plus R6's full Bash scope/verdict table — kept as full teaching prose here rather than in `SKILL.md` itself, since a checklist consumer (e.g. `plugin-rulebook-checker`, which already carries the corrected verdicts inline in `compact-rule-checklist.md`) only needs the corrected verdict, not the full reasoning trail behind it.

## R5 — `AskUserQuestion` in `allowed-tools`

ADVISORY, not REQUIRED — corrected 2026-07-27, was previously misclassified as forbidden.

Listing `AskUserQuestion` in `allowed-tools` is a harmless no-op, not a schema violation. Verified against current official docs (code.claude.com/docs/en/skills, "Pre-approve tools for a skill"): *"`allowed-tools`... does not restrict which tools are available: every tool remains callable"* — omitting a tool from `allowed-tools` never blocks it, so `AskUserQuestion` works identically whether listed or not. `AskUserQuestion` is a real, recognized tool name in Claude Code's permission vocabulary (the same docs use it as the canonical example for `disallowed-tools`: *"such as `AskUserQuestion` for a background loop"*), so listing it isn't malformed frontmatter either — it just grants pre-approval for a tool that was never permission-gated in the first place, so the grant has no effect.

Flag as ADVISORY ("redundant — AskUserQuestion doesn't need to be in allowed-tools, listing it has no effect") when present, not as a blocking REQUIRED violation. This corrects an earlier version of this rule that classified it as forbidden; if a `skill-reviewer`-style pass ever flags `AskUserQuestion` as a *missing* required tool grant, that finding is also incorrect for the same reason — the tool is always callable regardless of `allowed-tools`.

## R6 — Agent Files: Scoped Bash Is a FAIL, Not a Tightening Target

Verified against current official docs (code.claude.com/docs/en/sub-agents): an agent's `tools` frontmatter field has no documented Bash-scoping syntax at all — the only parenthetical-scoping form the platform supports there is `Agent(agent_type, ...)`, a specifically-documented mechanism for restricting which subagents can be spawned, not a general pattern applicable to other tools.

A `Bash(cmd:*)`-style entry inside an agent's `tools` array (as opposed to a skill/command's `allowed-tools` string) is therefore a FAIL in the opposite direction from the usual case: it doesn't function as scoping, so it should be replaced with bare `Bash` (the correct, and only, form for granting Bash to an agent) rather than "fixed" by tightening the scope further.

Flag a scoped-Bash entry found in an agent's `tools` field as REQUIRED — replace with bare `Bash`. This distinction was confirmed after three independent reviewer passes disagreed on it (two flagged the pattern as invalid, one found an internal `agent-development` reference template using it as apparent precedent — that template was itself propagating the same mistake, not real platform support).

## R6 — Bash Scope/Verdict Table (skill and command `allowed-tools` only — not agent `tools` fields)

**This table applies to a skill or command's `allowed-tools` string, the opposite case from the agent-file exception immediately above.** For an agent's `tools` field, ignore this table entirely and apply the reverse rule: bare `Bash` is REQUIRED-correct, and any scoped `Bash(...)` entry is the REQUIRED violation.

| Bash scope | Verdict |
|---|---|
| `Bash` (no scope argument at all) | REQUIRED — unrestricted, equivalent to `Bash(*)` |
| `Bash(*)` | REQUIRED — unrestricted |
| `Bash(sh:*)` `Bash(bash:*)` `Bash(cmd:*)` `Bash(powershell:*)` | REQUIRED — shell interpreters bypass scoping |
| `Bash(git:*)` `Bash(mkdir:*)` `Bash(node:*)` `Bash(python:*)` | PASS — named tool, scoped |
| `Bash(git:* mkdir:*)` | PASS — multiple named tools, each explicit |

## R6 — Format and Tool-Completeness Detail

**Format:** `allowed-tools` may be space-separated (preferred internal style), comma-separated, or a
YAML list.

**Preferred:** `allowed-tools: Read Edit Write Glob`
**Also valid:** `allowed-tools: Read,Edit,Write,Glob` (comma-separated), or a YAML list
**Wrong:** `allowed-tools: Bash(*)` (overly broad) or bare `allowed-tools: Bash` (no scope argument at
all — equally unrestricted)

**Tool completeness:** Every tool invoked in the command or skill body must be declared in
`allowed-tools`. Scan the body for tool name references (`Bash`, `Write`, `Edit`, `Glob`, `Grep`, `Read`,
`WebFetch`, `WebSearch`, etc.) — any tool called but absent from `allowed-tools` is a REQUIRED violation.

**Violation:** Body instructs Claude to run a shell command (Bash) but `Bash(...)` is absent from
`allowed-tools`.

## R6 — Mechanical Assist for the Tool-Completeness Sub-Check

Narrative "scan the body" review missed the tool-completeness violation four independent times in one
week in this repo (PR #54's `cd`, PR #51's `sleep`, PR #52's `grep`/`echo`, PR #61's `git diff` — each
caught only by a later third-party review round, not this check).

Run `${CLAUDE_SKILL_DIR}/scripts/check_tool_grants.py --file <target SKILL.md/command path>` as a first
pass before relying on the narrative scan alone — it mechanically extracts every inline-code command span
and flags one with no matching `Bash(<prefix>:*)` grant. It's a full-file heuristic, not a diff, and
finds candidates rather than confirmed violations: verify each reported line against its surrounding
prose (its own module docstring lists the specific false-positive classes it's known to produce — a
documentation example quoting grant syntax, a command with extra args beyond a wrapped grant, a word
that's also ordinary English, a prose ellipsis/wildcard) before treating it as a REQUIRED finding.
