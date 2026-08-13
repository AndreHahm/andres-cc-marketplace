# Tool Classification Taxonomy

## Categories

```text
coding-runtime
execution-companion
version-control
repository-host
package-manager
build-tool
test-tool
static-analysis
schema-validation
security-analysis
documentation
search-or-research
mcp-service
external-agent
operating-system-command
custom-script
unknown
```

## Detection Sources

* explicit tool-call names;
* shell command executables;
* MCP server identifiers;
* package invocations;
* Claude Code subagent names;
* network domains where safely available;
* generated files;
* project configuration;
* command output banners.

## Tool Usage Record

```yaml
tool:
  id: pytest
  category: test-tool
  version: "9.x"
  first_seen: EVT-000412
  invocation_count: 34
  successful_invocations: 29
  failed_invocations: 5
  changed_repository_state: false
  purposes:
    - verify acceptance examples
    - reproduce failing validation behavior
```

`first_seen` and invocation counts are best-effort within the current conversation's own evidence — this skill does not parse raw Claude Code session log files, so counts reflect what's observable in-session, not a cross-session ledger.

## Required Distinctions

Distinguish:

* a tool merely mentioned in text;
* a tool discovered in configuration;
* a tool actually invoked;
* a tool that changed repository state;
* a tool whose output was used as evidence for a finding.

Only "actually invoked" and later categories count toward the tool inventory in Phase 3 of `SKILL.md`. A tool merely mentioned or discovered in configuration is worth noting separately (e.g. "configured but never invoked this session") since that itself can be a finding — unused tooling, dead configuration — but it must not be counted as usage.
