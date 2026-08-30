---
name: hook-development
description: >-
  Creates and configures event-driven hooks in Claude Code plugins. Covers
  hooks.json structure, hook types (command, http, mcp_tool, prompt, agent),
  all hook events (PreToolUse, PostToolUse, Stop, SessionStart, UserPromptSubmit,
  etc.), stdin data parsing, nested JSON structure, exit code semantics, matchers,
  and production validation. Use when adding hooks to a plugin, writing hooks.json,
  implementing PreToolUse validation, blocking dangerous commands, running
  auto-format on file writes, enforcing completion standards with Stop hooks,
  loading session context at startup, automating responses to Claude Code events,
  or writing/configuring any Claude Code hook event. For reviewing an existing
  hook's quality/safety before deployment, use the hook-reviewer agent instead.
allowed-tools: Read Write Edit Glob Bash(jq:*) Bash(scripts/validate-hook-schema.sh:*) Bash(scripts/test-hook.sh:*) Bash(scripts/hook-linter.sh:*) Bash(shellcheck:*) Bash(claude:*) Skill
---

# Hook Development for Claude Code Plugins

Hooks are event-driven automation scripts that execute in response to Claude Code events. Use them to validate operations, enforce policies, add context, and integrate external tools.

**Key capabilities:** validate before tool runs (PreToolUse), react to results (PostToolUse), enforce completion standards (Stop), load project context (SessionStart).

## Quick Start

1. **Detect project type** — check for `.claude-plugin/plugin.json`; if present, hooks go to `hooks/hooks.json`; otherwise to `.claude/hooks.json`
2. **Choose an event** — `PreToolUse` (validate before), `PostToolUse` (react after), `Stop` (completion check), `SessionStart` (context loading)
3. **Pick a hook type** — prompt (LLM reasoning), command (deterministic bash), or agent (requires file inspection)
4. **Write configuration** — use the nested `"hooks": [...]` array (see CRITICAL section below)
5. **For command hooks** — read event data from stdin, not environment variables (see CRITICAL section below)
6. **Validate** — run `scripts/validate-hook-schema.sh` and `shellcheck` on scripts
7. **Test** — use `scripts/test-hook.sh` with sample input, then `claude --debug` live

