# Hook Validation Guide

Systematic 7-phase validation process and production checklists for creating and validating Claude Code hooks.

## Table of Contents

- [Quick Validation Checklist](#quick-validation-checklist)
- [New Hook Creation Checklist](#new-hook-creation-checklist)
- [7-Phase Validation Process](#7-phase-validation-process)
  - [Phase 1: Event Correctness](#phase-1-event-correctness)
  - [Phase 2: Matcher Analysis](#phase-2-matcher-analysis)
  - [Phase 3: Hook Type & Action](#phase-3-hook-type--action)
  - [Phase 4: Error Handling](#phase-4-error-handling)
  - [Phase 5: Performance Impact](#phase-5-performance-impact)
  - [Phase 6: Integration & Side Effects](#phase-6-integration--side-effects)
  - [Phase 7: Testing & Documentation](#phase-7-testing--documentation)
- [Security & Injection Prevention](#security--injection-prevention)
- [Existing Hook Validation Checklist](#existing-hook-validation-checklist)
- [Hook-Type Specific Checklists](#hook-type-specific-checklists)
- [Production & Team Hooks Checklist](#production--team-hooks-checklist)
- [Common Hook Patterns](#common-hook-patterns)
- [Troubleshooting Checklist](#troubleshooting-checklist)
- [When a Hook Fails Validation](#when-a-hook-fails-validation)
- [Sign-Off Checklist](#sign-off-checklist)

---

## Quick Validation Checklist

Use this for rapid validation of any hook:

- [ ] Phase 1: Event correct for hook's purpose
- [ ] Phase 2: Matcher is precise and syntactically valid
- [ ] Phase 3: Hook type matches action, action is safe, timeout exists
- [ ] Phase 4: Error handling defined, hook fails gracefully
  - [ ] **CRITICAL: Exit codes correct** (0=success, 2=blocking errors Claude sees, 1=non-blocking)
  - [ ] If blocking validation: uses `exit 2` for errors
  - [ ] If optional logging: uses `exit 0` or `exit 1`
  - [ ] onError behavior matches exit code strategy
- [ ] Phase 5: Hook executes quickly, doesn't trigger excessively
- [ ] Phase 6: Hook is idempotent, safe with concurrent execution
- [ ] Phase 7: Hook tested with real scenarios, documented
  - [ ] **Command hook script passes shellcheck** (run: `shellcheck script.sh`)
  - [ ] No unquoted variables (SC2086)
  - [ ] No useless echo/pipes (SC2005)
  - [ ] Proper exit codes used

---

## New Hook Creation Checklist

Use when creating a hook from scratch.

### Foundation
- [ ] **Hook purpose is clear** — Can describe in 1 sentence what the hook does
- [ ] **Problem it solves** — Why is this hook needed? What problem does it address?
- [ ] **Event selected** — Right event for the hook's purpose (Pre vs Post, which event?)
- [ ] **Matcher criteria defined** — When should hook execute within that event?
- [ ] **Hook type chosen** — Command, prompt, or agent? Why?

### Configuration
- [ ] **JSON structure correct** — Hook wrapped in `"hooks": [...]` array (see structure below)
- [ ] **Event syntax correct** — Event name matches Claude Code event names
- [ ] **Matcher syntax valid** — Regex is correct, special chars escaped
- [ ] **Matcher tested** — Tested with 3+ scenarios (matches when should, doesn't when shouldn't)
- [ ] **Hook type valid** — "command", "http", "mcp_tool", "prompt", or "agent"
- [ ] **Action is specified** — Command path, URL, MCP server/tool, prompt text, or agent reference

**Required JSON structure (NON-NEGOTIABLE):**
```json
{
  "hooks": {
    "EventName": [
      {
        "matcher": "pattern",
        "hooks": [
          { "type": "command", "command": "...", "timeout": 5000 }
        ]
      }
    ]
  }
}
```

❌ **Common mistake:** Direct hook without `"hooks"` wrapper causes `"Expected array, but received undefined"` error.

### Command Hook Configuration
- [ ] **Script passes shellcheck** — Run `shellcheck script.sh`, fix all warnings
- [ ] **Script exists** — File path is correct and file exists
- [ ] **Script executable** — Has execute permissions on Unix/Linux
- [ ] **Uses ${CLAUDE_PLUGIN_ROOT}** — Relative path, not hardcoded absolute path
- [ ] **Timeout specified** — Has reasonable timeout (e.g., 2000ms for formatting, 5000ms for validation)
- [ ] **No shell injection** — Arguments properly quoted/escaped
- [ ] **Error output captured** — Script has clear error messages to stderr

### Error Handling
- [ ] **onError defined** — Behavior when hook fails (warn, fail, continue)
- [ ] **Validation before execution** — Checks input/state before running
- [ ] **Graceful failure** — Fails without crashing plugin
- [ ] **Error message useful** — User can debug what went wrong
- [ ] **Recovery possible** — Plugin can continue if hook fails

### Integration Safety
- [ ] **No race conditions** — Safe if multiple hooks trigger simultaneously
- [ ] **Idempotent** — Safe to run multiple times without side effects
- [ ] **Atomic operations** — File writes are atomic (temp + move)
- [ ] **Plugin state assumptions** — Only assumes state that exists

### Testing
- [ ] **Real scenario testing** — Tested with actual plugin workflow
- [ ] **Success path tested** — Hook executes correctly when should trigger
- [ ] **Negative path tested** — Hook doesn't execute when shouldn't trigger
- [ ] **Failure path tested** — Hook handles errors gracefully
- [ ] **Performance tested** — Executes in acceptable time (<1s for sync)

---

## 7-Phase Validation Process

Apply these phases when validating any existing hook.

---

### Phase 1: Event Correctness

**Question:** Is the hook attached to the right event?

| Event | When It Fires | Best For | Common Mistakes |
|-------|---------------|----------|-----------------|
| PreToolUse | Before any tool executes | Validation, blocking | Waiting for result (use PostToolUse) |
| PostToolUse | After tool succeeds | Formatting, logging | Trying to block (use PreToolUse) |
| PostToolUseFailure | After tool fails | Error recovery, logging | Modifying failed result (immutable) |
| UserPromptSubmit | After user submits prompt | Parsing, validation | Blocking Claude (async only) |
| SessionStart | Session begins | Initialization, setup | Assuming environment ready |
| SessionEnd | Session ends | Cleanup, teardown | Trying to modify session state |
| PreCompact | Before history compaction | Backup, archiving | Modifying compact operation |
| PermissionRequest | Permission dialog shown | Approval workflow | Blocking user interaction |
| Stop | Agent about to stop | Completeness check | Forgetting `stop_hook_active` guard |

**Validation steps:**
1. What is the hook's primary purpose?
2. When should it execute? (Before/after what action?)
3. Which event matches that timing?
4. Can this hook achieve its goal on that event?

**Pass criteria:** Event selection makes logical sense for hook's purpose. Pre vs Post timing is correct.

---

### Phase 2: Matcher Analysis

**Question:** Will the hook trigger at the right times (not too often, not too rarely)?

**Validation steps:**
1. What conditions must be true for hook to execute?
2. Is the matcher syntactically correct? (Valid regex, correct operator syntax)
3. Does matcher use correct tool/field names?
4. Is matcher too broad? (Will it trigger unwanted times?)
5. Is matcher too narrow? (Will it miss intended cases?)

**Common matcher mistakes:**

| Mistake | Problem | Fix |
|---------|---------|-----|
| `.*` | Matches everything (performance killer) | Use specific tool name or pattern |
| `Write` (no anchors) | May match "DeviceWrite" or similar | `^Write$` for exact match |
| `Write\|Edit` (no anchors) | Partial matches possible | `^(Write\|Edit)$` |
| Tool names wrong | Check against event reference | Verify with `references/event-reference.md` |
| Regex syntax errors | Invalid patterns fail silently | Test regex separately |

**Example validation:**
```json
{
  "matcher": "^(Write|Edit)$"
}
```
✓ Precise: matches exactly Write or Edit tool names

**Pass criteria:** Matcher is syntactically valid, specific enough to avoid false triggers, and matches all intended use cases. Tested with multiple scenarios.

---

### Phase 3: Hook Type & Action

**Question:** Is the hook type appropriate for the action?

| Hook Type | Use Cases | Safety Concerns | Common Issues |
|-----------|-----------|-----------------|---------------|
| command | Validation, formatting, cleanup | Command injection, timeouts, shell escaping | Missing timeout, unsanitized input |
| prompt | LLM-based decisions, logic | Token cost, latency, consistency | Vague prompts, missing context |
| agent | Complex workflows, verification | Token cost, tool access, error states | Over-scoped tools, missing fallback |

**Validation steps:**
1. Is hook type appropriate for action?
2. Is the action safe to execute? (No shell injection, no data loss)
3. Are inputs sanitized? (Command hooks: escape shell args)
4. Is there a timeout? (Prevent hangs)
5. What happens if action fails?

**Command hook safety checklist:**
- Uses `${CLAUDE_PLUGIN_ROOT}` for paths (not hardcoded)
- Arguments are properly quoted
- Script exists and is executable
- No network dependencies without timeout
- Timeout < 5 seconds for blocking operations

**Pass criteria:** Hook type matches action, action is safe, timeout is reasonable, failure mode is clear.

---

### Phase 4: Error Handling

**Question:** Will hook fail gracefully without breaking plugin?

**Validation steps:**
1. What can fail? (Command timeout, network error, script crash, invalid input)
2. Is there validation before action executes?
3. **Does script use correct exit codes?** (Critical: 0=success, 2=blocking error, 1=non-blocking)
4. What happens if action fails? (Warn, block, continue?)
5. Is error message useful? (Can user debug?)
6. Can plugin recover?

**Exit code validation (CRITICAL):**
- **Does script need to communicate errors to Claude?**
  - YES → Must use `exit 2` for errors so Claude sees stderr message
  - NO → Use `exit 0` for success, `exit 1` for ignorable failures
- **Is exit code matched to hook purpose?**
  - Blocking validation → exit 2 (shows error to Claude)
  - Optional logging → exit 0 or 1 (errors don't matter)
  - Async background work → exit 0 or 1 (failures don't block execution)

**Error scenarios to consider:**
- Command timeout (script hangs)
- Matcher fails to evaluate (invalid syntax)
- Hook configuration error (wrong JSON)
- Missing script/resource (path doesn't exist)
- Permission denied (script not executable)

**Example error handling:**
```json
{
  "type": "command",
  "command": "${CLAUDE_PLUGIN_ROOT}/scripts/format.sh",
  "timeout": 5000,
  "onError": "warn"
}
```

**Pass criteria:** Hook has timeout, onError behavior defined, and fails without crashing plugin. Error is logged/visible.

---

### Phase 5: Performance Impact

**Question:** Will hook slow down Claude Code noticeably?

**Validation steps:**
1. Is hook synchronous or async? (Sync = blocks Claude)
2. How long does hook action take? (<1s preferred for sync)
3. How often does hook trigger? (Every tool use = high frequency)
4. Is there conditional logic to skip unnecessary execution?
5. Is matcher optimized? (Avoid `.*` or expensive regex)

**Performance red flags:**
- Sync network calls (command hook hitting API)
- Expensive regex matchers on every event
- Frequent triggers (PostToolUse on every single tool with `.*`)
- No timeout (runaway processes)

**Example: Too slow**
```json
{
  "event": "PostToolUse",
  "matcher": ".*",
  "hooks": [{
    "type": "command",
    "command": "curl https://api.example.com/..."
  }]
}
```

**Example: Better**
```json
{
  "event": "PostToolUse",
  "matcher": "^(Write|Edit)$",
  "hooks": [{
    "type": "command",
    "command": "${CLAUDE_PLUGIN_ROOT}/scripts/format.sh",
    "timeout": 2000
  }]
}
```

**Pass criteria:** Hook executes quickly (<1s), doesn't trigger excessively, matcher is efficient.

---

### Phase 6: Integration & Side Effects

**Question:** Will hook interact safely with plugin and other hooks?

**Validation steps:**
1. Does hook assume plugin state? (Will state exist?)
2. Does hook modify file system? (Could collide with other operations?)
3. Could multiple hooks trigger simultaneously? (Race conditions?)
4. Is hook idempotent? (Safe to run multiple times?)

**Common integration issues:**
- Hook modifies file, then another hook reads stale version
- Hook assumes directory exists (not created yet)
- Two hooks write same file concurrently (data loss)
- Hook expects specific plugin state (might not exist)

**Safer integration pattern:**
```bash
# Check existence before modifying
[ -f "$FILE" ] || exit 0

# Write atomically (temp file + move)
echo "$NEW_CONTENT" > "$FILE.tmp"
mv "$FILE.tmp" "$FILE"
```

**Pass criteria:** Hook is idempotent, uses atomic operations, doesn't assume external state, safe with concurrent execution.

---

### Phase 7: Testing & Documentation

**Question:** Has hook been tested? Is it documented?

**Validation steps:**
1. **Command hook script passes shellcheck** (if using command hooks)
   - Run: `shellcheck /path/to/script.sh`
   - Fix all warnings (SC2086 unquoted vars, SC2005 useless echo, etc.)
2. Hook tested with real plugin scenarios?
3. Tested matcher with multiple cases? (True positives and negatives)
4. Tested failure case? (What if action fails?)
5. Tested performance? (Reasonable execution time?)
6. Is hook documented? (Comments explaining matcher, action, failure mode)

**Test scenarios for format-on-write hook:**
```
✓ Write to .js file → matcher matches → hook executes → formatting applied
✗ Read from .js file → matcher fails → hook doesn't execute
✗ Write to .txt file → matcher fails → hook doesn't execute
✓ Format fails → timeout or error → logged, Claude continues
```

**Pass criteria:**
- Command hooks pass shellcheck with no warnings
- Hook tested with real scenarios
- Handles both success and failure cases
- Documented clearly with inline comments

---

## Security & Injection Prevention

**Command hooks run with the full permissions of the current system user.** There is no sandbox — treat every hook script as privileged local code, review it before enabling it, and apply the same scrutiny you would to any other unattended executable.

**Injection-prevention rules:**
- Never use `shell=True` with a string command in a Python `subprocess` call — pass a list of arguments instead
- Parse all stdin input as structured JSON (`json.load(sys.stdin)`); never interpolate raw stdin text into a shell command string

```python
import json
import subprocess
import sys

data = json.load(sys.stdin)
file_path = data["tool_input"]["file_path"]

# WRONG: string command + shell=True is injectable
# subprocess.run(f"cat {file_path}", shell=True)

# CORRECT: list arguments, no shell
subprocess.run(["cat", file_path], check=False)
```

**Official security checklist** — apply to every command hook script:
- Validate and sanitize all input before using it
- Quote every shell variable (`"$VAR"`, never bare `$VAR`)
- Reject path traversal (`..`) in any path derived from event data
- Use absolute paths for the script itself (`${CLAUDE_PLUGIN_ROOT}/scripts/...`)
- Skip sensitive files — `.env`, `.git/`, private keys, credentials — never read or write them from a hook unless that is the hook's explicit, reviewed purpose

---

## Existing Hook Validation Checklist

Use when auditing existing hooks against best practices.

### Phase 1: Event Correctness
- [ ] **Event matches hook purpose** — Right event for what hook does?
- [ ] **Event timing correct** — Pre vs Post makes sense?
- [ ] **Event has needed data** — Required fields available on that event?
- [ ] **No timing assumptions** — Doesn't assume state that doesn't exist?

### Phase 2: Matcher Quality
- [ ] **Matcher syntax valid** — No regex errors or typos
- [ ] **Matcher tested** — Verified with multiple test cases
- [ ] **Not too broad** — Doesn't match unintended cases
- [ ] **Not too narrow** — Matches all intended cases
- [ ] **Performance acceptable** — No expensive regex patterns
- [ ] **Documented** — Comments explain what matcher does

### Phase 2.5: JSON Structure (CRITICAL)
- [ ] **Hooks wrapped in array** — All hooks under `"hooks": [...]` (not direct properties)
- [ ] **Matcher in correct place** — `"matcher"` is sibling of `"hooks"` array, not inside it
- [ ] **Valid JSON syntax** — No trailing commas, quotes properly closed
- [ ] **Correct nesting** — Event → matchers → hooks array

**Correct structure:**
```json
{
  "hooks": {
    "EventName": [
      {
        "matcher": "pattern",
        "hooks": [
          { "type": "command", "command": "...", "timeout": 5000 }
        ]
      }
    ]
  }
}
```

### Phase 3: Hook Type & Action
- [ ] **Hook type appropriate** — Command/prompt/agent fits the action
- [ ] **Action is safe** — No shell injection, data loss, or security risks
- [ ] **Paths are portable** — Uses `${CLAUDE_PLUGIN_ROOT}`, not hardcoded
- [ ] **Resources exist** — Referenced scripts/files/agents exist
- [ ] **Permissions correct** — Executable files have execute perms

### Phase 4: Error Handling
- [ ] **Timeout exists** — Prevents hangs (command hooks especially)
- [ ] **onError behavior defined** — Hook knows what to do if it fails
- [ ] **Validation exists** — Checks inputs/state before executing
- [ ] **Error messages clear** — User can understand what went wrong
- [ ] **Plugin survives failure** — Doesn't crash if hook fails
- [ ] **Exit codes correct** — exit 0 (success), exit 2 (blocking error), exit 1 (non-blocking)

### Phase 5: Performance
- [ ] **Execution time acceptable** — <1s for sync hooks
- [ ] **Trigger frequency reasonable** — Doesn't trigger on every event
- [ ] **Matcher optimized** — No expensive regex patterns
- [ ] **No blocking I/O** — Network calls have timeout
- [ ] **No busy loops** — Doesn't spin waiting for conditions

### Phase 6: Integration
- [ ] **Idempotent** — Safe to run multiple times
- [ ] **Atomic operations** — File operations don't leave partial state
- [ ] **No race conditions** — Safe with concurrent hooks
- [ ] **File conflicts avoided** — Doesn't collide with other operations

### Phase 7: Testing
- [ ] **Success case tested** — Verified hook works when should trigger
- [ ] **Negative case tested** — Verified hook doesn't trigger when shouldn't
- [ ] **Error case tested** — Verified graceful failure
- [ ] **Performance tested** — Execution time measured
- [ ] **Integration tested** — Works with other plugin components
- [ ] **Command hook script passes shellcheck** — Zero warnings

---

## Hook-Type Specific Checklists

### Command Hook Checklist

#### Safety
- [ ] **Script exists and is accessible** — File path correct, readable
- [ ] **Script is executable** — Has execute permissions
- [ ] **No hardcoded paths** — Uses `${CLAUDE_PLUGIN_ROOT}` for plugin files
- [ ] **No shell injection** — Arguments properly quoted
- [ ] **Inputs validated** — Checks args/env vars before using
- [ ] **No `eval` or `exec`** — Especially with user input
- [ ] **No credentials** — Doesn't hardcode secrets
- [ ] **Timeout enforced** — Won't hang indefinitely

#### Reliability
- [ ] **Exit codes correct** — Script uses exit codes properly (0/1/2)
- [ ] **Error messages to stderr** — Errors written to stderr
- [ ] **Stdout used for output** — Only output goes to stdout
- [ ] **Handles missing deps** — Graceful error if dependencies missing
- [ ] **Idempotent** — Multiple runs don't cause issues
- [ ] **Atomic file ops** — Writes temp file, then moves

#### Performance
- [ ] **Script is fast** — <1s for sync operations
- [ ] **No unnecessary overhead** — Startup/teardown is quick
- [ ] **Timeout reasonable** — Not too short (script can't complete), not too long (hangs)

#### Debugging
- [ ] **Verbose logging available** — Can enable debug output
- [ ] **Error messages clear** — User can understand failure
- [ ] **Script testable standalone** — Can run script directly to test

---

### Prompt Hook Checklist

#### Prompt Quality
- [ ] **Prompt is clear** — Claude understands what to evaluate
- [ ] **Context included** — Prompt uses `$ARGUMENTS` for event context
- [ ] **Specific instructions** — What should Claude decide?
- [ ] **Output format defined** — How should Claude respond?
- [ ] **Not over-scoped** — Single decision, not multiple

#### Reliability
- [ ] **Consistent responses** — Prompt design leads to predictable outputs
- [ ] **Error handling** — What if LLM returns unexpected format?
- [ ] **Fallback behavior** — What if prompt evaluation fails?
- [ ] **Token cost reasonable** — Prompt is concise enough

#### Integration
- [ ] **$ARGUMENTS placeholder used** — Context passed to prompt
- [ ] **Blocking tolerated** — LLM call latency is acceptable for this use case
- [ ] **Async if long-running** — `async: true` for hooks that don't need to return a decision

---

### Agent Hook Checklist

#### Agent Setup
- [ ] **Agent exists** — Referenced agent is defined in plugin
- [ ] **Agent has tools** — Has necessary tools for verification
- [ ] **Tool scoping appropriate** — Only needed tools available
- [ ] **No dangerous tools** — Doesn't have unnecessary Bash or network access

#### Reliability
- [ ] **Agent trained on task** — Instructions clear for verification
- [ ] **Fallback defined** — What if agent can't decide?
- [ ] **Timeout specified** — Prevents runaway verification
- [ ] **Error handling** — What if agent crashes?

#### Performance
- [ ] **Verification is fast** — <5s typical for simple verification
- [ ] **Async if needed** — Consider `async: true` for long-running verification
- [ ] **Tool limits set** — Agent has iteration limits

#### Integration
- [ ] **Result interpretation** — Clear how agent response affects hook behavior
- [ ] **Safe to fail** — Plugin continues if agent fails
- [ ] **Audit trail** — Can see why verification passed/failed

---

## Production & Team Hooks Checklist

Use when creating hooks for production or team use.

### Code Quality
- [ ] **Shellcheck passes** — Command scripts run `shellcheck script.sh` with no errors
- [ ] **Version tracked** — Version field in hook metadata
- [ ] **Changelog maintained** — Document changes between versions
- [ ] **Code reviewed** — Peer review before deployment
- [ ] **Security reviewed** — Checked for injection, privilege issues
- [ ] **Well commented** — Clear for other team members

### Testing & Validation
- [ ] **Unit tested** — Script/agent tested independently
- [ ] **Integration tested** — Works with other plugin hooks
- [ ] **Stress tested** — Works with high frequency triggers
- [ ] **Failure cases tested** — All error paths verified
- [ ] **Real scenario tested** — Validated with actual plugin workflow
- [ ] **Regression tested** — New hooks don't break existing functionality

### Documentation
- [ ] **Hook purpose clear** — Why does this hook exist?
- [ ] **Event explained** — Why this event?
- [ ] **Configuration documented** — How to configure hook
- [ ] **Troubleshooting guide** — Common issues and fixes

### Monitoring & Maintenance
- [ ] **Logging implemented** — Hook execution logged
- [ ] **Metrics tracked** — Success/failure rates monitored
- [ ] **Alerts configured** — Team notified of failures
- [ ] **Update procedure** — How to deploy new hook versions
- [ ] **Rollback procedure** — How to disable broken hooks

---

## Common Hook Patterns

### Pattern: Format on Write
```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "^(Write|Edit)$",
        "hooks": [{
          "type": "command",
          "command": "${CLAUDE_PLUGIN_ROOT}/scripts/format.sh",
          "timeout": 2000
        }]
      }
    ]
  }
}
```

### Pattern: Validate Before Commit
```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "matcher": "commit|push",
        "hooks": [{
          "type": "command",
          "command": "${CLAUDE_PLUGIN_ROOT}/scripts/pre-commit-check.sh",
          "timeout": 5000
        }]
      }
    ]
  }
}
```

### Pattern: Cleanup on Session End
```json
{
  "hooks": {
    "SessionEnd": [
      {
        "matcher": ".*",
        "hooks": [{
          "type": "command",
          "command": "${CLAUDE_PLUGIN_ROOT}/scripts/cleanup.sh",
          "timeout": 3000
        }]
      }
    ]
  }
}
```

---

## Troubleshooting Checklist

### Settings JSON Format Error (FIX FIRST)
**Error message:** `hooks: Expected array, but received undefined`

This happens when hooks aren't wrapped in the required `"hooks": [...]` array.

❌ **WRONG:**
```json
{
  "hooks": {
    "SessionStart": [{
      "type": "command",
      "command": "..."
    }]
  }
}
```

✅ **CORRECT:**
```json
{
  "hooks": {
    "SessionStart": [{
      "hooks": [{
        "type": "command",
        "command": "..."
      }]
    }]
  }
}
```

### Hook Doesn't Trigger
- [ ] Event correct? — Check against event reference
- [ ] Matcher syntax valid? — Test regex separately
- [ ] Matcher too specific? — Overly narrow pattern?
- [ ] JSON structure correct? — See JSON Format Error above
- [ ] Hook enabled? — Check plugin.json has hook enabled

### Hook Triggers Too Often
- [ ] Matcher too broad? — Does `.*` match everything?
- [ ] Correct event? — Running on too many events?
- [ ] Conditional logic needed? — Should trigger only sometimes?

### Hook Fails Silently
- [ ] Error logging missing? — No way to see failures
- [ ] onError behavior? — Set to continue instead of fail?
- [ ] Timeout too short? — Does script need more time?
- [ ] Missing dependencies? — Script depends on things not available?
- [ ] Exit code wrong? — Using exit 1 instead of exit 2?

### Hook Slows Plugin Down
- [ ] Timeout too long? — Set longer timeout than needed?
- [ ] Sync vs async? — Blocking operation when async better?
- [ ] Expensive matcher? — Complex regex on every event?
- [ ] Command itself slow? — Optimize script performance

### Hook Causes Plugin Crash
- [ ] Unhandled error? — Doesn't have error handling
- [ ] State corruption? — Modifying plugin state unsafely
- [ ] Permission issue? — Trying to write where can't
- [ ] Race condition? — Colliding with other hooks

---

## When a Hook Fails Validation

If a hook doesn't pass all 7 phases:

1. **Identify the phase** — Which phase failed?
2. **Understand the issue** — Why did it fail?
3. **Fix the root cause** — Adjust hook configuration or action
4. **Re-validate that phase** — Verify fix works
5. **Re-run full validation** — Other phases may be affected

**Example:** Hook times out during Phase 5 (performance)
- Root cause: Slow script or synchronous network dependency
- Fix: Optimize script or switch to `async: true`
- Re-validate: Does it still execute correctly? Is new timing acceptable?

---

## Sign-Off Checklist

Before deploying hook to production:

- [ ] All 7 validation phases passed
- [ ] All relevant type-specific checklists reviewed
- [ ] Peer review completed
- [ ] Security review completed
- [ ] Testing complete (success, negative, error cases)
- [ ] Documentation complete
- [ ] Monitoring/logging set up
- [ ] Rollback procedure documented
- [ ] Team notified of deployment
