# Agent Validation

7-phase workflow for validating agents before deployment. Run all phases for new agents; re-run relevant phases after changes.

## When to Re-Validate

Re-run after:
- Changing the description (impacts delegation)
- Adding/removing tools (impacts security and execution)
- Changing permission mode
- Adding or modifying hooks
- Encountering bugs or unexpected behavior

---

## Phase 1: Configuration

Verify the agent file is correctly formatted with all required fields.

**Checklist:**
- [ ] File is Markdown with YAML frontmatter (`---` delimiters)
- [ ] `name` present: lowercase-hyphen, 3–64 chars
- [ ] `description` present: 10–5,000 chars (this skill's own agent-description limit — not R21's 1024-char SKILL.md-description limit, a different field)
- [ ] `model` field valid: `inherit`, `sonnet`, `opus`, `haiku`, `fable`, or a full model ID
- [ ] `model` role fit (advisory, not blocking): if the agent's role is clearly orchestrator/implementer/quality-gate, compare against the role-tier mapping in `references/configuration-reference.md` — a mismatch is worth a Minor note, not a required change; `inherit` is never itself a violation
- [ ] `color` (if present): use the current valid list in `references/configuration-reference.md` — don't duplicate a separate enum here
- [ ] `tools` present (required by this skill's convention): exact tool names (capitalized: `Read`, `Write`, `Bash`), scoped to least privilege
- [ ] `disallowedTools` (if present): exact tool names; don't use both `tools` and `disallowedTools` unless intentional
- [ ] `permissionMode` (if present): `default`, `manual` (alias for `default`, v2.1.200+), `acceptEdits`, `dontAsk`, `auto`, `bypassPermissions`, or `plan`
- [ ] YAML syntax valid (proper indentation, no typos)
- [ ] File location correct (`agents/` in plugin project)

**Common errors:**

| Error | Fix |
|-------|-----|
| Tool name misspelled (`write` instead of `Write`) | Use exact capitalization: Read, Write, Edit, Bash, Glob, Grep |
| Invalid permission mode value | Valid: default, manual, acceptEdits, dontAsk, auto, bypassPermissions, plan |
| Both `tools` and `disallowedTools` set | Choose one; `tools` is allowlist, `disallowedTools` is denylist |
| Missing `description` field | Required — delegation won't work without it |

---

## Phase 2: Delegation Signal

Verify the description will reliably trigger delegation.

**Checklist:**
- [ ] Description has specific trigger phrases (concrete actions, not "when needed")
- [ ] Trigger phrases match actual user request phrasings
- [ ] Scope/constraints stated clearly
- [ ] Description follows: [Action]. Use when [triggers]. [Constraints].
- [ ] Length ≤1024 chars
- [ ] No vague language; no marketing language
- [ ] Uses concrete verbs (analyze, review, fix, generate, execute)

**Testing delegation:**
```
Request: "Analyze the user_activity table and generate a report"
Description: "Execute read-only database queries for data analysis. Use when analyzing data,
              generating reports, or exploring table structure. SELECT only."
Expected: ✅ Specific triggers recognized → delegates
```

**Fix poor delegation:**
1. Write 3 realistic user requests that should trigger this agent
2. Extract the key words from those requests
3. Include those words in the description
4. Add "Do not invoke when..." if the agent triggers too broadly

---

## Phase 3: Prompt Quality

Verify the system prompt body is clear and actionable.

**Checklist:**
- [ ] Purpose is clear (what is this agent supposed to do?)
- [ ] Instructions are procedural (numbered steps Claude will follow)
- [ ] 2+ concrete examples Claude can adapt
- [ ] Error cases addressed (what if operation fails?)
- [ ] Constraints are explicit (what operations are blocked?)
- [ ] Language is technical and precise (no ambiguity)
- [ ] Length: 500–3,000 chars ideal; ≤10,000 max; not overwhelming
- [ ] Written in second person (`You are...`)
- [ ] Output format defined

**Fix weak prompts:**
- Add concrete examples with expected output format
- Break instructions into numbered steps
- Add explicit error handling guidance
- State constraints directly ("Do not modify files")

---

## Phase 4: Tool Scoping

Verify tool access matches the agent's purpose (principle of least privilege).

**Checklist:**
- [ ] Agent has only the tools it needs
- [ ] Read-only agents denied Write/Edit
- [ ] Write access only granted if required for purpose
- [ ] Bash access only granted if required
- [ ] Tool names are capitalized correctly

**Matching table:**

| Purpose | Required Tools | Should Deny |
|---------|----------------|-------------|
| Read-only analysis | Read, Grep, Glob | Write, Edit, Bash |
| Code review | Read, Grep, Glob | Write, Edit, Bash |
| Code fixes | Read, Write, Edit, Bash | — |
| Database analysis | Read, `Bash` — an agent's `tools` field has no Bash-scoping syntax at all; bare `Bash` is the only correct form (a scoped `Bash(cmd:*)` entry here is itself an R6 violation, the opposite of the skill/command case); hooks don't contain a plugin-scoped agent either | Write, Edit |

**Fix over-scoped tools:**
```yaml
# Before: Too much access
tools: ["Read", "Write", "Edit", "Bash", "Glob", "Grep"]

# After: Read-only analysis only
tools: ["Read", "Grep", "Glob"]
```

---

## Phase 5: Permission Mode

Verify the permission mode matches how the agent will be used.

**Checklist:**
- [ ] Foreground agent: `default` or `acceptEdits`
- [ ] Background agent: `dontAsk` (auto-deny permission prompts)
- [ ] Read-only agent: `plan` (blocks all write operations)
- [ ] Mode matches tool access
- [ ] Production agents use specific modes (not generic `default`)

**Matching table:**

| Use Case | Mode | Why |
|----------|------|-----|
| Interactive code review | default | User approves each suggestion |
| Auto-fixing code | acceptEdits | File edits trusted; prompt for everything else |
| Background research | dontAsk | Auto-deny prompts; tool access works unattended |
| Read-only analysis | plan | Block all writes regardless of tools |

**Fix mismatched modes:**
```yaml
# Before: Read-only task but default mode (will prompt user)
tools: ["Read", "Glob"]
permissionMode: default

# After: Appropriate for read-only background work
tools: ["Read", "Glob"]
permissionMode: plan
```

---

## Phase 6: Hook Configuration

Only applicable if the agent file has a `hooks:` field.

**Checklist:**
- [ ] Hook YAML syntax is valid
- [ ] `matcher` specifies a tool name (e.g., `"Bash"`)
- [ ] Hook script path is relative and exists on disk
- [ ] Hook script is executable (`chmod +x`)
- [ ] PreToolUse hooks validate before execution
- [ ] Exit codes correct: 0 = allow, 2 = block
- [ ] Error messages written to stderr

**Example hook:**
```yaml
hooks:
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "./scripts/validate-readonly.sh"
```

**Example validation script:**
```bash
#!/bin/bash
INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')
if echo "$COMMAND" | grep -iE 'INSERT|UPDATE|DELETE|DROP|CREATE|ALTER'; then
  echo "Blocked: Only SELECT allowed" >&2
  exit 2
fi
exit 0
```

Test hooks independently: `echo '{"tool_input":{"command":"SELECT 1"}}' | ./scripts/validate-readonly.sh`

---

## Phase 7: Real-World Testing

**Checklist:**
- [ ] Claude delegates to this agent (not others) on realistic requests
- [ ] Test with multiple request phrasings (not just one)
- [ ] Agent completes its task successfully
- [ ] Output is useful and formatted correctly
- [ ] Failures fail gracefully (no crashes; clear error messages)
- [ ] Tools work as expected (accepts/denies as configured)
- [ ] Permission modes work (prompts or auto-deny as configured)
- [ ] Works in background if intended (main conversation continues)

**Debugging failed tests:**

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| Delegation not happening | Description lacks specific trigger phrases | Rewrite description; add worked scenarios in body |
| Execution failing | Prompt is unclear; tool access wrong | Improve prompt; verify tools |
| Permission denied unexpectedly | Tool not in allowlist or hook blocking | Check tool list, permission mode, hook logic |
| Output confusing | Output format not defined in prompt | Add explicit output format section to prompt |

---

## Validation Sign-Off

An agent is deployment-ready when all phases pass:

- ✅ Phase 1: Configuration valid (YAML, required fields)
- ✅ Phase 2: Delegation reliable (description has specific trigger phrases)
- ✅ Phase 3: Prompt clear (Claude can execute from instructions)
- ✅ Phase 4: Tool access minimal (principle of least privilege)
- ✅ Phase 5: Permission mode appropriate (matches use case)
- ✅ Phase 6: Hooks correct (if present)
- ✅ Phase 7: Real-world testing passes

---

## Security Checklist (Production)

**Plugin-scoped agents (the case this skill covers):** `permissionMode` and `hooks` are accepted by the
schema but are **not honored for plugin-scoped agents** — see `agent-development/SKILL.md`'s `hooks`
section. Neither `plan` mode nor a `hooks:` field actually contains a plugin agent's writes; the only
working hardening mechanism for a plugin-scoped agent is its `tools`/`disallowedTools` allowlist itself.
The two checklist items below that reference `plan`/hooks apply only to non-plugin (project-level) agents.

- [ ] No unnecessary write access
- [ ] Read-only agents omit `Write`, `Edit`, and `Bash` from `tools` entirely — this is the only hardening
      that actually works for a plugin-scoped agent; `plan` mode or hooks (project-level agents only)
- [ ] Hooks prevent dangerous operations (e.g., SQL writes) — project-level agents only, not plugin-scoped
- [ ] No credentials, API keys, or secrets in body
- [ ] No hardcoded paths that expose internal structure
- [ ] Tool scoping follows principle of least privilege
- [ ] Sensitive-data agents use restricted permission modes (project-level agents only) or, for
      plugin-scoped agents, a narrowed `tools` allowlist

---

## Team & Production Agents

Additional requirements before sharing or deploying to a team:

- [ ] Error handling is robust with clear, user-friendly messages
- [ ] Hook scripts tested (allow case, block case, error case)
- [ ] Documentation explains purpose, trigger phrases, permission mode rationale
- [ ] Security review completed (permissions, tool access, hook logic)
- [ ] Tested across multiple realistic request phrasings