*For the full 13-step workflow with tooling auto-detection, lint, and documentation steps, see [Implementation Workflow](#implementation-workflow) below.*

## When to Use

- Adding validation before tool calls (file writes, bash commands, API calls)
- Enforcing project policies at runtime without editing every command
- Loading project context or env vars at session start
- Verifying Claude completes tasks fully before stopping
- Logging, alerting, or auditing tool usage

## When NOT to Use

- For one-time prompts — use slash commands instead
- For global config changes — modify `settings.json` directly
- Never edit `~/.claude/plugins/cache/` — those are read-only installed copies
- Reviewing an existing hook's quality/safety before deployment → use the `hook-reviewer` agent instead

## Finding-ID Fix Mode

When invoked with a bounded finding-ID list (e.g. from `plugin-lifecycle-downstream`'s Phase
4/6/8), follow `plugin-rulebook/references/finding-id-fix-contract.md` instead of this
skill's normal open-ended workflow: touch only the named findings' files, report per-ID
`applied`/`deferred`/`failed` status, and never mark a fix verified — that stays the
originating checker's job.

---

## CRITICAL: Hook File Location

**Most common mistake:** placing hooks in `.claude-plugin/hooks.json` (WRONG).

✅ **Correct locations:**
- **Plugin projects** (has `.claude-plugin/plugin.json`): `hooks/hooks.json` at plugin root
- **Regular projects** (no `.claude-plugin/`): `.claude/hooks.json`

❌ **Wrong:** `.claude-plugin/hooks.json` — only `plugin.json` belongs in `.claude-plugin/`

**Auto-detect:** check for `.claude-plugin/plugin.json`; its presence means plugin project. If hooks aren't firing, check file location first.

---

## CRITICAL: Command Hooks Receive Data via Stdin

**The #1 reason command hooks silently do nothing:** expecting environment variables instead of reading stdin.

❌ **WRONG — env var substitution does NOT work:**
```json
{ "env": {"FILE_PATH": "${arguments.file_path}"} }
```

✅ **CORRECT — read ALL event data from stdin as JSON:**
```bash
#!/bin/bash
INPUT=$(cat)                                          # Read all event data from stdin
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path')
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name')
```

See `references/command-hook-input-parsing.md` for correct field paths per event type.

---

## CRITICAL: Nested "hooks" Array JSON Structure

**The #1 JSON mistake:** forgetting the nested `"hooks": [...]` array inside each event matcher.

✅ **CORRECT — required for all hooks:**
```json
{
  "hooks": {
    "EventName": [
      {
        "matcher": "regex-pattern",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/scripts/script.sh",
            "timeout": 5000,
            "onError": "warn"
          }
        ]
      }
    ]
  }
}
```

❌ **WRONG — produces "Expected array, but received undefined":**
```json
{
  "hooks": {
    "EventName": [{ "type": "command", "command": "..." }]
  }
}
```

Every hook action (command, http, mcp_tool, prompt, agent) **must** be inside a `"hooks": [...]` array.

---

## Hook Types

Five action types: `prompt` (LLM-driven, flexible), `command` (bash, deterministic), `agent` (multi-turn, file inspection), `http` (webhook), `mcp_tool` (calls an installed MCP server tool). Full field reference and JSON example per type: `references/hook-types.md` (`mcp_tool` has its own dedicated reference, `references/mcp-tools.md`).

**Type decision:**

| Use Case | Type |
|---|---|
| Fast deterministic check (lint, file size, path regex) | command |
| Intelligent reasoning (context-aware, needs judgment) | prompt |
| Verification requiring file inspection or test runs | agent |
| Complex branches or state checks | command |
| Call an installed MCP server tool | mcp_tool |
| Notify or delegate to an external system | http |

Not every type is valid for every event (e.g. `SessionStart` supports only `command` and `mcp_tool`) — validate the type/event combination, not just each independently. Full compatibility matrix: `references/event-reference.md`.

---

## Hook Configuration Formats

### Plugin Format (`hooks/hooks.json`)

```json
{
  "description": "Optional description",
  "hooks": {
    "PreToolUse": [...],
    "Stop": [...],
    "SessionStart": [...]
  }
}
```

### Settings Format (`.claude/settings.json` or `.claude/hooks.json`)

```json
{
  "PreToolUse": [...],
  "Stop": [...],
  "SessionStart": [...]
}
```

Events go directly at the top level — no wrapper object. Plugin hooks merge with user hooks and run in parallel. Settings format also supports a top-level `disableAllHooks` boolean key to disable every configured hook at once — verify whether this applies to plugin `hooks/hooks.json` too before relying on it there.

`hooks/hooks.json` has only two top-level keys: `description` and `hooks` — verify this against the current platform schema before enforcing it. Shared team hooks belong in `.claude/settings.json` (checked into version control) — never in `.claude/settings.local.json`, which is personal and gitignored.

---

## Hook Handler Fields

All handlers:

| Field | Required | Description |
|---|---|---|
| `type` | yes | `"command"`, `"http"`, `"mcp_tool"`, `"prompt"`, or `"agent"` |
| `timeout` | no | Seconds before canceling. Defaults: command=600, prompt=30, agent=60. Flag values outside 1-600s as suspect |
| `statusMessage` | no | Custom spinner text while hook runs |
| `once` | no | Run once per session then auto-remove. **Only honored in skill frontmatter hooks** — ignored in settings files and agent frontmatter |
| `if` | no | Exactly one permission rule — no `&&`, `\|\|`, or list syntax. Use separate handlers for multiple conditions |

Command-only:

| Field | Required | Description |
|---|---|---|
| `command` | yes | Shell command to execute |
| `args` | no | Array of arguments — when present, `command` runs as an executable (exec form, no shell interpretation) instead of being passed to a shell |
| `async` | no | `true` = background, non-blocking, command hooks only. Cannot block, cannot return decisions, and delivers output on a later turn — never use for safety gates |
| `asyncRewake` | no | Background mode only — wake Claude when the async hook exits with code 2 |
| `shell` | no | Shell used to run `command` — `"bash"` or `"powershell"` |

Prompt/Agent-only:

| Field | Required | Description |
|---|---|---|
| `prompt` | yes | Prompt text; use `$ARGUMENTS` as placeholder for the hook's full JSON input |
| `model` | no | Model override (defaults to Haiku) |

HTTP-only:

| Field | Required | Description |
|---|---|---|
| `url` | yes | Endpoint to POST event data to |
| `headers` | no | Custom HTTP headers |
| `allowedEnvVars` | no | Env vars permitted to be forwarded to the request |

MCP Tool-only:

| Field | Required | Description |
|---|---|---|
| `server` | yes | MCP server name |
| `tool` | yes | Tool name on that server |

---

## Hook Events

| Event | When | Can Block? | Use For |
|---|---|---|---|
| `PreToolUse` | Before tool runs | ✅ Yes | Validate, deny, modify tool input |
| `PermissionRequest` | Permission dialog | ✅ Yes | Auto-allow/deny permissions |
| `PostToolUse` | After tool (success) | ❌ No | Feedback, logging, follow-up |
| `PostToolUseFailure` | After tool (failure) | ❌ No | Error guidance, alerts |
| `UserPromptSubmit` | User submits prompt | ✅ Yes | Add context, validate, block |
| `Stop` | Agent about to stop | ✅ Yes | Completeness check |
| `SubagentStop` | Subagent about to stop | ✅ Yes | Subagent task validation |
| `SubagentStart` | Subagent spawned | ❌ No | Inject context into subagent |
| `SessionStart` | Session begins | ❌ No | Load context, set env vars |
| `SessionEnd` | Session ends | ❌ No | Cleanup, logging |
| `PreCompact` | Before context compact | ❌ No | Preserve critical context |
| `Notification` | Claude sends notification | ❌ No | React to notifications |
| `WorktreeCreate` | Worktree created | ⚠️ Special | Must return the absolute path of the created worktree — not a standard allow/block decision |

This is not the full event list — Claude Code also ships `Setup`, `UserPromptExpansion`, `PostToolBatch`, `MessageDisplay`, `TeammateIdle`, `TaskCreated`, `TaskCompleted`, `WorktreeRemove`, `CwdChanged`, `PermissionDenied`, `StopFailure`, `InstructionsLoaded`, `ConfigChange`, `FileChanged`, `PostCompact`, `Elicitation`, and `ElicitationResult`. Full list, per-event payloads, and the hook-type/event compatibility matrix: `references/event-reference.md`.

**⚠️ Stop/SubagentStop infinite loop guard** — always check `stop_hook_active`:
```bash
INPUT=$(cat)
if [ "$(echo "$INPUT" | jq -r '.stop_hook_active')" = "true" ]; then
  exit 0  # Already in hook-triggered continuation — allow stop
fi
```

For per-event data payloads, timing, matcher values, and output schemas, see `references/event-reference.md` and `references/decision-schemas.md`.

---

## Matchers

```json
"matcher": "Write"           // Exact tool name
"matcher": "Read|Write|Edit" // Multiple tools
"matcher": "*"               // All tools (use sparingly)
"matcher": "mcp__.*__delete" // Regex — all MCP delete tools
```

Matchers are **case-sensitive**. Events that match on something other than tool name:

| Event | Matches on |
|---|---|
| `SubagentStart/Stop` | Agent type (`Bash`, `Explore`, custom names) |
| `SessionStart` | How session started (`startup`, `resume`, `clear`, `compact`) |
| `SessionEnd` | Why session ended (`clear`, `logout`, `prompt_input_exit`, `other`) |
| `Notification` | Notification type (`permission_prompt`, `idle_prompt`, `auth_success`) |
| `PreCompact` | What triggered it (`manual`, `auto`) |
| `Stop`, `UserPromptSubmit`, `TeammateIdle`, `TaskCreated`, `TaskCompleted`, `WorktreeCreate`, `WorktreeRemove`, `CwdChanged` | No matcher support — always fires (verify current list against `references/event-reference.md`) |

---

## Environment Variables

Available in a `hooks/hooks.json`/`.claude/hooks.json` command hook:

| Variable | Description |
|---|---|
| `$CLAUDE_PROJECT_DIR` | Project root path |
| `$CLAUDE_PLUGIN_ROOT` | Plugin installation dir — use for portable file references in `hooks.json` |
| `$CLAUDE_ENV_FILE` | **SessionStart only** — append `export VAR=val` here to persist env vars for the session |
| `$CLAUDE_CODE_REMOTE` | Set if running in remote context |

**A skill/agent frontmatter-embedded `hooks:` block is different:** `$CLAUDE_PLUGIN_ROOT` is not
confirmed available there, and is confirmed broken for a project-level skill (no enclosing plugin) —
see `references/component-scoped-hooks.md`'s "Environment Variables Available" section for the
confirmed-working alternative (a relative path, or `$CLAUDE_PROJECT_DIR` with the full path).

---

## Exit Codes & Output Contract

| Exit Code | Meaning |
|---|---|
| `0` | Pass/continue |
| `2` | Block — stderr content is fed to Claude |
| other | Non-blocking warning — logged, execution continues |

Some events have exceptions to this contract (e.g. `SessionStart` never blocks) — see `references/exit-code-behavior.md`. Blocking/error messages go to stderr; informational context output goes to stdout.

A hook must pick one signaling mode: exit-code mode, or structured JSON on stdout with exit `0`. JSON output is ignored whenever the exit code is `2`. All hook output (stdout, `additionalContext`, `systemMessage`) is capped at 10,000 characters — summarize large results and write details to a file. HTTP hooks cannot block via a non-2xx status; return `2xx` with a JSON decision body instead.

Full semantics and JSON schemas: `references/exit-code-behavior.md`, `references/decision-schemas.md`.

---

## Performance & Safety

- Each hook should complete in under 5 seconds; hooks that regularly exceed this may be disabled by Claude Code
- Keep total hook execution time across all matching hooks under ~30 seconds with parallel processing
- Filter by event type, tool name, file path, and extension before doing expensive work — never scan the whole project inside a hook
- Cap displayed findings to 5-10 items; emit a summary line if more exist
- Prefer Python for cross-platform hook scripts; use `pathlib.Path` for all paths — never hardcode `/tmp/` or OS-specific separators. Portable runner fallback: `uv` → `python3` → `python` (see `references/patterns-and-templates.md`)
- Never use `shell=True` with string commands — use list arguments. Parse stdin as structured JSON and never interpolate raw input into shell commands (see `references/patterns-and-templates.md` and `references/validation-guide.md`)
- Command hooks run with the full permissions of the current system user — treat every hook script as privileged local code
- Hooks must not open `/dev/tty` or send escape sequences directly to the interface; use the JSON `systemMessage` field instead

---

## Common Workflow Patterns

| Pattern | Events | Description |
|---|---|---|
| Auto-format chain | PostToolUse (Write\|Edit) | Run Prettier → ESLint → TypeScript check on every file write |
| Test-on-save | PostToolUse (Write\|Edit) | Locate and run the corresponding test file |
| Observability pipeline | SessionStart + PreToolUse + PostToolUse + SessionEnd | Log session init, tool attempts, results, and summary |
| Security guardrails | PreToolUse (Write\|Edit\|Bash) | Multi-layer: path traversal → permission → allowlist |
| Context loading | SessionStart (startup) | Load project docs, check git status, validate environment |

---

## Implementation Workflow

For a `hooks/hooks.json`/`.claude/hooks.json` hook. For a skill/agent frontmatter-embedded `hooks:`
block instead, see `references/component-scoped-hooks.md` — step 7 below does not apply there.

1. **Detect project type** — check for `.claude-plugin/plugin.json` to pick correct hooks file location
2. **Auto-detect tooling** to suggest relevant hooks:
   - `tsconfig.json` → PostToolUse type-check hook
   - `.prettierrc` → PostToolUse auto-format hook
   - `.eslintrc.*` → PostToolUse lint hook
   - `package.json` with `test` script → Stop test-validation hook
   - Git repository → PreToolUse security scan hook
3. **Identify events** — use the Hook Events table above
4. **Choose hook type** — prompt (flexible), agent (requires file inspection), command (deterministic)
5. **Write configuration** — ensure nested `"hooks": [...]` array is present
6. **For command hooks** — read all data from stdin (`INPUT=$(cat)`)
7. **Use `${CLAUDE_PLUGIN_ROOT}`** for all file references (this step is `hooks.json`-specific — see the note above)
8. **Add `stop_hook_active` guard** to all Stop/SubagentStop hooks
9. **Validate configuration** — `scripts/validate-hook-schema.sh hooks/hooks.json`
10. **Lint scripts** — `shellcheck scripts/my-hook.sh`
11. **Test happy and sad paths** — `scripts/test-hook.sh` with valid and invalid inputs
12. **Test live** — `claude --debug`; look for hook registration and execution logs
13. **Document hooks** in plugin README; validate against `references/validation-guide.md`

**Optional (TDD-style):** define the behavior violation you want to prevent first, then write the hook, then review.

---

## Testing & Validation

After writing or modifying hooks:

1. **JSON structure** — `jq empty hooks/hooks.json && echo "Valid"` before anything else
2. **Schema validation** — `scripts/validate-hook-schema.sh hooks/hooks.json`
3. **Script lint** — `shellcheck scripts/my-hook.sh` for all command hook scripts
4. **Manual test** — pipe sample event JSON and check exit code and stdout:
   ```bash
   bash scripts/my-hook.sh <<< '{"tool_name":"Write","tool_input":{"file_path":"/test.txt"}}'
   echo "Exit: $?"
   ```
5. **Live test** — restart Claude Code, trigger the hooked event, check `claude --debug` output

**Quality gates:**
- [ ] `jq empty` passes on hooks.json
- [ ] `shellcheck` passes on all hook scripts (zero warnings)
- [ ] Happy path: valid input → hook passes (exit 0)
- [ ] Sad path: invalid/blocked input → hook fires correctly (exit 2 + stderr)
- [ ] Stop hooks include `stop_hook_active` guard
- [ ] `scripts/validate-hook-schema.sh` reports no errors

**Deep Test coverage for a hook:** step 4's "Manual test" above exercises one sample input by
hand — Deep Test coverage means running `scripts/test-hook.sh --create-sample <event-type>`
for every event type the hook's own `matcher` in `hooks.json` actually configures it to
receive, then running `scripts/test-hook.sh` against each generated sample (a happy-path
input and, where meaningful, a blocked-path input) rather than just one. `scripts/test-hook.sh
--json`/`--yaml` emits a machine-readable `status: pass|fail` result per run (plus
`exit_code`/`classification`/`output`) so a caller aggregating results across every event
type — e.g. `plugin-lifecycle-downstream`'s optional Deep Test step — doesn't have to parse
the human-readable text output.

**Verify this skill activates on:**
- "add a hook to this plugin" / "write hooks.json"
- "implement PreToolUse validation to block dangerous commands"
- "auto-format on every file write" / "enforce completion standards with a Stop hook"
- "load session context at startup" / "automate a response to a Claude Code event"

**Verify it does NOT activate on:**
- "just run this once" → a slash command, not a hook
- "change a global config setting" → edit `settings.json` directly instead
- "review this existing hook's quality/safety before I ship it" → the `hook-reviewer` agent instead

**Last dated run record:** 2026-08-30, `evals/hook-development/` — 3/3 scenarios,
8/8 assertions passed (Quick Workflow, `with_skill` only — see `evals/hook-development/evals.json`).
2 of 4 declared trigger scenarios aren't yet exercised by an eval (auto-format-on-write, session-context
loading) — see `evals.json`'s `testing_validation_coverage` field.

---

## Additional Resources

| Reference | Purpose |
|---|---|
| `references/hook-types.md` | Full field reference and JSON example for each of the 5 hook action types |
| `references/event-reference.md` | Complete event docs: data payloads, timing, matcher values |
| `references/decision-schemas.md` | Output schemas for prompt/agent/command hooks by event |
| `references/exit-code-behavior.md` | Exit code semantics (0/1/2) with per-event scenarios |
| `references/command-hook-input-parsing.md` | Stdin field paths and bash parsing patterns per event |
| `references/patterns-and-templates.md` | 11 common patterns and copy-paste templates for all hook types |
| `references/advanced-hooks.md` | 18 advanced patterns: rate limiting, caching, retry, cross-event workflows, external integrations |
| `references/how-hooks-work.md` | Lifecycle, execution model, `onError`, hot-reload limits |
| `references/validation-guide.md` | 7-phase systematic validation; production checklists; troubleshooting |
| `references/migration.md` | Migrating command hooks to prompt hooks |
| `references/component-scoped-hooks.md` | Hooks scoped to skills and subagents via YAML frontmatter |
| `references/mcp-tools.md` | Hook patterns for MCP tool events |

| Example | Contents |
|---|---|
| `examples/validate-write.sh` | File write validation with path safety checks |
| `examples/validate-bash.sh` | Bash command validation and allowlist |
| `examples/load-context.sh` | SessionStart context loading with `$CLAUDE_ENV_FILE` |

| Script | Purpose |
|---|---|
| `scripts/validate-hook-schema.sh` | Validate hooks.json structure and syntax |
| `scripts/test-hook.sh` | Test hooks with sample input before deployment |
| `scripts/hook-linter.sh` | Check hook scripts for common issues |
| `plugin-rulebook` | Plugin-level rules — invoke before finalizing any hook to check naming, language, formatting, tool-scoping, and external-reference compliance |
